from fastapi import APIRouter, Depends, HTTPException, Query, Body, Header, UploadFile, File, Request
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import text
from datetime import datetime, timedelta
from typing import Optional, Dict
import base64
import hashlib
import hmac
import os
import secrets
import csv
import io
import json
import re
import time
from zipfile import BadZipFile
from ..database.db import get_db
from ..database.models import (
    ActionApproval,
    AIAction,
    AuditLog,
    CashflowForecast,
    Customer,
    Expense,
    ExpenseCategory,
    Invoice,
    LedgerAccount,
    LedgerEntry,
    Merchant,
    Payment,
    Product,
    RepaymentPrediction,
    SimulationRun,
    Supplier,
    SupplierPayable,
    Owner,
    RazorpayWebhookLog,
)
from ..services.ledger_service import LedgerService
from ..services.cashflow_service import CashflowService
from ..services.customer_intelligence import CustomerIntelligenceService
from ..services.ml_repayment_service import ml_repayment_service
from ..services.decision_engine import DecisionEngine
from ..services.policy_engine import PolicyEngine
from ..services.simulation_service import SimulationService
from ..services.evaluation_service import EvaluationService
from ..services.copilot_service import CopilotService
from ..services.demo_scenarios import DemoScenariosService
from ..services.razorpay_service import RazorpayService
from ..services.expense_service import ExpenseService
from ..services.promise_to_pay_service import PromiseToPayService
from ..services.ai_intelligence_service import AIIntelligenceService

router = APIRouter(prefix="/api")
MAX_IMPORT_SIZE = 10 * 1024 * 1024
LOGIN_FAILURES: dict[str, list[float]] = {}

AUTH_SECRET = os.getenv("CASHPILOT_AUTH_SECRET", "change-this-cashpilot-secret")
AUTH_TOKEN_TTL_SECONDS = int(os.getenv("CASHPILOT_AUTH_TTL_SECONDS", "28800"))

def _password_hash(password: str, salt: str | None = None) -> str:
    salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 120000).hex()
    return f"{salt}${digest}"

def _password_matches(password: str, stored: str) -> bool:
    try:
        salt, digest = stored.split("$", 1)
    except ValueError:
        return False
    return hmac.compare_digest(_password_hash(password, salt).split("$", 1)[1], digest)

def _token(username: str) -> str:
    value = base64.urlsafe_b64encode(f"{username}|{int(time.time())}".encode()).decode().rstrip("=")
    signature = hmac.new(AUTH_SECRET.encode(), value.encode(), hashlib.sha256).hexdigest()
    return f"{value}.{signature}"

def _owner(authorization: Optional[str], db: Session) -> Owner:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Owner login required")
    try:
        value, signature = authorization[7:].split(".", 1)
        expected = hmac.new(AUTH_SECRET.encode(), value.encode(), hashlib.sha256).hexdigest()
        token_data = base64.urlsafe_b64decode(value + "=" * (-len(value) % 4)).decode()
        username, issued_at_text = token_data.rsplit("|", 1)
        if time.time() - int(issued_at_text) > AUTH_TOKEN_TTL_SECONDS:
            raise HTTPException(status_code=401, detail="Owner session expired. Please sign in again")
    except (ValueError, UnicodeDecodeError):
        raise HTTPException(status_code=401, detail="Invalid owner session")
    if not hmac.compare_digest(signature, expected):
        raise HTTPException(status_code=401, detail="Invalid owner session")
    owner = db.query(Owner).filter(Owner.username == username).first()
    if not owner:
        raise HTTPException(status_code=401, detail="Owner account not found")
    return owner

def _merchant(db: Session) -> Merchant:
    merchant = db.query(Merchant).first()
    if not merchant:
        merchant = Merchant(name="My Business", business_type="Distributor/Wholesaler", currency="INR")
        db.add(merchant)
        db.flush()
    return merchant

def _ensure_ledger_accounts(db: Session) -> None:
    accounts = {
        "1010": ("Cash & Bank Account", "ASSET"),
        "1020": ("Accounts Receivable", "ASSET"),
        "1030": ("Inventory / Supplier Advances", "ASSET"),
        "2010": ("Accounts Payable", "LIABILITY"),
        "2020": ("Other Liabilities", "LIABILITY"),
        "3010": ("Owner's Capital", "EQUITY"),
        "4010": ("Sales Revenue", "REVENUE"),
        "5010": ("Cost of Goods Sold", "EXPENSE"),
        "5020": ("Rent Expense", "EXPENSE"),
        "5030": ("Payroll Expense", "EXPENSE"),
        "5040": ("Utilities Expense", "EXPENSE"),
        "5050": ("Operating Expense", "EXPENSE"),
        "5060": ("Software Expense", "EXPENSE"),
        "5070": ("Finance Expense", "EXPENSE"),
    }
    for code, (name, account_type) in accounts.items():
        if not db.query(LedgerAccount).filter(LedgerAccount.code == code).first():
            db.add(LedgerAccount(code=code, name=name, type=account_type, balance=0.0))
    db.flush()

def _post_cash_delta(db: Session, amount: float, description: str, source_type: str, source_id: str, created_by: str, cash_in: bool, debit_account: str = None, credit_account: str = None) -> None:
    if amount <= 0:
        return
    _ensure_ledger_accounts(db)
    merchant = _merchant(db)
    merchant.current_cash = max(0.0, float(merchant.current_cash or 0.0) + (amount if cash_in else -amount))
    debit = debit_account or ("1010" if cash_in else "5050")
    credit = credit_account or ("4010" if cash_in else "1010")
    LedgerService.post_entry(db, debit, credit, amount, description, source_type, source_id, created_by)

@router.get("/auth/status")
def auth_status(db: Session = Depends(get_db)):
    owner = db.query(Owner).first()
    return {"setup_required": owner is None, "username": owner.username if owner else None}

@router.get("/auth/username-availability")
def username_availability(username: str = Query("", min_length=0), db: Session = Depends(get_db)):
    normalized_username = username.strip()
    owner = db.query(Owner).filter(Owner.username == normalized_username).first() if normalized_username else None
    return {
        "username": normalized_username,
        "available": bool(normalized_username) and owner is None,
        "already_exists": owner is not None,
        "setup_required": db.query(Owner).first() is None,
    }

@router.post("/auth/setup")
def setup_owner(payload: Dict = Body(...), db: Session = Depends(get_db)):
    username = str(payload.get("username", "")).strip()
    password = str(payload.get("password", ""))
    business_name = str(payload.get("business_name", "")).strip() or "My Business"
    opening_balance = float(payload.get("current_balance") if payload.get("current_balance") not in (None, "") else 200000.0)
    if len(username) < 3 or len(password) < 8 or opening_balance < 0:
        raise HTTPException(status_code=400, detail="Username must be 3+ characters and password 8+ characters")
    if db.query(Owner).filter(Owner.username == username).first():
        raise HTTPException(status_code=409, detail=f"Username '{username}' already exists. Choose another username.")
    if db.query(Owner).first():
        merchant = Merchant(name=business_name, business_type="Distributor/Wholesaler", currency="INR", min_cash_buffer=200000.0, current_cash=opening_balance)
        db.add(merchant)
        db.flush()
        _ensure_ledger_accounts(db)
        owner = Owner(username=username, password_hash=_password_hash(password), merchant_id=merchant.id)
        db.add(owner)
        db.add(AuditLog(actor="OWNER", action="CREATE_OWNER_ACCOUNT", details=f"Additional owner account created for {username}"))
        db.commit()
        return {"token": _token(username), "username": username, "business_name": merchant.name}
    for model in (Payment, RepaymentPrediction, Invoice, ActionApproval, AIAction, SupplierPayable, Expense, Customer, Supplier,
                  Product, AuditLog, CashflowForecast, LedgerEntry, SimulationRun, RazorpayWebhookLog):
        db.query(model).delete(synchronize_session=False)
    db.query(LedgerAccount).update({LedgerAccount.balance: 0.0}, synchronize_session=False)
    owner = Owner(username=username, password_hash=_password_hash(password))
    db.add(owner)
    merchant = _merchant(db)
    owner.merchant_id = merchant.id
    merchant.name = business_name
    merchant.current_cash = opening_balance
    _ensure_ledger_accounts(db)
    if opening_balance > 0:
        cash_account = db.query(LedgerAccount).filter(LedgerAccount.code == "1010").one()
        capital_account = db.query(LedgerAccount).filter(LedgerAccount.code == "3010").one()
        cash_account.balance = opening_balance
        capital_account.balance = opening_balance
        db.add(LedgerEntry(entry_number=f"OPEN-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
                           transaction_date=datetime.utcnow(), debit_account="1010", credit_account="3010",
                           amount=opening_balance, description="Opening balance", source_type="MANUAL",
                           created_by=username, is_approved=True))
    db.add(AuditLog(actor="OWNER", action="CREATE_OWNER_ACCOUNT", details=f"Owner account created for {username}"))
    db.commit()
    return {"token": _token(username), "username": username, "business_name": merchant.name}

@router.post("/auth/login")
def login_owner(payload: Dict = Body(...), db: Session = Depends(get_db)):
    username = str(payload.get("username", "")).strip()
    now = time.time()
    recent_failures = [stamp for stamp in LOGIN_FAILURES.get(username, []) if now - stamp < 900]
    if len(recent_failures) >= 5:
        raise HTTPException(status_code=429, detail="Too many failed attempts. Try again in 15 minutes")
    owner = db.query(Owner).filter(Owner.username == username).first()
    if not owner or not _password_matches(str(payload.get("password", "")), owner.password_hash):
        LOGIN_FAILURES[username] = recent_failures + [now]
        raise HTTPException(status_code=401, detail="Incorrect username or password")
    LOGIN_FAILURES.pop(username, None)
    return {"token": _token(owner.username), "username": owner.username}

@router.get("/auth/me")
def current_owner(authorization: Optional[str] = Header(default=None), db: Session = Depends(get_db)):
    owner = _owner(authorization, db)
    return {"username": owner.username}

@router.get("/health")
def health_check():
    return {"status": "ok", "app": "CashPilot AI Backend", "version": "1.0.0"}

@router.post("/owner/customers")
def create_customer(payload: Dict = Body(...), authorization: Optional[str] = Header(default=None), db: Session = Depends(get_db)):
    owner = _owner(authorization, db)
    name = str(payload.get("name", "")).strip()
    if not name:
        raise HTTPException(status_code=400, detail="Customer name is required")
    merchant = _merchant(db)
    customer = Customer(
        merchant_id=merchant.id,
        name=name,
        phone=str(payload.get("phone", "")).strip(),
        email=str(payload.get("email", "")).strip(),
        address=str(payload.get("address", "")).strip(),
        credit_period_days=int(payload.get("credit_period_days", 15)),
        credit_limit=float(payload.get("credit_limit", 500000) or 500000),
    )
    db.add(customer)
    db.add(AuditLog(actor=owner.username, action="CREATE_CUSTOMER", details=f"Added customer {name}"))
    db.commit()
    return {"id": customer.id, "name": customer.name}

@router.post("/owner/sales")
def create_sale(payload: Dict = Body(...), authorization: Optional[str] = Header(default=None), db: Session = Depends(get_db)):
    owner = _owner(authorization, db)
    merchant = _merchant(db)
    customer = db.query(Customer).filter(Customer.id == payload.get("customer_id")).first()
    if not customer:
        raise HTTPException(status_code=400, detail="Select an existing customer")
    amount = float(payload.get("amount", 0) or 0)
    if amount <= 0:
        raise HTTPException(status_code=400, detail="Sale amount must be greater than zero")
    paid_amount = min(amount, max(0.0, float(payload.get("paid_amount", 0) or 0)))
    issue_date = datetime.fromisoformat(str(payload.get("issue_date"))) if payload.get("issue_date") else datetime.utcnow()
    due_date = datetime.fromisoformat(str(payload.get("due_date"))) if payload.get("due_date") else issue_date
    invoice_number = str(payload.get("invoice_number", "")).strip() or f"INV-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
    if db.query(Invoice).filter(Invoice.invoice_number == invoice_number).first():
        raise HTTPException(status_code=409, detail="Invoice number already exists")
    invoice = Invoice(merchant_id=merchant.id, customer_id=customer.id, invoice_number=invoice_number,
                      issue_date=issue_date, due_date=due_date, total_amount=amount, paid_amount=paid_amount,
                      outstanding_amount=amount - paid_amount,
                      status="PAID" if paid_amount == amount else "PARTIALLY_PAID" if paid_amount else "ISSUED",
                      payment_terms_days=max(0, (due_date.date() - issue_date.date()).days))
    customer.total_purchases_val = (customer.total_purchases_val or 0) + amount
    customer.total_paid_val = (customer.total_paid_val or 0) + paid_amount
    customer.current_outstanding = (customer.current_outstanding or 0) + amount - paid_amount
    customer.total_transactions_count = (customer.total_transactions_count or 0) + 1
    db.add(invoice)
    db.flush()
    if paid_amount:
        _post_cash_delta(db, paid_amount, f"Customer payment received for invoice {invoice_number}", "PAYMENT", invoice.id, owner.username, True, "1010", "4010")
    if invoice.outstanding_amount:
        _post_cash_delta(db, invoice.outstanding_amount, f"Credit sale recorded for invoice {invoice_number}", "SALE", invoice.id, owner.username, False, "1020", "4010")
    db.add(AuditLog(actor=owner.username, action="CREATE_SALE", details=f"Recorded sale {invoice_number}"))
    db.commit()
    return {"id": invoice.id, "invoice_number": invoice.invoice_number}

@router.post("/owner/purchases")
def create_purchase(payload: Dict = Body(...), authorization: Optional[str] = Header(default=None), db: Session = Depends(get_db)):
    owner = _owner(authorization, db)
    merchant = _merchant(db)
    supplier_name = str(payload.get("supplier_name", "")).strip()
    amount = float(payload.get("amount", 0) or 0)
    if not supplier_name or amount <= 0:
        raise HTTPException(status_code=400, detail="Supplier and purchase amount are required")
    supplier = db.query(Supplier).filter(Supplier.merchant_id == merchant.id, Supplier.name == supplier_name).first()
    if not supplier:
        supplier = Supplier(merchant_id=merchant.id, name=supplier_name)
        db.add(supplier)
        db.flush()
    supplier.contact_person = str(payload.get("contact_person", "")).strip() or supplier.contact_person
    supplier.phone = str(payload.get("phone", "")).strip() or supplier.phone
    supplier.email = str(payload.get("email", "")).strip() or supplier.email
    supplier.category = str(payload.get("category", "Inventory Supplier")).strip() or supplier.category
    supplier.criticality = str(payload.get("criticality", supplier.criticality)).upper()
    supplier.payment_terms = str(payload.get("payment_terms", supplier.payment_terms)).upper()
    purchase_date = datetime.fromisoformat(str(payload.get("purchase_date"))) if payload.get("purchase_date") else datetime.utcnow()
    due_date = datetime.fromisoformat(str(payload.get("due_date"))) if payload.get("due_date") else purchase_date
    paid_amount = min(amount, max(0.0, float(payload.get("paid_amount", 0) or 0)))
    bill = SupplierPayable(supplier_id=supplier.id, bill_number=str(payload.get("bill_number", "")).strip() or f"BILL-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
                           purchase_date=purchase_date, due_date=due_date, total_amount=amount, paid_amount=paid_amount,
                           outstanding_amount=amount - paid_amount,
                           status="PAID" if paid_amount == amount else "PARTIALLY_PAID" if paid_amount else "UNPAID")
    supplier.current_payable = (supplier.current_payable or 0) + amount - paid_amount
    db.add(bill)
    db.flush()
    if paid_amount:
        _post_cash_delta(db, paid_amount, f"Supplier payment made for bill {bill.bill_number}", "SUPPLIER_PAYMENT", bill.id, owner.username, False, "2010", "1010")
    _post_cash_delta(db, amount, f"Inventory purchase recorded for bill {bill.bill_number}", "PURCHASE", bill.id, owner.username, False, "5010", "2010")
    db.add(AuditLog(actor=owner.username, action="CREATE_PURCHASE", details=f"Recorded purchase for {supplier_name}"))
    db.commit()
    return {"id": bill.id, "bill_number": bill.bill_number}

@router.post("/owner/expenses")
def create_expense(payload: Dict = Body(...), authorization: Optional[str] = Header(default=None), db: Session = Depends(get_db)):
    owner = _owner(authorization, db)
    merchant = _merchant(db)
    title = str(payload.get("title", "")).strip()
    amount = float(payload.get("amount", 0) or 0)
    if not title or amount <= 0:
        raise HTTPException(status_code=400, detail="Expense title and amount are required")
    category_name = str(payload.get("category", "Miscellaneous")).strip() or "Miscellaneous"
    category = db.query(ExpenseCategory).filter(ExpenseCategory.name == category_name).first()
    if not category:
        category = ExpenseCategory(name=category_name, type=str(payload.get("category_type", "MISC")).upper())
        db.add(category)
        db.flush()
    expense_date = datetime.fromisoformat(str(payload.get("date"))) if payload.get("date") else datetime.utcnow()
    expense = Expense(merchant_id=merchant.id, category_id=category.id, title=title, amount=amount, expense_date=expense_date,
                      is_recurring=bool(payload.get("is_recurring", False)), frequency=str(payload.get("frequency", "ONE_TIME")))
    db.add(expense)
    db.flush()
    _post_cash_delta(db, amount, f"Expense paid: {title}", "EXPENSE", expense.id, owner.username, False, "5050", "1010")
    db.add(AuditLog(actor=owner.username, action="CREATE_EXPENSE", details=f"Recorded expense {title}"))
    db.commit()
    return {"id": expense.id, "title": expense.title}

@router.post("/owner/invoices/{invoice_id}/payment")
def record_customer_payment(invoice_id: str, payload: Dict = Body(...), authorization: Optional[str] = Header(default=None), db: Session = Depends(get_db)):
    owner = _owner(authorization, db)
    invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    amount = float(payload.get("amount", 0) or 0)
    if amount <= 0 or amount > invoice.outstanding_amount + 0.01:
        raise HTTPException(status_code=400, detail="Payment must be positive and no more than the outstanding amount")
    invoice.paid_amount += amount
    invoice.outstanding_amount = max(0.0, invoice.total_amount - invoice.paid_amount)
    invoice.status = "PAID" if invoice.outstanding_amount <= 0.01 else "PARTIALLY_PAID"
    if invoice.customer:
        invoice.customer.total_paid_val = (invoice.customer.total_paid_val or 0) + amount
        invoice.customer.current_outstanding = max(0.0, (invoice.customer.current_outstanding or 0) - amount)
    payment = Payment(invoice_id=invoice.id, customer_id=invoice.customer_id, amount=amount, payment_method=str(payload.get("payment_method", "Bank_Transfer")), status="SUCCESS", transaction_reference=str(payload.get("reference", "")))
    db.add(payment)
    db.flush()
    _post_cash_delta(db, amount, f"Customer payment received for invoice {invoice.invoice_number}", "PAYMENT", payment.id, owner.username, True, "1010", "1020")
    db.add(AuditLog(actor=owner.username, action="RECORD_CUSTOMER_PAYMENT", details=f"Received INR {amount:,.2f} for {invoice.invoice_number}"))
    db.commit()
    return {"status": "recorded", "invoice_id": invoice.id, "paid_amount": invoice.paid_amount, "outstanding_amount": invoice.outstanding_amount, "invoice_status": invoice.status}

@router.post("/owner/payables/{payable_id}/payment")
def record_supplier_payment(payable_id: str, payload: Dict = Body(...), authorization: Optional[str] = Header(default=None), db: Session = Depends(get_db)):
    owner = _owner(authorization, db)
    payable = db.query(SupplierPayable).filter(SupplierPayable.id == payable_id).first()
    if not payable:
        raise HTTPException(status_code=404, detail="Payable not found")
    amount = float(payload.get("amount", 0) or 0)
    if amount <= 0 or amount > payable.outstanding_amount + 0.01:
        raise HTTPException(status_code=400, detail="Payment must be positive and no more than the outstanding amount")
    payable.paid_amount += amount
    payable.outstanding_amount = max(0.0, payable.total_amount - payable.paid_amount)
    payable.status = "PAID" if payable.outstanding_amount <= 0.01 else "PARTIALLY_PAID"
    if payable.supplier:
        payable.supplier.current_payable = max(0.0, (payable.supplier.current_payable or 0) - amount)
    _post_cash_delta(db, amount, f"Supplier payment made for bill {payable.bill_number}", "SUPPLIER_PAYMENT", payable.id, owner.username, False, "2010", "1010")
    db.add(AuditLog(actor=owner.username, action="RECORD_SUPPLIER_PAYMENT", details=f"Paid INR {amount:,.2f} for {payable.bill_number}"))
    db.commit()
    return {"status": "recorded", "payable_id": payable.id, "paid_amount": payable.paid_amount, "outstanding_amount": payable.outstanding_amount, "payable_status": payable.status}

@router.put("/owner/invoices/{invoice_id}")
def update_invoice(invoice_id: str, payload: Dict = Body(...), authorization: Optional[str] = Header(default=None), db: Session = Depends(get_db)):
    owner = _owner(authorization, db)
    invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    old_paid = invoice.paid_amount
    old_total = invoice.total_amount
    if "invoice_number" in payload:
        new_number = str(payload["invoice_number"]).strip()
        duplicate = db.query(Invoice).filter(Invoice.invoice_number == new_number, Invoice.id != invoice.id).first()
        if duplicate: raise HTTPException(status_code=409, detail="Invoice number already exists")
        invoice.invoice_number = new_number
    if "total_amount" in payload: invoice.total_amount = float(payload["total_amount"])
    if "due_date" in payload: invoice.due_date = datetime.fromisoformat(str(payload["due_date"]))
    if "paid_amount" in payload: invoice.paid_amount = min(invoice.total_amount, max(0.0, float(payload["paid_amount"])))
    if invoice.total_amount <= 0: raise HTTPException(status_code=400, detail="Invoice total must be greater than zero")
    invoice.outstanding_amount = max(0.0, invoice.total_amount - invoice.paid_amount)
    invoice.status = "PAID" if invoice.outstanding_amount <= 0.01 else "PARTIALLY_PAID" if invoice.paid_amount else "ISSUED"
    if invoice.customer:
        invoice.customer.current_outstanding = max(0.0, (invoice.customer.current_outstanding or 0) + old_total - old_paid - invoice.total_amount + invoice.paid_amount)
        invoice.customer.total_purchases_val = max(0.0, (invoice.customer.total_purchases_val or 0) + invoice.total_amount - old_total)
        invoice.customer.total_paid_val = max(0.0, (invoice.customer.total_paid_val or 0) + invoice.paid_amount - old_paid)
    cash_delta = invoice.paid_amount - old_paid
    total_delta = invoice.total_amount - old_total
    if total_delta > 0: _post_cash_delta(db, total_delta, f"Invoice value increase for {invoice.invoice_number}", "INVOICE_ADJUSTMENT", invoice.id, owner.username, False, "1020", "4010")
    elif total_delta < 0: _post_cash_delta(db, abs(total_delta), f"Invoice value reduction for {invoice.invoice_number}", "INVOICE_ADJUSTMENT", invoice.id, owner.username, False, "4010", "1020")
    if cash_delta > 0: _post_cash_delta(db, cash_delta, f"Additional customer payment for invoice {invoice.invoice_number}", "PAYMENT", invoice.id, owner.username, True, "1010", "1020")
    elif cash_delta < 0: _post_cash_delta(db, abs(cash_delta), f"Customer payment reversal for invoice {invoice.invoice_number}", "PAYMENT_REVERSAL", invoice.id, owner.username, False, "1020", "1010")
    db.add(AuditLog(actor=owner.username, action="UPDATE_INVOICE", details=f"Updated invoice {invoice.invoice_number}"))
    db.commit()
    return {"status": "updated", "id": invoice.id, "outstanding_amount": invoice.outstanding_amount}

@router.put("/owner/payables/{payable_id}")
def update_payable(payable_id: str, payload: Dict = Body(...), authorization: Optional[str] = Header(default=None), db: Session = Depends(get_db)):
    owner = _owner(authorization, db)
    payable = db.query(SupplierPayable).filter(SupplierPayable.id == payable_id).first()
    if not payable: raise HTTPException(status_code=404, detail="Payable not found")
    old_paid = payable.paid_amount
    old_total = payable.total_amount
    if "bill_number" in payload: payable.bill_number = str(payload["bill_number"]).strip()
    if "total_amount" in payload: payable.total_amount = float(payload["total_amount"])
    if "due_date" in payload: payable.due_date = datetime.fromisoformat(str(payload["due_date"]))
    if "paid_amount" in payload: payable.paid_amount = min(payable.total_amount, max(0.0, float(payload["paid_amount"])))
    if payable.total_amount <= 0: raise HTTPException(status_code=400, detail="Bill total must be greater than zero")
    payable.outstanding_amount = max(0.0, payable.total_amount - payable.paid_amount)
    payable.status = "PAID" if payable.outstanding_amount <= 0.01 else "PARTIALLY_PAID" if payable.paid_amount else "UNPAID"
    if payable.supplier: payable.supplier.current_payable = max(0.0, (payable.supplier.current_payable or 0) + old_total - old_paid - payable.total_amount + payable.paid_amount)
    cash_delta = payable.paid_amount - old_paid
    total_delta = payable.total_amount - old_total
    if total_delta > 0: _post_cash_delta(db, total_delta, f"Bill value increase for {payable.bill_number}", "BILL_ADJUSTMENT", payable.id, owner.username, False, "5010", "2010")
    elif total_delta < 0: _post_cash_delta(db, abs(total_delta), f"Bill value reduction for {payable.bill_number}", "BILL_ADJUSTMENT", payable.id, owner.username, False, "2010", "5010")
    if cash_delta > 0: _post_cash_delta(db, cash_delta, f"Additional supplier payment for bill {payable.bill_number}", "SUPPLIER_PAYMENT", payable.id, owner.username, False, "2010", "1010")
    elif cash_delta < 0: _post_cash_delta(db, abs(cash_delta), f"Supplier payment reversal for bill {payable.bill_number}", "PAYMENT_REVERSAL", payable.id, owner.username, True, "1010", "2010")
    db.add(AuditLog(actor=owner.username, action="UPDATE_PAYABLE", details=f"Updated bill {payable.bill_number}"))
    db.commit()
    return {"status": "updated", "id": payable.id, "outstanding_amount": payable.outstanding_amount}

@router.put("/owner/expenses/{expense_id}")
def update_expense(expense_id: str, payload: Dict = Body(...), authorization: Optional[str] = Header(default=None), db: Session = Depends(get_db)):
    owner = _owner(authorization, db)
    expense = db.query(Expense).filter(Expense.id == expense_id).first()
    if not expense: raise HTTPException(status_code=404, detail="Expense not found")
    old_amount = expense.amount
    if "title" in payload: expense.title = str(payload["title"]).strip()
    if "amount" in payload: expense.amount = max(0.0, float(payload["amount"]))
    if expense.amount <= 0: raise HTTPException(status_code=400, detail="Expense amount must be greater than zero")
    if "is_recurring" in payload: expense.is_recurring = bool(payload["is_recurring"])
    delta = expense.amount - old_amount
    if delta > 0: _post_cash_delta(db, delta, f"Additional expense paid: {expense.title}", "EXPENSE", expense.id, owner.username, False, "5050", "1010")
    elif delta < 0: _post_cash_delta(db, abs(delta), f"Expense correction received: {expense.title}", "EXPENSE_REVERSAL", expense.id, owner.username, True, "1010", "5050")
    db.add(AuditLog(actor=owner.username, action="UPDATE_EXPENSE", details=f"Updated expense {expense.title}"))
    db.commit()
    return {"status": "updated", "id": expense.id, "amount": expense.amount}

def _import_rows(filename: str, content: bytes) -> list[dict]:
    extension = filename.lower().rsplit(".", 1)[-1]
    if extension == "csv":
        try:
            decoded = content.decode("utf-8-sig")
        except UnicodeDecodeError:
            decoded = content.decode("latin-1")
        reader = csv.DictReader(io.StringIO(decoded))
        return [dict(row) for row in reader]
    if extension in {"xlsx", "xlsm"}:
        from openpyxl import load_workbook
        try:
            sheet = load_workbook(io.BytesIO(content), read_only=True, data_only=True).active
        except (BadZipFile, OSError, ValueError) as exc:
            raise HTTPException(status_code=400, detail="The Excel file is invalid or corrupted") from exc
        values = list(sheet.values)
        if not values:
            return []
        headers = [str(value or "").strip().lower() for value in values[0]]
        return [dict(zip(headers, row)) for row in values[1:] if any(value is not None for value in row)]
    text_content = ""
    if extension == "pdf":
        from pypdf import PdfReader
        from pypdf.errors import PdfReadError
        try:
            text_content = "\n".join(page.extract_text() or "" for page in PdfReader(io.BytesIO(content)).pages)
        except (PdfReadError, OSError, ValueError) as exc:
            raise HTTPException(status_code=400, detail="The PDF file is invalid or cannot be read") from exc
    elif extension == "docx":
        from docx import Document
        try:
            document = Document(io.BytesIO(content))
        except (BadZipFile, OSError, ValueError) as exc:
            raise HTTPException(status_code=400, detail="The DOCX file is invalid or corrupted") from exc
        text_content = "\n".join(paragraph.text for paragraph in document.paragraphs)
    elif extension in {"png", "jpg", "jpeg", "webp"}:
        try:
            import pytesseract
            from PIL import Image
            text_content = pytesseract.image_to_string(Image.open(io.BytesIO(content)))
        except (ImportError, OSError):
            raise HTTPException(status_code=400, detail="Image OCR requires Tesseract OCR to be installed")
    else:
        raise HTTPException(status_code=400, detail="Use CSV, Excel, PDF, DOCX, PNG, JPG, or WEBP")
    rows = []
    for line in text_content.splitlines():
        amounts = re.findall(r"(?:₹|Rs\.?|INR)?\s*([0-9][0-9,]*(?:\.\d+)?)", line, flags=re.I)
        amount = float(amounts[-1].replace(",", "")) if amounts else 0
        lower = line.lower()
        record_type = "expense" if any(word in lower for word in ("expense", "rent", "salary", "fuel", "utility", "bill")) else "sale" if any(word in lower for word in ("sale", "invoice", "buyer", "customer")) else "purchase"
        rows.append({"type": record_type, "name": re.sub(r"(?:₹|Rs\.?|INR)?\s*[0-9][0-9,]*(?:\.\d+)?", "", line, flags=re.I).strip(" :-"), "amount": amount})
    return [row for row in rows if row.get("name") and row.get("amount", 0) > 0]

def _normalized_import_row(raw: dict) -> dict:
    aliases = {
        "record": "type",
        "record_type": "type",
        "kind": "type",
        "customer_name": "name",
        "buyer_name": "name",
        "supplier_name": "name",
        "seller_name": "name",
        "description": "name",
        "title": "name",
        "total_amount": "amount",
        "value": "amount",
        "invoice": "invoice_number",
        "bill": "bill_number",
        "paid": "paid_amount",
        "payment": "paid_amount",
    }
    normalized = {}
    for key, value in raw.items():
        if key is None:
            continue
        clean_key = re.sub(r"[^a-z0-9]+", "_", str(key).strip().lower()).strip("_")
        if not clean_key:
            continue
        normalized[aliases.get(clean_key, clean_key)] = value
    return normalized

def _number(value, default: float = 0.0) -> float:
    try:
        return float(str(value or default).replace(",", "").strip())
    except (TypeError, ValueError):
        return default

def _integer(value, default: int = 15) -> int:
    try:
        return int(float(str(value or default).replace(",", "").strip()))
    except (TypeError, ValueError):
        return default

@router.post("/owner/import")
async def import_business_file(file: UploadFile = File(...), commit: bool = Query(False), authorization: Optional[str] = Header(default=None), db: Session = Depends(get_db)):
    owner = _owner(authorization, db)
    content = await file.read()
    if len(content) > MAX_IMPORT_SIZE:
        raise HTTPException(status_code=413, detail="File is too large. Maximum size is 10 MB")
    rows = _import_rows(file.filename or "", content)
    if not rows:
        raise HTTPException(status_code=400, detail="No readable records found")
    if not commit:
        valid = 0
        invalid = 0
        for raw in rows:
            row = _normalized_import_row(raw)
            try:
                amount = float(str(row.get("amount", row.get("total", 0)) or 0).replace(",", ""))
            except ValueError:
                amount = 0
            record_type = str(row.get("type", row.get("record_type", "expense"))).lower()
            if row.get("name") or row.get("customer") or row.get("buyer") or row.get("supplier") or row.get("seller") or row.get("title"):
                valid += 1 if amount > 0 or record_type in {"buyer", "customer", "seller", "supplier"} else 0
            else:
                invalid += 1
        return {"status": "preview", "filename": file.filename, "rows": rows[:100], "total_rows": len(rows), "valid_rows": valid, "invalid_rows": invalid}
    merchant = _merchant(db)
    counts = {"buyers": 0, "sellers": 0, "sales": 0, "purchases": 0, "expenses": 0, "skipped": 0}
    errors = []
    seen_invoice_numbers = set()
    seen_bill_numbers = set()

    def unique_import_number(value: str, prefix: str, model) -> str:
        base = value.strip() or f"{prefix}-{datetime.utcnow().strftime('%Y%m%d%H%M%S%f')}"
        candidate = base
        suffix = 2
        column_name = "invoice_number" if model is Invoice else "bill_number"
        while (
            candidate.casefold() in seen_invoice_numbers | seen_bill_numbers
            or db.execute(
                text(
                    f"SELECT 1 FROM {model.__tablename__} "
                    f"WHERE lower({column_name}) = lower(:number) LIMIT 1"
                ),
                {"number": candidate},
            ).first()
        ):
            candidate = f"{base}-IMP-{suffix}"
            suffix += 1
        return candidate
    try:
        for raw in rows:
            row = _normalized_import_row(raw)
            record_type = str(row.get("type", "expense")).lower()
            name = str(row.get("name", "") or "").strip()
            amount = _number(row.get("amount", 0))
            if not name or (amount <= 0 and record_type not in {"buyer", "customer", "seller", "supplier"}):
                continue
            if record_type in {"buyer", "customer"}:
                if db.query(Customer).filter(Customer.merchant_id == merchant.id, Customer.name == name).first():
                    counts["skipped"] += 1; errors.append(f"Buyer already exists: {name}"); continue
                db.add(Customer(merchant_id=merchant.id, name=name, phone=str(row.get("phone", "")), email=str(row.get("email", "")), address=str(row.get("address", "")), credit_period_days=_integer(row.get("credit_days"), 15), credit_limit=_number(row.get("credit_limit"), 500000)))
                counts["buyers"] += 1
            elif record_type in {"seller", "supplier"}:
                if db.query(Supplier).filter(Supplier.merchant_id == merchant.id, Supplier.name == name).first():
                    counts["skipped"] += 1; errors.append(f"Seller already exists: {name}"); continue
                db.add(Supplier(merchant_id=merchant.id, name=name, contact_person=str(row.get("contact_person", "")), phone=str(row.get("phone", "")), email=str(row.get("email", "")), category=str(row.get("category", "Inventory Supplier")), criticality=str(row.get("criticality", "HIGH")).upper(), payment_terms=str(row.get("payment_terms", "NET_15")).upper()))
                counts["sellers"] += 1
            elif record_type in {"sale", "sales", "invoice"}:
                invoice_number = str(row.get("invoice_number", "") or "").strip()
                existing_invoice = db.query(Invoice).filter(Invoice.invoice_number == invoice_number).first() if invoice_number else None
                if existing_invoice and existing_invoice.merchant_id == merchant.id:
                    counts["skipped"] += 1; errors.append(f"Invoice already exists: {invoice_number}"); continue
                invoice_number = unique_import_number(invoice_number, "IMP-INV", Invoice)
                seen_invoice_numbers.add(invoice_number.casefold())
                buyer = next((item for item in db.query(Customer).filter(Customer.merchant_id == merchant.id).all() if item.name.strip().casefold() == name.casefold()), None)
                if not buyer:
                    buyer = Customer(merchant_id=merchant.id, name=name); db.add(buyer); db.flush(); counts["buyers"] += 1
                due_days = _integer(row.get("due_days"), 15)
                paid_amount = min(amount, max(0.0, _number(row.get("paid_amount"))))
                invoice = Invoice(merchant_id=merchant.id, customer_id=buyer.id, invoice_number=invoice_number, issue_date=datetime.utcnow(), due_date=datetime.utcnow() + timedelta(days=due_days), total_amount=amount, paid_amount=paid_amount, outstanding_amount=amount - paid_amount, status="PAID" if paid_amount == amount else "PARTIALLY_PAID" if paid_amount else "ISSUED", payment_terms_days=due_days)
                db.add(invoice); db.flush()
                buyer.total_purchases_val = (buyer.total_purchases_val or 0) + amount
                buyer.total_paid_val = (buyer.total_paid_val or 0) + paid_amount
                buyer.current_outstanding = (buyer.current_outstanding or 0) + amount - paid_amount
                buyer.total_transactions_count = (buyer.total_transactions_count or 0) + 1
                if paid_amount: _post_cash_delta(db, paid_amount, f"Imported customer payment for invoice {invoice_number}", "PAYMENT", invoice.id, owner.username, True, "1010", "4010")
                if invoice.outstanding_amount: _post_cash_delta(db, invoice.outstanding_amount, f"Imported credit sale for invoice {invoice_number}", "SALE", invoice.id, owner.username, False, "1020", "4010")
                counts["sales"] += 1
            elif record_type in {"purchase", "purchases", "bill"}:
                bill_number = str(row.get("bill_number", "") or "").strip()
                existing_bill = db.query(SupplierPayable).filter(SupplierPayable.bill_number == bill_number).first() if bill_number else None
                if existing_bill and existing_bill.supplier and existing_bill.supplier.merchant_id == merchant.id:
                    counts["skipped"] += 1; errors.append(f"Bill already exists: {bill_number}"); continue
                bill_number = unique_import_number(bill_number, "IMP-BILL", SupplierPayable)
                seen_bill_numbers.add(bill_number.casefold())
                seller = next((item for item in db.query(Supplier).filter(Supplier.merchant_id == merchant.id).all() if item.name.strip().casefold() == name.casefold()), None)
                if not seller:
                    seller = Supplier(merchant_id=merchant.id, name=name); db.add(seller); db.flush(); counts["sellers"] += 1
                due_days = _integer(row.get("due_days"), 15)
                paid_amount = min(amount, max(0.0, _number(row.get("paid_amount"))))
                payable = SupplierPayable(supplier_id=seller.id, bill_number=bill_number, purchase_date=datetime.utcnow(), due_date=datetime.utcnow() + timedelta(days=due_days), total_amount=amount, paid_amount=paid_amount, outstanding_amount=amount - paid_amount, status="PAID" if paid_amount == amount else "PARTIALLY_PAID" if paid_amount else "UNPAID")
                db.add(payable); db.flush()
                seller.current_payable = (seller.current_payable or 0) + amount - paid_amount
                if paid_amount: _post_cash_delta(db, paid_amount, f"Imported supplier payment for bill {bill_number}", "SUPPLIER_PAYMENT", payable.id, owner.username, False, "2010", "1010")
                _post_cash_delta(db, amount, f"Imported inventory purchase for bill {bill_number}", "PURCHASE", payable.id, owner.username, False, "5010", "2010")
                counts["purchases"] += 1
            else:
                category_name, category_type = ExpenseService.classify_expense(name)
                category = db.query(ExpenseCategory).filter(ExpenseCategory.name == category_name).first()
                if not category:
                    category = ExpenseCategory(name=category_name, type=category_type); db.add(category); db.flush()
                expense = Expense(merchant_id=merchant.id, category_id=category.id, title=name, amount=amount, expense_date=datetime.utcnow(), is_recurring=str(row.get("recurring", "false")).lower() in {"true", "yes", "1"}, frequency="MONTHLY" if str(row.get("recurring", "false")).lower() in {"true", "yes", "1"} else "ONE_TIME")
                db.add(expense); db.flush()
                _post_cash_delta(db, amount, f"Imported expense paid: {name}", "EXPENSE", expense.id, owner.username, False, "5050", "1010")
                counts["expenses"] += 1
        imported = counts["buyers"] + counts["sellers"] + counts["sales"] + counts["purchases"] + counts["expenses"]
    except (SQLAlchemyError, TypeError, ValueError) as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Import could not be saved: {exc}") from exc
    if not imported:
        raise HTTPException(status_code=400, detail="No valid records found. Include type, name, and amount columns.")
    db.add(AuditLog(actor=owner.username, action="IMPORT_BUSINESS_FILE", details=f"Imported {imported} records from {file.filename}"))
    db.commit()
    return {"status": "imported", "filename": file.filename, "imported": imported, "errors": errors[:50], **counts}

@router.post("/owner/starter-data")
def add_starter_data(authorization: Optional[str] = Header(default=None), db: Session = Depends(get_db)):
    owner = _owner(authorization, db)
    merchant = _merchant(db)
    if db.query(Customer).count() or db.query(Supplier).count() or db.query(Invoice).count() or db.query(SupplierPayable).count() or db.query(Expense).count():
        raise HTTPException(status_code=409, detail="Business data already exists")
    today = datetime.utcnow()
    buyer_one = Customer(merchant_id=merchant.id, name="Northstar Retail", phone="+91 90000 11111", email="accounts@northstar.example", credit_period_days=15, credit_limit=300000, reliability_score=86, on_time_payment_rate=0.9, avg_payment_delay_days=3, segment="RELIABLE")
    buyer_two = Customer(merchant_id=merchant.id, name="Greenline Stores", phone="+91 90000 22222", email="finance@greenline.example", credit_period_days=30, credit_limit=500000, reliability_score=64, on_time_payment_rate=0.68, avg_payment_delay_days=10, segment="SLOW_PAYER")
    seller_one = Supplier(merchant_id=merchant.id, name="Sunrise Foods", contact_person="Meera Shah", phone="+91 90000 33333", email="billing@sunrise.example", category="FMCG", criticality="HIGH", payment_terms="NET_15")
    seller_two = Supplier(merchant_id=merchant.id, name="Swift Logistics", contact_person="Arjun Rao", phone="+91 90000 44444", email="ops@swift.example", category="Logistics", criticality="MEDIUM", payment_terms="NET_30")
    db.add_all([buyer_one, buyer_two, seller_one, seller_two])
    db.flush()
    sale_one = Invoice(merchant_id=merchant.id, customer_id=buyer_one.id, invoice_number="START-INV-001", issue_date=today, due_date=today + timedelta(days=7), total_amount=180000, paid_amount=60000, outstanding_amount=120000, status="PARTIALLY_PAID", payment_terms_days=7)
    sale_two = Invoice(merchant_id=merchant.id, customer_id=buyer_two.id, invoice_number="START-INV-002", issue_date=today - timedelta(days=5), due_date=today + timedelta(days=25), total_amount=260000, paid_amount=0, outstanding_amount=260000, status="ISSUED", payment_terms_days=30)
    bill = SupplierPayable(supplier_id=seller_one.id, bill_number="START-BILL-001", purchase_date=today, due_date=today + timedelta(days=10), total_amount=95000, outstanding_amount=95000, status="UNPAID", priority_level="HIGH")
    buyer_one.total_purchases_val = 180000; buyer_one.total_paid_val = 60000; buyer_one.current_outstanding = 120000; buyer_one.total_transactions_count = 1
    buyer_two.total_purchases_val = 260000; buyer_two.current_outstanding = 260000; buyer_two.total_transactions_count = 1
    seller_one.current_payable = 95000
    category = db.query(ExpenseCategory).filter(ExpenseCategory.name == "Operations").first()
    if not category:
        category = ExpenseCategory(name="Operations", type="VARIABLE")
        db.add(category)
        db.flush()
    expense_one = Expense(merchant_id=merchant.id, category_id=category.id, title="Warehouse utilities", amount=18000, expense_date=today, is_recurring=True, frequency="MONTHLY")
    expense_two = Expense(merchant_id=merchant.id, category_id=category.id, title="Delivery fuel", amount=12000, expense_date=today, is_recurring=False, frequency="ONE_TIME")
    expense_three = Expense(merchant_id=merchant.id, category_id=category.id, title="Packaging supplies", amount=8500, expense_date=today, is_recurring=False, frequency="ONE_TIME")
    db.add_all([sale_one, sale_two, bill, expense_one, expense_two, expense_three])
    db.add(AuditLog(actor=owner.username, action="ADD_STARTER_DATA", details="Added small starter business dataset"))
    db.commit()
    return {"status": "added", "buyers": 2, "sellers": 2, "sales": 2, "purchases": 1, "expenses": 3, "total_records": 10}

@router.delete("/owner/business-data")
def clear_business_data(authorization: Optional[str] = Header(default=None), db: Session = Depends(get_db)):
    owner = _owner(authorization, db)
    scoped_models = (Payment, RepaymentPrediction, Invoice, ActionApproval, AIAction, SupplierPayable, Expense, Customer, Supplier,
                     AuditLog, CashflowForecast, LedgerEntry, SimulationRun, RazorpayWebhookLog)
    for model in scoped_models:
        db.query(model).filter(model.merchant_id == owner.merchant_id).delete(synchronize_session=False)
    merchant = db.query(Merchant).filter(Merchant.id == owner.merchant_id).first()
    if merchant:
        merchant.current_cash = 0.0
    db.add(AuditLog(actor=owner.username, action="CLEAR_BUSINESS_DATA", details="Removed all business and demo records"))
    db.commit()
    return {"status": "cleared"}

@router.post("/seed")
def seed_dataset(db: Session = Depends(get_db)):
    raise HTTPException(status_code=410, detail="Synthetic demo seeding has been removed")

@router.get("/dashboard/kpis")
def get_dashboard_kpis(db: Session = Depends(get_db)):
    merchant = db.query(Merchant).first()
    if not merchant:
        merchant = _merchant(db)

    _ensure_ledger_accounts(db)
    LedgerService.reconcile_account_balances(db)
    cash_acct = db.query(LedgerAccount).filter(LedgerAccount.code == "1010").first()
    current_cash = float(merchant.current_cash) if merchant.current_cash is not None else (float(cash_acct.balance) if cash_acct else 450000.0)

    invoices = db.query(Invoice).all()
    total_receivables = sum(i.outstanding_amount for i in invoices)
    
    payables = db.query(SupplierPayable).all()
    total_payables = sum(p.outstanding_amount for p in payables)

    revenue_at_risk = 0.0
    for inv in invoices:
        if inv.outstanding_amount <= 0:
            continue
        pred = (
            db.query(RepaymentPrediction)
            .filter(RepaymentPrediction.invoice_id == inv.id)
            .order_by(RepaymentPrediction.created_at.desc())
            .first()
        )
        probability = pred.repayment_probability_15d if pred else min(0.98, max(0.15, inv.customer.on_time_payment_rate if inv.customer else 0.5))
        revenue_at_risk += inv.outstanding_amount * (1.0 - probability)

    cf = CashflowService.forecast_7_15_days(db, forecast_days=7)
    expected_recovery_7d = cf["total_expected_inflow"]
    min_7d_cash = cf["min_projected_cash"]

    liquidity_score = min(100.0, (min_7d_cash / max(1.0, merchant.min_cash_buffer)) * 100.0)
    receivables_quality = max(0.0, 100.0 - ((revenue_at_risk / max(1.0, total_receivables)) * 100.0))
    payable_pressure = max(0.0, 100.0 - ((total_payables / max(1.0, current_cash + expected_recovery_7d)) * 100.0))
    expenses = db.query(Expense).all()
    anomaly_count = sum(1 for e in expenses if e.is_anomaly)
    expense_stability = max(0.0, 100.0 - anomaly_count * 18.0)
    customers = db.query(Customer).all()
    customer_base = sum(c.reliability_score for c in customers) / max(1, len(customers))
    health_score = round(
        (liquidity_score * 0.30)
        + (receivables_quality * 0.25)
        + (payable_pressure * 0.20)
        + (expense_stability * 0.10)
        + (customer_base * 0.15),
        1,
    )

    return {
        "current_cash": round(current_cash, 2),
        "min_cash_buffer": round(merchant.min_cash_buffer, 2),
        "total_receivables": round(total_receivables, 2),
        "total_payables": round(total_payables, 2),
        "revenue_at_risk": round(revenue_at_risk, 2),
        "expected_recovery_7d": round(expected_recovery_7d, 2),
        "min_7d_cash": round(min_7d_cash, 2),
        "liquidity_status": "LIQUIDITY_RISK" if cf["has_liquidity_violation"] else "HEALTHY",
        "financial_health_score": min(100.0, max(0.0, health_score)),
        "health_factors": {
            "liquidity": round(liquidity_score, 1),
            "receivable_quality": round(receivables_quality, 1),
            "payable_pressure": round(payable_pressure, 1),
            "expense_stability": round(expense_stability, 1),
            "customer_base_reliability": round(customer_base, 1)
        }
    }

@router.get("/cashflow/forecast")
def get_cashflow_forecast(
    days: int = Query(15, ge=7, le=30),
    buffer: Optional[float] = None,
    db: Session = Depends(get_db)
):
    return CashflowService.forecast_7_15_days(db, forecast_days=days, custom_buffer=buffer)

@router.get("/receivables")
def get_receivables(db: Session = Depends(get_db)):
    invoices = db.query(Invoice).filter(Invoice.outstanding_amount > 0).all()
    results = []

    for inv in invoices:
        cust = inv.customer
        if not cust: continue

        stored_prediction = (
            db.query(RepaymentPrediction)
            .filter(RepaymentPrediction.invoice_id == inv.id)
            .order_by(RepaymentPrediction.created_at.desc())
            .first()
        )
        if stored_prediction:
            pred = {
                "repayment_probability_15d": stored_prediction.repayment_probability_15d,
                "expected_payment_days": stored_prediction.expected_payment_days,
                "confidence": stored_prediction.confidence_level,
            }
        else:
            pred = ml_repayment_service.predict_invoice_repayment(cust, inv.outstanding_amount)
        prob = pred["repayment_probability_15d"]
        exp_days = pred["expected_payment_days"]

        # Priority formula
        prio = round((inv.outstanding_amount / 10000.0) * prob * (1.5 if inv.status == "OVERDUE" else 1.0), 1)

        results.append({
            "invoice_id": inv.id,
            "invoice_number": inv.invoice_number,
            "customer_id": cust.id,
            "customer_name": cust.name,
            "segment": cust.segment,
            "outstanding_amount": round(inv.outstanding_amount, 2),
            "total_amount": round(inv.total_amount, 2),
            "issue_date": inv.issue_date.strftime("%Y-%m-%d") if inv.issue_date else None,
            "due_date": inv.due_date.strftime("%Y-%m-%d") if inv.due_date else None,
            "status": inv.status,
            "reliability_score": round(cust.reliability_score, 1),
            "repayment_probability_15d": prob,
            "expected_payment_days": exp_days,
            "priority_score": prio,
            "prediction_confidence": pred.get("confidence", "MEDIUM"),
            "expected_recoverable_amount": round(inv.outstanding_amount * prob, 2),
            "suggested_action": "SEND_PAYMENT_LINK" if prob >= 0.85 else ("SEND_REMINDER" if prob >= 0.65 else ("HUMAN_ESCALATION" if prob >= 0.40 else "WAIT"))
        })

    results.sort(key=lambda r: r["priority_score"], reverse=True)
    return {"receivables": results}

@router.get("/customers")
def get_customers(db: Session = Depends(get_db)):
    customers = db.query(Customer).order_by(Customer.current_outstanding.desc()).all()
    return {
        "customers": [{
            "id": c.id,
            "name": c.name,
            "phone": c.phone,
            "email": c.email,
            "segment": c.segment,
            "behavior_trend": c.behavior_trend,
            "reliability_score": round(c.reliability_score, 1),
            "on_time_payment_rate": round(c.on_time_payment_rate * 100, 1),
            "avg_payment_delay_days": c.avg_payment_delay_days,
            "current_outstanding": round(c.current_outstanding, 2),
            "total_purchases_val": round(c.total_purchases_val, 2),
            "total_paid_val": round(c.total_paid_val, 2),
            "overdue_count": c.overdue_count,
            "total_transactions_count": c.total_transactions_count,
            "has_active_p2p": c.has_active_p2p,
            "opt_out_contact": c.opt_out_contact,
        } for c in customers]
    }

@router.get("/customers/{customer_id}")
def get_customer_profile(customer_id: str, db: Session = Depends(get_db)):
    cust = CustomerIntelligenceService.update_customer_intelligence(db, customer_id)
    if not cust:
        raise HTTPException(status_code=404, detail="Customer not found")

    invoices = db.query(Invoice).filter(Invoice.customer_id == customer_id).all()
    
    return {
        "customer": {
            "id": cust.id,
            "name": cust.name,
            "phone": cust.phone,
            "email": cust.email,
            "reliability_score": round(cust.reliability_score, 1),
            "segment": cust.segment,
            "behavior_trend": cust.behavior_trend,
            "on_time_payment_rate": round(cust.on_time_payment_rate * 100, 1),
            "avg_payment_delay_days": cust.avg_payment_delay_days,
            "max_payment_delay_days": cust.max_payment_delay_days,
            "total_purchases_val": round(cust.total_purchases_val, 2),
            "total_paid_val": round(cust.total_paid_val, 2),
            "current_outstanding": round(cust.current_outstanding, 2),
            "overdue_count": cust.overdue_count,
            "total_transactions_count": cust.total_transactions_count,
            "has_active_p2p": cust.has_active_p2p,
            "p2p_amount": cust.p2p_amount,
            "p2p_promised_date": cust.p2p_promised_date,
            "opt_out_contact": cust.opt_out_contact
        },
        "invoices": [{
            "id": i.id,
            "invoice_number": i.invoice_number,
            "amount": i.total_amount,
            "outstanding": i.outstanding_amount,
            "status": i.status,
            "due_date": i.due_date.strftime("%Y-%m-%d") if i.due_date else None
        } for i in invoices]
    }

@router.get("/payables")
def get_payables(db: Session = Depends(get_db)):
    payables = db.query(SupplierPayable).filter(SupplierPayable.outstanding_amount > 0).all()
    results = []

    for sp in payables:
        sup = sp.supplier
        results.append({
            "id": sp.id,
            "supplier_id": sup.id if sup else None,
            "supplier_name": sup.name if sup else "Supplier",
            "bill_number": sp.bill_number,
            "total_amount": round(sp.total_amount, 2),
            "outstanding_amount": round(sp.outstanding_amount, 2),
            "due_date": sp.due_date.strftime("%Y-%m-%d") if sp.due_date else None,
            "priority_level": sp.priority_level,
            "criticality": sup.criticality if sup else "HIGH",
            "early_discount_percent": sup.early_discount_percent if sup else 1.0,
            "late_penalty_percent": sup.late_penalty_percent if sup else 1.5,
            "payment_terms": sup.payment_terms if sup else "NET_15",
            "recommended_action": "PRIORITY_PAY" if sp.priority_level == "CRITICAL" else "PAY_IN_TIMEFRAME"
        })

    results.sort(key=lambda x: (x["due_date"] or "9999-12-31"))
    return {"payables": results}

@router.get("/expenses")
def get_expenses(db: Session = Depends(get_db)):
    expenses = db.query(Expense).order_by(Expense.expense_date.desc()).all()
    results = []

    for exp in expenses:
        category = db.query(ExpenseCategory).filter(ExpenseCategory.id == exp.category_id).first()
        results.append({
            "id": exp.id,
            "title": exp.title,
            "category": category.name if category else "Miscellaneous",
            "category_type": category.type if category else "MISC",
            "amount": round(exp.amount, 2),
            "date": exp.expense_date.strftime("%Y-%m-%d") if exp.expense_date else None,
            "is_recurring": exp.is_recurring,
            "frequency": exp.frequency,
            "historical_avg": exp.historical_avg,
            "is_anomaly": exp.is_anomaly,
            "anomaly_reason": exp.anomaly_reason
        })

    monthly_breakdown = {}
    for row in results:
        key = row["category"]
        monthly_breakdown[key] = round(monthly_breakdown.get(key, 0.0) + row["amount"], 2)

    return {"expenses": results, "monthly_breakdown": monthly_breakdown}

@router.get("/ledger")
def get_ledger(db: Session = Depends(get_db)):
    _ensure_ledger_accounts(db)
    bs = LedgerService.get_balance_sheet(db)
    entries = db.query(AuditLog).order_by(AuditLog.timestamp.desc()).limit(50).all()
    
    return {
        "balance_sheet": bs,
        "ledger_entries": LedgerService.get_ledger_rows(db),
        "audit_trail": [{
            "id": e.id,
            "timestamp": e.timestamp.strftime("%Y-%m-%d %H:%M:%S") if e.timestamp else None,
            "actor": e.actor,
            "action": e.action,
            "details": e.details
        } for e in entries]
    }

@router.get("/actions/today")
def get_today_action_plan(buffer: Optional[float] = None, db: Session = Depends(get_db)):
    return DecisionEngine.generate_daily_action_plan(db, custom_buffer=buffer)

@router.get("/actions")
def get_actions(db: Session = Depends(get_db)):
    plan = DecisionEngine.generate_daily_action_plan(db)
    return plan

@router.post("/actions/approve/{action_id}")
def approve_action(action_id: str, db: Session = Depends(get_db)):
    act = PolicyEngine.approve_action(db, action_id)
    if not act:
        raise HTTPException(status_code=404, detail="Action not found")
    return {"status": "approved", "action_id": action_id, "action_status": act.status}

@router.post("/actions/reject/{action_id}")
def reject_action(action_id: str, payload: Dict = Body(default={}), db: Session = Depends(get_db)):
    act = db.query(AIAction).filter(AIAction.id == action_id).first()
    if not act:
        raise HTTPException(status_code=404, detail="Action not found")
    act.status = "REJECTED"
    approval = db.query(ActionApproval).filter(ActionApproval.action_id == action_id).first()
    if not approval:
        approval = ActionApproval(action_id=action_id)
        db.add(approval)
    approval.status = "REJECTED"
    approval.reviewed_by = payload.get("reviewer", "User")
    approval.review_notes = payload.get("notes", "Rejected from approval center")
    approval.reviewed_at = datetime.utcnow()
    db.add(AuditLog(
        actor=approval.reviewed_by,
        action="REJECT_AI_ACTION",
        details=f"Rejected AI action {act.action_type} for {act.target_name}",
    ))
    db.commit()
    return {"status": "rejected", "action_id": action_id, "action_status": act.status}

@router.post("/actions/execute/{action_id}")
def execute_action(action_id: str, db: Session = Depends(get_db)):
    act = db.query(AIAction).filter(AIAction.id == action_id).first()
    if not act:
        raise HTTPException(status_code=404, detail="Action not found")
    if act.status != "APPROVED":
        raise HTTPException(status_code=409, detail="Approve this AI action before execution")

    payload = {"action_id": act.id, "status": "EXECUTED"}
    if act.action_type == "SEND_PAYMENT_LINK":
        customer = db.query(Customer).filter(Customer.id == act.target_id).first()
        invoice = (
            db.query(Invoice)
            .filter(Invoice.customer_id == act.target_id, Invoice.outstanding_amount > 0)
            .order_by(Invoice.due_date.asc())
            .first()
        )
        if not customer or not invoice:
            raise HTTPException(status_code=400, detail="No active invoice available for payment-link execution")
        link = RazorpayService.create_payment_link(
            invoice.id,
            customer.name,
            float(invoice.outstanding_amount),
            invoice.due_date.strftime("%Y-%m-%d") if invoice.due_date else datetime.utcnow().strftime("%Y-%m-%d"),
        )
        payload["payment_link"] = link
        act.approval_reason = act.approval_reason or "Executed via Razorpay AI workflow"

    act.status = "EXECUTED"
    db.add(AuditLog(
        actor="AI_ENGINE",
        action="EXECUTE_AI_ACTION",
        details=f"Executed AI action {act.action_type} for {act.target_name}",
    ))
    db.commit()
    return {"status": "executed", "action_id": action_id, "action_status": act.status, **payload}

@router.get("/ai/insights")
def get_ai_insights(db: Session = Depends(get_db)):
    kpis = get_dashboard_kpis(db)
    plan = DecisionEngine.generate_daily_action_plan(db)
    top_actions = sorted(plan["action_items"], key=lambda item: item["priority_score"], reverse=True)[:5]
    return {
        "liquidity_status": kpis["liquidity_status"],
        "financial_health_score": kpis["financial_health_score"],
        "top_actions": top_actions,
        "recommended_focus": [
            "Push high-confidence payment links for reliable buyers before 5-day due dates.",
            "Protect minimum cash buffer before approving supplier-risky payments.",
            "Flag anomalies in recurring expenses before they distort the monthly run-rate.",
        ],
        "smart_summary": (
            f"Current cash is ₹{kpis['current_cash']:,.2f}. The engine expects ₹{kpis['expected_recovery_7d']:,.2f} in recoveries over the next 7 days, "
            f"with a minimum projected cash of ₹{kpis['min_7d_cash']:,.2f}."
        ),
    }

@router.get("/ai/overview")
def get_ai_overview(db: Session = Depends(get_db)):
    return AIIntelligenceService.overview(db)

@router.post("/ai/invoice/analyze")
def analyze_invoice_with_ai(payload: Dict = Body(...)):
    return AIIntelligenceService.analyze_invoice(payload)

@router.get("/ai/compliance")
def get_ai_compliance(db: Session = Depends(get_db)):
    return AIIntelligenceService.compliance(db)

@router.post("/ai/scenario")
def run_ai_scenario(payload: Dict = Body(default={}), db: Session = Depends(get_db)):
    return AIIntelligenceService.scenario(db, payload)

@router.post("/ai/voice/intent")
def resolve_voice_intent(payload: Dict = Body(...)):
    return AIIntelligenceService.voice_intent(str(payload.get("text", "")))

@router.post("/ai/feedback")
def record_ai_feedback(payload: Dict = Body(...), db: Session = Depends(get_db)):
    action_id = str(payload.get("action_id", ""))
    if not action_id:
        raise HTTPException(status_code=400, detail="action_id is required")
    return AIIntelligenceService.record_feedback(db, action_id, str(payload.get("outcome", "UNKNOWN")), str(payload.get("notes", "")))

@router.post("/simulator/run")
def run_simulation(payload: Dict = Body(default={}), db: Session = Depends(get_db)):
    buf = payload.get("min_buffer", 200000.0)
    return SimulationService.run_strategy_simulation(db, custom_buffer=buf)

@router.get("/evaluation/benchmark")
def get_benchmark(db: Session = Depends(get_db)):
    return EvaluationService.get_benchmark_report(db)

@router.post("/copilot/chat")
def copilot_chat(payload: Dict = Body(...), db: Session = Depends(get_db)):
    question = payload.get("question", "")
    return CopilotService.query(db, question)

@router.get("/scenarios/list")
def list_scenarios():
    return {"scenarios": DemoScenariosService.get_all_scenarios()}

@router.post("/scenarios/apply/{scenario_id}")
def apply_scenario(scenario_id: str, db: Session = Depends(get_db)):
    return DemoScenariosService.apply_scenario(db, scenario_id)

@router.post("/razorpay/payment-link")
def create_razorpay_link(payload: Dict = Body(...), db: Session = Depends(get_db)):
    inv_id = payload.get("invoice_id")
    invoice = db.query(Invoice).filter(Invoice.id == inv_id).first() if inv_id else None
    if invoice:
        if invoice.outstanding_amount <= 0:
            raise HTTPException(status_code=409, detail="Invoice is already paid")
        inv_id = invoice.id
        name = invoice.customer.name if invoice.customer else payload.get("customer_name", "Customer")
        amt = invoice.outstanding_amount
        due = invoice.due_date.strftime("%Y-%m-%d") if invoice.due_date else datetime.utcnow().strftime("%Y-%m-%d")
    else:
        inv_id = inv_id or "inv_demo"
        name = payload.get("customer_name", "Customer A")
        amt = float(payload.get("amount", 200000.0))
        due = payload.get("due_date", "2026-09-15")
    return RazorpayService.create_payment_link(inv_id, name, amt, due)

@router.post("/razorpay/webhook")
async def handle_razorpay_webhook(request: Request, razorpay_signature: Optional[str] = Header(default=None, alias="X-Razorpay-Signature"), db: Session = Depends(get_db)):
    raw_body = await request.body()
    if not RazorpayService.verify_webhook_signature(raw_body, razorpay_signature):
        raise HTTPException(status_code=401, detail="Invalid Razorpay webhook signature")
    try:
        payload = json.loads(raw_body)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail="Invalid webhook JSON") from exc
    return RazorpayService.process_webhook(db, payload)

@router.get("/reports")
def get_reports(db: Session = Depends(get_db)):
    kpis = get_dashboard_kpis(db)
    plan = DecisionEngine.generate_daily_action_plan(db)
    expenses = get_expenses(db)
    payables = get_payables(db)["payables"]
    receivables = get_receivables(db)["receivables"]
    benchmark = EvaluationService.get_benchmark_report(db)

    return {
        "reports": [
            {
                "id": "daily_ai_financial_report",
                "title": "Daily AI Financial Report",
                "summary": (
                    f"Current cash INR {kpis['current_cash']:,.0f}; minimum forecast cash INR {kpis['min_7d_cash']:,.0f}; "
                    f"status {kpis['liquidity_status'].replace('_', ' ')}."
                ),
                "metrics": {
                    "current_cash": kpis["current_cash"],
                    "expected_recovery_7d": kpis["expected_recovery_7d"],
                    "revenue_at_risk": kpis["revenue_at_risk"],
                    "actions": plan["total_actions"],
                },
            },
            {
                "id": "customer_receivable_report",
                "title": "Customer Receivable Report",
                "summary": f"{len(receivables)} open receivable invoices sorted by expected recoverable cash and urgency.",
                "metrics": {
                    "total_receivables": kpis["total_receivables"],
                    "top_customer": receivables[0]["customer_name"] if receivables else None,
                    "top_expected_recoverable": receivables[0]["expected_recoverable_amount"] if receivables else 0,
                },
            },
            {
                "id": "supplier_payable_report",
                "title": "Supplier Payable Report",
                "summary": f"{len(payables)} supplier obligations require scheduling against the cash buffer.",
                "metrics": {
                    "total_payables": kpis["total_payables"],
                    "highest_priority_supplier": payables[0]["supplier_name"] if payables else None,
                },
            },
            {
                "id": "expense_report",
                "title": "Expense Report",
                "summary": "Monthly expense mix with anomaly detection and recurring expense signals.",
                "metrics": {
                    "monthly_breakdown": expenses["monthly_breakdown"],
                    "anomaly_count": len([e for e in expenses["expenses"] if e["is_anomaly"]]),
                },
            },
            {
                "id": "ai_action_performance_report",
                "title": "AI Action Performance Report",
                "summary": "Strategy and model performance calculated from the current synthetic dataset.",
                "metrics": benchmark["decision_benchmark"],
            },
        ]
    }

@router.get("/settings")
def get_settings(db: Session = Depends(get_db)):
    merchant = db.query(Merchant).first()
    return {
        "merchant": {
            "id": merchant.id if merchant else None,
            "name": merchant.name if merchant else "CashPilot Demo Merchant",
            "business_type": merchant.business_type if merchant else "Distributor/Wholesaler",
            "currency": merchant.currency if merchant else "INR",
            "min_cash_buffer": merchant.min_cash_buffer if merchant else 200000.0,
        },
        "policy_rules": PolicyEngine.POLICY_RULES,
        "security": {
            "authentication": "Demo bearer-token boundary ready; production deployments should connect an identity provider.",
            "audit_logging": "Enabled for scenario, action, ledger, and webhook events.",
            "llm_financial_control": "Disabled. Calculations come from database, deterministic services, and ML model outputs.",
        },
    }

@router.post("/settings")
def update_settings(payload: Dict = Body(...), db: Session = Depends(get_db)):
    merchant = db.query(Merchant).first()
    if not merchant:
        merchant = _merchant(db)
    if "min_cash_buffer" in payload:
        merchant.min_cash_buffer = float(payload["min_cash_buffer"])
    db.add(AuditLog(
        actor="USER",
        action="UPDATE_SETTINGS",
        details=f"Updated settings: {payload}",
    ))
    db.commit()
    return get_settings(db)

@router.post("/documents/structured-extract")
def structured_document_extract(payload: Dict = Body(...)):
    description = payload.get("description", "")
    amount = float(payload.get("amount", 0.0) or 0.0)
    category, category_type = ExpenseService.classify_expense(description)
    return {
        "vendor": payload.get("vendor"),
        "invoice_number": payload.get("invoice_number"),
        "date": payload.get("date"),
        "amount": amount,
        "tax": float(payload.get("tax", 0.0) or 0.0),
        "category": category,
        "category_type": category_type,
        "confidence": "LOW" if not description or amount <= 0 else "MEDIUM",
        "review_required": True,
        "message": "Fallback structured extraction prepared. Review before posting to ledger.",
    }

@router.post("/promise-to-pay/extract")
def extract_promise_to_pay(payload: Dict = Body(...)):
    text = payload.get("message", "")
    return PromiseToPayService.extract_promise(text)

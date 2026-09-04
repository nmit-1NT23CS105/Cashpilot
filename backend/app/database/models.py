from sqlalchemy import Column, String, Integer, Float, Boolean, DateTime, ForeignKey, Text, JSON, Enum
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
from .db import Base

def generate_uuid():
    return str(uuid.uuid4())

class Merchant(Base):
    __tablename__ = "merchants"

    id = Column(String, primary_key=True, default=generate_uuid)
    name = Column(String, nullable=False)
    business_type = Column(String, default="Distributor/Wholesaler")
    currency = Column(String, default="INR")
    min_cash_buffer = Column(Float, default=200000.0) # Default ₹2,00,000
    current_cash = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow)

    customers = relationship("Customer", back_populates="merchant")
    manufacturers = relationship("Manufacturer", back_populates="merchant")
    suppliers = relationship("Supplier", back_populates="merchant")

class Owner(Base):
    __tablename__ = "owners"

    id = Column(String, primary_key=True, default=generate_uuid)
    username = Column(String, unique=True, nullable=False, index=True)
    password_hash = Column(String, nullable=False)
    merchant_id = Column(String, ForeignKey("merchants.id"), index=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class Manufacturer(Base):
    __tablename__ = "manufacturers"

    id = Column(String, primary_key=True, default=generate_uuid)
    merchant_id = Column(String, ForeignKey("merchants.id"), index=True)
    name = Column(String, nullable=False)
    contact_person = Column(String)
    phone = Column(String)
    email = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)

    merchant = relationship("Merchant", back_populates="manufacturers")
    products = relationship("Product", back_populates="manufacturer")

class Supplier(Base):
    __tablename__ = "suppliers"

    id = Column(String, primary_key=True, default=generate_uuid)
    merchant_id = Column(String, ForeignKey("merchants.id"), index=True)
    name = Column(String, nullable=False)
    contact_person = Column(String)
    phone = Column(String)
    email = Column(String)
    category = Column(String, default="Inventory Supplier")
    criticality = Column(String, default="HIGH") # CRITICAL, HIGH, MEDIUM, LOW
    payment_terms = Column(String, default="NET_15") # NET_7, NET_15, NET_30
    early_discount_percent = Column(Float, default=2.0)
    late_penalty_percent = Column(Float, default=1.5)
    current_payable = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow)

    merchant = relationship("Merchant", back_populates="suppliers")
    payables = relationship("SupplierPayable", back_populates="supplier")

class Customer(Base):
    __tablename__ = "customers"

    id = Column(String, primary_key=True, default=generate_uuid)
    merchant_id = Column(String, ForeignKey("merchants.id"), index=True)
    name = Column(String, nullable=False)
    phone = Column(String)
    email = Column(String)
    address = Column(String)
    credit_period_days = Column(Integer, default=15)
    credit_limit = Column(Float, default=500000.0)
    
    # Intelligence Metrics
    reliability_score = Column(Float, default=75.0) # 0-100
    on_time_payment_rate = Column(Float, default=0.85) # 0.0 - 1.0
    avg_payment_delay_days = Column(Float, default=3.0)
    max_payment_delay_days = Column(Float, default=12.0)
    total_purchases_val = Column(Float, default=0.0)
    total_paid_val = Column(Float, default=0.0)
    current_outstanding = Column(Float, default=0.0)
    overdue_count = Column(Integer, default=0)
    total_transactions_count = Column(Integer, default=0)
    
    # Segment & Behavior Tag
    segment = Column(String, default="RELIABLE") # RELIABLE, SLOW_PAYER, HIGH_RISK, NEW_CUSTOMER, DETERIORATING, IMPROVING
    behavior_trend = Column(String, default="STABLE") # STABLE, DETERIORATING, IMPROVING
    
    # Promise to Pay
    has_active_p2p = Column(Boolean, default=False)
    p2p_amount = Column(Float, default=0.0)
    p2p_promised_date = Column(String, nullable=True)
    p2p_confidence = Column(Float, default=0.0)
    opt_out_contact = Column(Boolean, default=False)
    
    created_at = Column(DateTime, default=datetime.utcnow)

    merchant = relationship("Merchant", back_populates="customers")
    invoices = relationship("Invoice", back_populates="customer")

class ProductCategory(Base):
    __tablename__ = "product_categories"

    id = Column(String, primary_key=True, default=generate_uuid)
    name = Column(String, nullable=False)

class Product(Base):
    __tablename__ = "products"

    id = Column(String, primary_key=True, default=generate_uuid)
    manufacturer_id = Column(String, ForeignKey("manufacturers.id"), index=True)
    sku = Column(String, unique=True, index=True)
    name = Column(String, nullable=False)
    purchase_price = Column(Float, nullable=False)
    selling_price = Column(Float, nullable=False)
    stock_quantity = Column(Integer, default=100)
    created_at = Column(DateTime, default=datetime.utcnow)

    manufacturer = relationship("Manufacturer", back_populates="products")

class Invoice(Base):
    __tablename__ = "invoices"

    id = Column(String, primary_key=True, default=generate_uuid)
    merchant_id = Column(String, ForeignKey("merchants.id"), index=True)
    customer_id = Column(String, ForeignKey("customers.id"), index=True)
    invoice_number = Column(String, unique=True, index=True)
    issue_date = Column(DateTime, default=datetime.utcnow)
    due_date = Column(DateTime, index=True)
    total_amount = Column(Float, nullable=False)
    paid_amount = Column(Float, default=0.0)
    outstanding_amount = Column(Float, nullable=False)
    status = Column(String, default="ISSUED") # ISSUED, PARTIALLY_PAID, PAID, OVERDUE, DISPUTED
    payment_terms_days = Column(Integer, default=15)
    
    created_at = Column(DateTime, default=datetime.utcnow)

    customer = relationship("Customer", back_populates="invoices")
    payments = relationship("Payment", back_populates="invoice")
    predictions = relationship("RepaymentPrediction", back_populates="invoice")

class Payment(Base):
    __tablename__ = "payments"

    id = Column(String, primary_key=True, default=generate_uuid)
    invoice_id = Column(String, ForeignKey("invoices.id"), index=True)
    customer_id = Column(String, ForeignKey("customers.id"), index=True)
    merchant_id = Column(String, ForeignKey("merchants.id"), index=True)
    payment_date = Column(DateTime, default=datetime.utcnow)
    amount = Column(Float, nullable=False)
    payment_method = Column(String, default="UPI/Razorpay") # Razorpay, Bank_Transfer, Cash, Cheque
    status = Column(String, default="SUCCESS") # SUCCESS, FAILED, PARTIAL, REFUNDED
    transaction_reference = Column(String, nullable=True)
    razorpay_payment_id = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    invoice = relationship("Invoice", back_populates="payments")

class SupplierPayable(Base):
    __tablename__ = "supplier_payables"

    id = Column(String, primary_key=True, default=generate_uuid)
    supplier_id = Column(String, ForeignKey("suppliers.id"), index=True)
    merchant_id = Column(String, ForeignKey("merchants.id"), index=True)
    bill_number = Column(String)
    purchase_date = Column(DateTime, default=datetime.utcnow)
    due_date = Column(DateTime, index=True)
    total_amount = Column(Float, nullable=False)
    paid_amount = Column(Float, default=0.0)
    outstanding_amount = Column(Float, nullable=False)
    priority_level = Column(String, default="MEDIUM") # CRITICAL, HIGH, MEDIUM, LOW
    status = Column(String, default="UNPAID") # UNPAID, PARTIALLY_PAID, PAID
    created_at = Column(DateTime, default=datetime.utcnow)

    supplier = relationship("Supplier", back_populates="payables")

class ExpenseCategory(Base):
    __tablename__ = "expense_categories"

    id = Column(String, primary_key=True, default=generate_uuid)
    name = Column(String, nullable=False) # Fixed, Variable, Financial, Technology, Statutory, Miscellaneous
    type = Column(String, default="VARIABLE") # FIXED, VARIABLE, FINANCIAL, TECH, STATUTORY, MISC

class Expense(Base):
    __tablename__ = "expenses"

    id = Column(String, primary_key=True, default=generate_uuid)
    merchant_id = Column(String, ForeignKey("merchants.id"), index=True)
    category_id = Column(String, ForeignKey("expense_categories.id"))
    title = Column(String, nullable=False)
    amount = Column(Float, nullable=False)
    expense_date = Column(DateTime, default=datetime.utcnow, index=True)
    is_recurring = Column(Boolean, default=False)
    frequency = Column(String, default="MONTHLY") # MONTHLY, WEEKLY, DAILY, ONE_TIME
    historical_avg = Column(Float, nullable=True)
    is_anomaly = Column(Boolean, default=False)
    anomaly_reason = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class LedgerAccount(Base):
    __tablename__ = "ledger_accounts"

    id = Column(String, primary_key=True, default=generate_uuid)
    code = Column(String, unique=True, index=True)
    name = Column(String, nullable=False)
    type = Column(String, nullable=False) # ASSET, LIABILITY, EQUITY, REVENUE, EXPENSE
    balance = Column(Float, default=0.0)

class LedgerEntry(Base):
    __tablename__ = "ledger_entries"

    id = Column(String, primary_key=True, default=generate_uuid)
    entry_number = Column(String, unique=True, index=True)
    merchant_id = Column(String, ForeignKey("merchants.id"), index=True)
    transaction_date = Column(DateTime, default=datetime.utcnow, index=True)
    debit_account = Column(String, ForeignKey("ledger_accounts.code"))
    credit_account = Column(String, ForeignKey("ledger_accounts.code"))
    amount = Column(Float, nullable=False)
    description = Column(String, nullable=False)
    source_type = Column(String, default="MANUAL") # SALE, PURCHASE, PAYMENT, SUPPLIER_PAYMENT, EXPENSE
    source_id = Column(String, nullable=True)
    is_approved = Column(Boolean, default=True)
    created_by = Column(String, default="SYSTEM")
    created_at = Column(DateTime, default=datetime.utcnow)

class RepaymentPrediction(Base):
    __tablename__ = "repayment_predictions"

    id = Column(String, primary_key=True, default=generate_uuid)
    invoice_id = Column(String, ForeignKey("invoices.id"), index=True)
    customer_id = Column(String, ForeignKey("customers.id"), index=True)
    merchant_id = Column(String, ForeignKey("merchants.id"), index=True)
    repayment_probability_15d = Column(Float, nullable=False) # 0.00 to 1.00
    expected_payment_days = Column(Float, nullable=False) # e.g. 3.2 days
    confidence_level = Column(String, default="HIGH") # HIGH, MEDIUM, LOW
    factors = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    invoice = relationship("Invoice", back_populates="predictions")

class CashflowForecast(Base):
    __tablename__ = "cashflow_forecasts"

    id = Column(String, primary_key=True, default=generate_uuid)
    forecast_date = Column(String, index=True) # YYYY-MM-DD
    day_offset = Column(Integer) # 0 to 15
    starting_cash = Column(Float, nullable=False)
    expected_inflow = Column(Float, nullable=False)
    expected_outflow = Column(Float, nullable=False)
    projected_ending_cash = Column(Float, nullable=False)
    is_liquidity_violation = Column(Boolean, default=False)
    violation_shortfall = Column(Float, default=0.0)
    merchant_id = Column(String, ForeignKey("merchants.id"), index=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class AIAction(Base):
    __tablename__ = "ai_actions"

    id = Column(String, primary_key=True, default=generate_uuid)
    action_type = Column(String, nullable=False) # SEND_PAYMENT_LINK, SEND_REMINDER, HUMAN_ESCALATION, WAIT, PRIORITIZE_SUPPLIER, REVIEW_EXPENSE
    target_type = Column(String, nullable=False) # CUSTOMER, SUPPLIER, EXPENSE
    target_id = Column(String, nullable=False)
    merchant_id = Column(String, ForeignKey("merchants.id"), index=True)
    target_name = Column(String, nullable=False)
    amount = Column(Float, default=0.0)
    priority_score = Column(Float, default=0.0)
    confidence = Column(Float, default=0.90)
    explanation = Column(Text, nullable=False)
    status = Column(String, default="RECOMMENDED") # RECOMMENDED, APPROVED, REJECTED, EXECUTED, PAUSED_FOR_LIQUIDITY
    requires_approval = Column(Boolean, default=False)
    approval_reason = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class ActionApproval(Base):
    __tablename__ = "action_approvals"

    id = Column(String, primary_key=True, default=generate_uuid)
    action_id = Column(String, ForeignKey("ai_actions.id"), index=True)
    merchant_id = Column(String, ForeignKey("merchants.id"), index=True)
    status = Column(String, default="PENDING") # PENDING, APPROVED, REJECTED
    reviewed_by = Column(String, default="User")
    review_notes = Column(String, nullable=True)
    reviewed_at = Column(DateTime, nullable=True)

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(String, primary_key=True, default=generate_uuid)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    actor = Column(String, default="AI_ENGINE") # AI_ENGINE, USER, SYSTEM, WEBHOOK
    action = Column(String, nullable=False)
    details = Column(Text, nullable=False)
    merchant_id = Column(String, ForeignKey("merchants.id"), index=True)
    metadata_json = Column(JSON, nullable=True)

class SimulationRun(Base):
    __tablename__ = "simulation_runs"

    id = Column(String, primary_key=True, default=generate_uuid)
    run_date = Column(DateTime, default=datetime.utcnow)
    scenario_name = Column(String, nullable=False)
    summary_json = Column(JSON, nullable=False)
    merchant_id = Column(String, ForeignKey("merchants.id"), index=True)

class RazorpayWebhookLog(Base):
    __tablename__ = "razorpay_webhook_logs"

    id = Column(String, primary_key=True, default=generate_uuid)
    event_id = Column(String, index=True)
    event_type = Column(String, nullable=False) # payment.captured, payment.failed, settlement.processed, refund.created
    payload = Column(JSON, nullable=False)
    processed = Column(Boolean, default=True)
    merchant_id = Column(String, ForeignKey("merchants.id"), index=True)
    received_at = Column(DateTime, default=datetime.utcnow)

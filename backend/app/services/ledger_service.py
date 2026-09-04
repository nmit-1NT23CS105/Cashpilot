from datetime import datetime
import uuid
from sqlalchemy.orm import Session
from ..database.models import Expense, Invoice, LedgerAccount, LedgerEntry, SupplierPayable, AuditLog, Merchant

class LedgerService:
    EXPENSE_ACCOUNT_BY_KEYWORD = [
        ("rent", "5020"),
        ("salary", "5030"),
        ("wages", "5030"),
        ("electricity", "5040"),
        ("power", "5040"),
        ("delivery", "5050"),
        ("transport", "5050"),
        ("fuel", "5050"),
        ("software", "5060"),
        ("cloud", "5060"),
        ("internet", "5060"),
        ("bank", "5070"),
        ("interest", "5070"),
    ]

    @staticmethod
    def post_entry(
        db: Session,
        debit_account_code: str,
        credit_account_code: str,
        amount: float,
        description: str,
        source_type: str = "MANUAL",
        source_id: str = None,
        created_by: str = "SYSTEM"
    ) -> LedgerEntry:
        if amount <= 0:
            raise ValueError("Ledger entry amount must be greater than zero.")

        debit_acct = db.query(LedgerAccount).filter(LedgerAccount.code == debit_account_code).first()
        credit_acct = db.query(LedgerAccount).filter(LedgerAccount.code == credit_account_code).first()

        if not debit_acct or not credit_acct:
            raise ValueError(f"Invalid ledger account code: {debit_account_code} or {credit_account_code}")

        entry_num = f"LEG-{int(datetime.utcnow().timestamp() * 1000)}-{uuid.uuid4().hex[:6].upper()}"

        entry = LedgerEntry(
            entry_number=entry_num,
            transaction_date=datetime.utcnow(),
            debit_account=debit_account_code,
            credit_account=credit_account_code,
            amount=amount,
            description=description,
            source_type=source_type,
            source_id=source_id,
            is_approved=True,
            created_by=created_by
        )

        # Update Account Balances deterministically
        # Asset / Expense increases with Debit, decreases with Credit
        # Liability / Revenue / Equity increases with Credit, decreases with Debit
        if debit_acct.type in ["ASSET", "EXPENSE"]:
            debit_acct.balance += amount
        else:
            debit_acct.balance -= amount

        if credit_acct.type in ["LIABILITY", "REVENUE", "EQUITY"]:
            credit_acct.balance += amount
        else:
            credit_acct.balance -= amount

        db.add(entry)

        audit = AuditLog(
            actor=created_by,
            action="POST_LEDGER_ENTRY",
            details=f"Posted DEBIT {debit_account_code} ({debit_acct.name}), CREDIT {credit_account_code} ({credit_acct.name}) of ₹{amount:,.2f} for {description}"
        )
        db.add(audit)
        db.commit()
        db.refresh(entry)
        return entry

    @staticmethod
    def get_balance_sheet(db: Session):
        LedgerService.reconcile_account_balances(db)
        accounts = db.query(LedgerAccount).all()
        grouped = {
            "assets": {a.name: round(a.balance, 2) for a in accounts if a.type == "ASSET"},
            "liabilities": {a.name: round(a.balance, 2) for a in accounts if a.type == "LIABILITY"},
            "equity": {a.name: round(a.balance, 2) for a in accounts if a.type == "EQUITY"},
            "revenue": {a.name: round(a.balance, 2) for a in accounts if a.type == "REVENUE"},
            "expenses": {a.name: round(a.balance, 2) for a in accounts if a.type == "EXPENSE"},
        }

        assets = sum(a.balance for a in accounts if a.type == "ASSET")
        liabilities = sum(a.balance for a in accounts if a.type == "LIABILITY")
        equity = sum(a.balance for a in accounts if a.type == "EQUITY")
        revenue = sum(a.balance for a in accounts if a.type == "REVENUE")
        expenses = sum(a.balance for a in accounts if a.type == "EXPENSE")

        net_income = revenue - expenses

        return {
            "total_assets": round(assets, 2),
            "total_liabilities": round(liabilities, 2),
            "total_equity": round(equity + net_income, 2),
            "total_revenue": round(revenue, 2),
            "total_expenses": round(expenses, 2),
            "net_income": round(net_income, 2),
            "is_balanced": abs(assets - (liabilities + equity + net_income)) < 1.0,
            "assets": grouped["assets"],
            "liabilities": grouped["liabilities"],
            "equity": {
                **grouped["equity"],
                "Current Period Net Income": round(net_income, 2),
            },
            "revenue": grouped["revenue"],
            "expenses": grouped["expenses"],
            "accounts": [{"code": a.code, "name": a.name, "type": a.type, "balance": round(a.balance, 2)} for a in accounts]
        }

    @staticmethod
    def reconcile_account_balances(db: Session) -> None:
        accounts = {a.code: a for a in db.query(LedgerAccount).all()}
        required = {"1010", "1020", "1030", "2010", "2020", "3010", "4010", "5010", "5020", "5030", "5040", "5050", "5060", "5070"}
        if not required.issubset(accounts.keys()):
            return

        merchant = db.query(Merchant).first()
        # Older databases added this column as VARCHAR during migration.
        current_cash = float(merchant.current_cash or 0.0) if merchant else float(accounts["1010"].balance or 0.0)
        invoices = db.query(Invoice).all()
        payables = db.query(SupplierPayable).all()
        expenses = db.query(Expense).all()

        receivables = sum(i.outstanding_amount for i in invoices)
        invoiced_revenue = sum(i.total_amount for i in invoices)
        cogs_estimate = round(invoiced_revenue * 0.78, 2)
        supplier_outstanding = sum(p.outstanding_amount for p in payables)

        for account in accounts.values():
            account.balance = 0.0

        accounts["1010"].balance = current_cash
        accounts["1020"].balance = receivables
        accounts["1030"].balance = supplier_outstanding
        accounts["2010"].balance = supplier_outstanding
        accounts["4010"].balance = invoiced_revenue
        accounts["5010"].balance = cogs_estimate

        for expense in expenses:
            title = expense.title.lower()
            account_code = "5050"
            for keyword, mapped_code in LedgerService.EXPENSE_ACCOUNT_BY_KEYWORD:
                if keyword in title:
                    account_code = mapped_code
                    break
            accounts[account_code].balance += expense.amount

        revenue = accounts["4010"].balance
        operating_expenses = sum(accounts[code].balance for code in ["5010", "5020", "5030", "5040", "5050", "5060", "5070"])
        net_income = revenue - operating_expenses
        assets = accounts["1010"].balance + accounts["1020"].balance + accounts["1030"].balance
        liabilities = accounts["2010"].balance + accounts["2020"].balance

        accounts["3010"].balance = round(assets - liabilities - net_income, 2)
        db.flush()

    @staticmethod
    def get_ledger_rows(db: Session, limit: int = 100):
        accounts = {a.code: a for a in db.query(LedgerAccount).all()}
        entries = (
            db.query(LedgerEntry)
            .order_by(LedgerEntry.transaction_date.desc(), LedgerEntry.created_at.desc())
            .limit(limit)
            .all()
        )

        rows = []
        for entry in entries:
            debit_name = accounts.get(entry.debit_account).name if accounts.get(entry.debit_account) else entry.debit_account
            credit_name = accounts.get(entry.credit_account).name if accounts.get(entry.credit_account) else entry.credit_account
            rows.append({
                "id": entry.id,
                "date": entry.transaction_date.strftime("%Y-%m-%d") if entry.transaction_date else None,
                "transaction": entry.description,
                "debit_account": debit_name,
                "credit_account": credit_name,
                "debit": round(entry.amount, 2),
                "credit": round(entry.amount, 2),
                "source": entry.source_type,
                "status": "APPROVED" if entry.is_approved else "PENDING",
                "created_by": entry.created_by,
            })
        return rows

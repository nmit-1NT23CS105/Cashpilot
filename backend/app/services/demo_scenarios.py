from typing import Dict, List
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from ..database.models import ActionApproval, AIAction, Merchant, Customer, Invoice, SupplierPayable, Expense, LedgerAccount, RepaymentPrediction

class DemoScenariosService:
    SCENARIOS = [
        {
            "id": "scenario_8_main",
            "name": "Scenario 8: Recovery vs Liquidity Conflict (MAIN DEMO)",
            "description": "High-probability Customer A receivable (₹2.0L) vs low-probability Customer B (₹3.0L) vs Supplier X payment (₹5.0L due tomorrow) threatening Day-3 cash buffer.",
            "tag": "FEATURED"
        },
        {
            "id": "scenario_1_healthy",
            "name": "Scenario 1: Healthy Distributor",
            "description": "Normal positive cash flow, all customer repayment probabilities >85%, cash balance safely above ₹2.0L minimum buffer.",
            "tag": "NORMAL"
        },
        {
            "id": "scenario_2_crisis",
            "name": "Scenario 2: Liquidity Crisis",
            "description": "Large supplier payables due before customer collections arrive. Immediate risk alert triggered.",
            "tag": "CRITICAL"
        },
        {
            "id": "scenario_3_high_risk",
            "name": "Scenario 3: High-Risk Customer",
            "description": "Customer B owes ₹3.0L overdue with deteriorating payment history (48% probability). Escalated to human manager.",
            "tag": "RISK"
        },
        {
            "id": "scenario_4_reliable",
            "name": "Scenario 4: Reliable Customer",
            "description": "Customer A has 96/100 Reliability Score and 96% repayment probability within 3 days. Automated payment link issued.",
            "tag": "AUTOMATED"
        },
        {
            "id": "scenario_5_delayed_settlement",
            "name": "Scenario 5: Delayed Razorpay Settlement",
            "description": "Expected ₹3.2L settlement delayed by 2 days. AI automatically shifts supplier payment priorities to avoid overdraft.",
            "tag": "SETTLEMENT"
        },
        {
            "id": "scenario_6_p2p_promise",
            "name": "Scenario 6: Customer Promise-to-Pay",
            "description": "Customer E promises ₹40,000 on Friday. Automated collection outreach paused per AI policy.",
            "tag": "PROMISE"
        },
        {
            "id": "scenario_7_expense_spike",
            "name": "Scenario 7: Unexpected Expense Spike",
            "description": "Electricity Board bill spikes 105% to ₹41,000. Flagged for operational review before posting.",
            "tag": "EXPENSE"
        }
    ]

    @staticmethod
    def get_all_scenarios() -> List[Dict]:
        return DemoScenariosService.SCENARIOS

    @staticmethod
    def _customer_by_position(db: Session, position: int) -> Customer:
        return db.query(Customer).order_by(Customer.created_at.asc()).offset(position).first()

    @staticmethod
    def _set_customer_invoice(
        db: Session,
        merchant: Merchant,
        customer: Customer,
        invoice_number: str,
        amount: float,
        due_offset_days: int,
        status: str,
        probability: float,
        expected_days: float,
    ) -> None:
        today = datetime.utcnow()
        for invoice in db.query(Invoice).filter(Invoice.customer_id == customer.id).all():
            invoice.status = "PAID"
            invoice.paid_amount = invoice.total_amount
            invoice.outstanding_amount = 0.0

        invoice = db.query(Invoice).filter(Invoice.invoice_number == invoice_number).first()
        if not invoice:
            invoice = Invoice(
                merchant_id=merchant.id,
                customer_id=customer.id,
                invoice_number=invoice_number,
                total_amount=amount,
                paid_amount=0.0,
                outstanding_amount=amount,
                payment_terms_days=15,
            )
            db.add(invoice)
            db.flush()

        invoice.merchant_id = merchant.id
        invoice.customer_id = customer.id
        invoice.issue_date = today + timedelta(days=due_offset_days - 15)
        invoice.due_date = today + timedelta(days=due_offset_days)
        invoice.total_amount = amount
        invoice.paid_amount = 0.0
        invoice.outstanding_amount = amount
        invoice.status = status
        invoice.payment_terms_days = 15

        db.add(RepaymentPrediction(
            invoice_id=invoice.id,
            customer_id=customer.id,
            repayment_probability_15d=probability,
            expected_payment_days=expected_days,
            confidence_level="HIGH" if probability >= 0.8 or probability <= 0.4 else "MEDIUM",
            factors={
                "scenario": "main_demo",
                "on_time_rate": customer.on_time_payment_rate,
                "reliability_score": customer.reliability_score,
            },
        ))

    @staticmethod
    def _recalculate_customer_totals(db: Session) -> None:
        for customer in db.query(Customer).all():
            invoices = db.query(Invoice).filter(Invoice.customer_id == customer.id).all()
            customer.total_transactions_count = len(invoices)
            customer.total_purchases_val = sum(invoice.total_amount for invoice in invoices)
            customer.total_paid_val = sum(invoice.paid_amount for invoice in invoices)
            customer.current_outstanding = sum(invoice.outstanding_amount for invoice in invoices)
            customer.overdue_count = sum(1 for invoice in invoices if invoice.status == "OVERDUE")

    @staticmethod
    def _apply_main_demo(db: Session, merchant: Merchant, cash_acct: LedgerAccount) -> None:
        today = datetime.utcnow()
        if cash_acct:
            cash_acct.balance = 450000.0
        if merchant:
            merchant.min_cash_buffer = 200000.0

        for invoice in db.query(Invoice).all():
            invoice.status = "PAID"
            invoice.paid_amount = invoice.total_amount
            invoice.outstanding_amount = 0.0

        demo_profiles = [
            ("Customer A (Prime Retailers)", "RELIABLE", "STABLE", 96.0, 0.96, 1.2, 200000.0, 3, "ISSUED", 0.96, 3.0),
            ("Customer B (Metro Marts)", "HIGH_RISK", "DETERIORATING", 48.0, 0.45, 14.5, 300000.0, -5, "OVERDUE", 0.48, 10.0),
            ("Customer C (Sunshine Superstore)", "RELIABLE", "STABLE", 91.0, 0.91, 2.8, 100000.0, 4, "ISSUED", 0.91, 4.0),
            ("Customer D (City Bazaar)", "SLOW_PAYER", "STABLE", 35.0, 0.32, 18.0, 200000.0, -12, "OVERDUE", 0.32, 14.5),
            ("Customer E (Royal Provisions - P2P Active)", "PROMISE_TO_PAY", "STABLE", 74.0, 0.75, 5.5, 40000.0, -2, "OVERDUE", 0.75, 2.0),
            ("Customer F (Northline Stores)", "FAST_PAYER", "STABLE", 89.0, 0.88, 1.0, 220000.0, 1, "ISSUED", 0.85, 1.0),
            ("Customer G (Value Bazaar)", "SLOW_PAYER", "STABLE", 62.0, 0.60, 8.0, 180000.0, 8, "ISSUED", 0.60, 8.0),
        ]

        for index, profile in enumerate(demo_profiles):
            customer = DemoScenariosService._customer_by_position(db, index)
            if not customer:
                continue
            (
                name,
                segment,
                trend,
                score,
                on_time_rate,
                delay,
                amount,
                due_offset,
                status,
                probability,
                expected_days,
            ) = profile
            customer.name = name
            customer.segment = segment
            customer.behavior_trend = trend
            customer.reliability_score = score
            customer.on_time_payment_rate = on_time_rate
            customer.avg_payment_delay_days = delay
            customer.max_payment_delay_days = max(delay * 2.2, delay + 3.0)
            customer.opt_out_contact = False
            customer.has_active_p2p = "P2P" in name
            customer.p2p_amount = 40000.0 if customer.has_active_p2p else 0.0
            customer.p2p_promised_date = (today + timedelta(days=2)).strftime("%Y-%m-%d") if customer.has_active_p2p else None
            customer.p2p_confidence = 0.92 if customer.has_active_p2p else 0.0
            DemoScenariosService._set_customer_invoice(
                db,
                merchant,
                customer,
                f"DEMO-MAIN-{index + 1:02d}",
                amount,
                due_offset,
                status,
                probability,
                expected_days,
            )

        for payable in db.query(SupplierPayable).all():
            payable.status = "PAID"
            payable.paid_amount = payable.total_amount
            payable.outstanding_amount = 0.0

        suppliers = db.query(SupplierPayable).order_by(SupplierPayable.created_at.asc()).all()
        if suppliers:
            suppliers[0].bill_number = "BILL-SUP-9001"
            suppliers[0].due_date = today + timedelta(days=1)
            suppliers[0].total_amount = 500000.0
            suppliers[0].paid_amount = 0.0
            suppliers[0].outstanding_amount = 500000.0
            suppliers[0].priority_level = "CRITICAL"
            suppliers[0].status = "UNPAID"
        if len(suppliers) > 1:
            suppliers[1].due_date = today + timedelta(days=7)
            suppliers[1].total_amount = 120000.0
            suppliers[1].paid_amount = 0.0
            suppliers[1].outstanding_amount = 120000.0
            suppliers[1].priority_level = "HIGH"
            suppliers[1].status = "UNPAID"

        DemoScenariosService._recalculate_customer_totals(db)

    @staticmethod
    def apply_scenario(db: Session, scenario_id: str) -> Dict:
        merchant = db.query(Merchant).first()
        cash_acct = db.query(LedgerAccount).filter(LedgerAccount.code == "1010").first()
        db.query(ActionApproval).delete(synchronize_session=False)
        db.query(AIAction).delete(synchronize_session=False)
        DemoScenariosService._apply_main_demo(db, merchant, cash_acct)

        if scenario_id == "scenario_1_healthy":
            if cash_acct: cash_acct.balance = 650000.0
            if merchant: merchant.min_cash_buffer = 200000.0
            for payable in db.query(SupplierPayable).filter(SupplierPayable.outstanding_amount > 0).all():
                payable.due_date = datetime.utcnow() + timedelta(days=10)
                payable.priority_level = "MEDIUM"
            for customer in db.query(Customer).limit(7).all():
                customer.segment = "RELIABLE"
                customer.behavior_trend = "STABLE"
                customer.reliability_score = max(customer.reliability_score, 88.0)
                customer.on_time_payment_rate = max(customer.on_time_payment_rate, 0.88)
            for prediction in db.query(RepaymentPrediction).all():
                prediction.repayment_probability_15d = max(prediction.repayment_probability_15d, 0.88)
                prediction.expected_payment_days = min(prediction.expected_payment_days, 4.0)
        elif scenario_id == "scenario_2_crisis":
            if cash_acct: cash_acct.balance = 180000.0
            if merchant: merchant.min_cash_buffer = 250000.0
        elif scenario_id == "scenario_8_main" or scenario_id == "scenario_3_high_risk":
            pass
        elif scenario_id == "scenario_5_delayed_settlement":
            if cash_acct: cash_acct.balance = 220000.0
            if merchant: merchant.min_cash_buffer = 200000.0

        db.commit()
        return {
            "status": "applied",
            "active_scenario_id": scenario_id,
            "current_cash": cash_acct.balance if cash_acct else 450000.0,
            "min_buffer": merchant.min_cash_buffer if merchant else 200000.0
        }

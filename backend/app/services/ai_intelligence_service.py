from datetime import datetime, timedelta
from typing import Dict, List

from sqlalchemy.orm import Session

from ..database.models import AuditLog, Customer, Expense, Invoice, Merchant, Product, SupplierPayable
from .cashflow_service import CashflowService
from .decision_engine import DecisionEngine
from .ml_repayment_service import ml_repayment_service


class AIIntelligenceService:
    """Deterministic AI feature layer for explainable, approval-safe business decisions."""

    @staticmethod
    def _customer_risk(customer: Customer) -> Dict:
        outstanding = customer.current_outstanding or 0.0
        credit_limit = customer.credit_limit or 1.0
        balance_ratio = min(2.5, max(0.0, outstanding / max(1.0, credit_limit)))
        history_quality = min(1.0, (customer.total_transactions_count or 0) / 10.0)
        on_time_gap = max(0.0, 0.85 - (customer.on_time_payment_rate or 0.85))
        delay_penalty = min(30.0, (customer.avg_payment_delay_days or 0.0) * 2.2)
        overdue_penalty = min(25.0, (customer.overdue_count or 0) * 6.0)
        trend_penalty = 15.0 if customer.behavior_trend == "DETERIORATING" else 0.0
        ratio_penalty = max(0.0, (balance_ratio - 0.7) * 30.0)
        risk = 30.0 + (balance_ratio * 18.0) + (on_time_gap * 100.0) + delay_penalty + overdue_penalty + trend_penalty + ratio_penalty
        risk = max(0.0, min(100.0, risk - ((customer.reliability_score or 75.0) * 0.35)))

        factors = []
        if customer.avg_payment_delay_days > 7:
            factors.append("average payment delay is above 7 days")
        if customer.on_time_payment_rate < 0.75:
            factors.append("on-time payment rate is below 75%")
        if customer.behavior_trend == "DETERIORATING":
            factors.append("recent payment behavior is deteriorating")
        if outstanding > credit_limit:
            factors.append("outstanding balance exceeds credit limit")
        overdue_invoices = sum(1 for invoice in customer.invoices if invoice.outstanding_amount > 0 and invoice.due_date and invoice.due_date.date() < datetime.utcnow().date())
        if overdue_invoices:
            risk = min(100.0, risk + min(20.0, overdue_invoices * 5.0))
            factors.append(f"{overdue_invoices} outstanding invoice(s) are overdue")
        if history_quality < 0.3:
            factors.append("limited payment history reduces prediction confidence")

        return {
            "customer_id": customer.id,
            "customer_name": customer.name,
            "risk_score": round(risk, 1),
            "risk_band": "HIGH" if risk >= 55 else "MEDIUM" if risk >= 30 else "LOW",
            "outstanding": round(outstanding, 2),
            "recommended_credit_limit": round(max(0.0, outstanding * 1.15), 2),
            "confidence": round(0.55 + history_quality * 0.4, 2),
            "factors": factors or ["payment history is within the normal range"],
            "recommended_action": "HUMAN_REVIEW" if risk >= 55 else "MONITOR" if risk >= 30 else "MAINTAIN_TERMS",
        }

    @staticmethod
    def _supplier_optimization(db: Session) -> List[Dict]:
        results = []
        for payable in db.query(SupplierPayable).filter(SupplierPayable.outstanding_amount > 0).all():
            supplier = payable.supplier
            due_days = (payable.due_date.date() - datetime.utcnow().date()).days if payable.due_date else 30
            discount = (supplier.early_discount_percent if supplier else 0.0) or 0.0
            penalty = (supplier.late_penalty_percent if supplier else 0.0) or 0.0
            discount_value = payable.outstanding_amount * discount / 100
            penalty_value = payable.outstanding_amount * penalty / 100
            urgency = 100 if due_days <= 0 else max(10, 100 - due_days * 4)
            score = min(100.0, urgency * 0.55 + (penalty * 12) + (discount * 8))
            results.append({
                "payable_id": payable.id,
                "supplier_name": supplier.name if supplier else "Supplier",
                "amount": round(payable.outstanding_amount, 2),
                "due_in_days": due_days,
                "priority_score": round(score, 1),
                "early_discount_value": round(discount_value, 2),
                "late_penalty_value": round(penalty_value, 2),
                "recommended_action": "PAY_NOW" if due_days <= 0 or penalty_value > discount_value else "SCHEDULE",
                "explanation": "Pay now to avoid a late penalty." if due_days <= 0 or penalty_value > discount_value else "Schedule near the due date and preserve cash while the early discount is lower than the liquidity value.",
            })
        return sorted(results, key=lambda item: item["priority_score"], reverse=True)

    @staticmethod
    def overview(db: Session) -> Dict:
        ml_repayment_service.refresh_if_needed(db)
        cashflow = CashflowService.forecast_7_15_days(db, forecast_days=15)
        plan = DecisionEngine.generate_daily_action_plan(db)
        customers = [AIIntelligenceService._customer_risk(customer) for customer in db.query(Customer).all()]
        anomalies = [expense for expense in db.query(Expense).all() if expense.is_anomaly]
        invoices = db.query(Invoice).all()
        observed_predictions = sum(1 for invoice in invoices if invoice.status in {"PAID", "OVERDUE"})
        return {
            "agents": [
                {"name": "Collections Agent", "status": "READY", "focus": "payment timing and Razorpay recovery"},
                {"name": "Liquidity Agent", "status": "READY", "focus": "15-day cash buffer protection"},
                {"name": "Supplier Agent", "status": "READY", "focus": "discount, penalty, and due-date optimization"},
                {"name": "Risk Agent", "status": "READY", "focus": "customer default and concentration signals"},
                {"name": "Expense Agent", "status": "READY", "focus": "anomalies and recurring cost drift"},
                {"name": "Compliance Agent", "status": "READY", "focus": "invoice and GST data quality"},
            ],
            "cashflow": cashflow,
            "action_plan": plan,
            "customer_risk": sorted(customers, key=lambda item: item["risk_score"], reverse=True),
            "supplier_optimization": AIIntelligenceService._supplier_optimization(db),
            "expense_signals": [{"title": expense.title, "amount": expense.amount, "reason": expense.anomaly_reason or "Anomaly detected"} for expense in anomalies],
            "model_quality": {"observed_invoice_outcomes": observed_predictions, "data_quality": round(min(1.0, observed_predictions / 20.0), 2), "confidence_note": "Confidence increases as paid, overdue, and partial-payment outcomes accumulate."},
            "explainability": {"method": "rules + historical behavior + repayment model", "llm_controls": "LLMs cannot directly mutate ledger or move money", "human_approval": "Required for high-value and low-confidence actions"},
        }

    @staticmethod
    def analyze_invoice(payload: Dict) -> Dict:
        description = str(payload.get("description", ""))
        amount = float(payload.get("amount", 0) or 0)
        tax = float(payload.get("tax", 0) or 0)
        warnings = []
        if amount <= 0:
            warnings.append("Amount is missing or invalid")
        if tax < 0 or tax > amount * 0.3:
            warnings.append("Tax amount needs review")
        if not payload.get("invoice_number"):
            warnings.append("Invoice number is missing")
        return {"fields": {"vendor": payload.get("vendor"), "invoice_number": payload.get("invoice_number"), "date": payload.get("date"), "amount": amount, "tax": tax}, "confidence": round(max(0.25, 0.95 - len(warnings) * 0.18), 2), "duplicate_risk": "HIGH" if not payload.get("invoice_number") else "LOW", "warnings": warnings, "recommended_action": "REVIEW_BEFORE_POSTING" if warnings else "READY_FOR_APPROVAL"}

    @staticmethod
    def compliance(db: Session) -> Dict:
        invoices = db.query(Invoice).all()
        missing_due_dates = [invoice.invoice_number for invoice in invoices if not invoice.due_date]
        missing_customer_data = [invoice.invoice_number for invoice in invoices if not invoice.customer or not invoice.customer.name]
        return {"gst_readiness": round(max(0, 100 - len(missing_due_dates) * 15 - len(missing_customer_data) * 10), 1), "checks": [{"name": "Invoice due dates", "status": "REVIEW" if missing_due_dates else "PASS", "count": len(missing_due_dates)}, {"name": "Customer identity", "status": "REVIEW" if missing_customer_data else "PASS", "count": len(missing_customer_data)}, {"name": "Outstanding reconciliation", "status": "PASS", "count": sum(1 for invoice in invoices if invoice.outstanding_amount >= 0)}], "missing_due_dates": missing_due_dates, "missing_customer_data": missing_customer_data}

    @staticmethod
    def scenario(db: Session, payload: Dict) -> Dict:
        collection_rate = max(0.0, min(1.0, float(payload.get("collection_rate", 0.8))))
        sales_change = float(payload.get("sales_change_percent", 0.0)) / 100
        expense_change = float(payload.get("expense_change_percent", 0.0)) / 100
        current_cash = CashflowService.forecast_7_15_days(db, forecast_days=15)["current_cash"]
        receivables = sum(invoice.outstanding_amount for invoice in db.query(Invoice).all())
        expenses = sum(expense.amount for expense in db.query(Expense).all())
        expected_recovery = receivables * collection_rate
        projected_cash = current_cash + expected_recovery + receivables * sales_change - expenses * expense_change
        merchant = db.query(Merchant).first()
        buffer = merchant.min_cash_buffer if merchant else 200000.0
        return {"assumptions": {"collection_rate": collection_rate, "sales_change_percent": sales_change * 100, "expense_change_percent": expense_change * 100}, "current_cash": round(current_cash, 2), "expected_recovery": round(expected_recovery, 2), "projected_cash": round(projected_cash, 2), "buffer_gap": round(projected_cash - buffer, 2), "recommendation": "PROTECT_LIQUIDITY" if projected_cash < buffer else "EXECUTE_COLLECTION_PLAN"}

    @staticmethod
    def voice_intent(text: str) -> Dict:
        normalized = text.lower().strip()
        if any(word in normalized for word in ["collect", "receivable", "payment link"]):
            intent = "COLLECTIONS_REVIEW"
        elif any(word in normalized for word in ["supplier", "payable", "vendor"]):
            intent = "SUPPLIER_REVIEW"
        elif any(word in normalized for word in ["cash", "forecast", "liquidity"]):
            intent = "LIQUIDITY_FORECAST"
        else:
            intent = "FINANCIAL_SUMMARY"
        return {"intent": intent, "transcript": text, "requires_confirmation": True, "next_step": "Open the relevant intelligence queue and confirm before making any financial change."}

    @staticmethod
    def record_feedback(db: Session, action_id: str, outcome: str, notes: str = "") -> Dict:
        db.add(AuditLog(actor="USER", action="AI_FEEDBACK", details=f"AI action {action_id} outcome={outcome}; {notes}"))
        db.commit()
        return {"status": "recorded", "action_id": action_id, "outcome": outcome}
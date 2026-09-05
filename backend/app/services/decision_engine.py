from datetime import datetime
from typing import Dict

from sqlalchemy.orm import Session

from ..database.models import AIAction, Customer, Expense, Invoice, Merchant, RepaymentPrediction, SupplierPayable
from .cashflow_service import CashflowService
from .ml_repayment_service import ml_repayment_service
from .policy_engine import PolicyEngine


class DecisionEngine:
    @staticmethod
    def _persist_action(db: Session, action: Dict) -> Dict:
        existing = (
            db.query(AIAction)
            .filter(
                AIAction.action_type == action["action_type"],
                AIAction.target_type == action["target_type"],
                AIAction.target_id == action["target_id"],
            )
            .order_by(AIAction.created_at.desc())
            .first()
        )

        preserved_statuses = {"APPROVED", "REJECTED", "EXECUTED"}
        if existing:
            existing.target_name = action["target_name"]
            existing.amount = action["amount"]
            existing.priority_score = action["priority_score"]
            existing.confidence = action["confidence"]
            existing.explanation = action["explanation"]
            existing.requires_approval = action["requires_approval"]
            existing.approval_reason = action.get("approval_reason")
            if existing.status not in preserved_statuses:
                existing.status = action["status"]
            action["id"] = existing.id
            action["status"] = existing.status
        else:
            existing = AIAction(**{k: v for k, v in action.items() if k in {
                "action_type",
                "target_type",
                "target_id",
                "target_name",
                "amount",
                "priority_score",
                "confidence",
                "explanation",
                "status",
                "requires_approval",
                "approval_reason",
            }})
            db.add(existing)
            db.flush()
            action["id"] = existing.id

        return action

    @staticmethod
    def _customer_action(
        db: Session,
        invoice: Invoice,
        customer: Customer,
        has_liquidity_crisis: bool,
        min_projected_cash: float,
        min_buffer: float,
    ) -> Dict:
        if customer.opt_out_contact:
            return {
                "action_type": "STOP",
                "target_type": "CUSTOMER",
                "target_id": customer.id,
                "target_name": customer.name,
                "amount": invoice.outstanding_amount,
                "priority_score": 0.0,
                "confidence": 1.0,
                "status": "STOPPED",
                "requires_approval": False,
                "approval_reason": None,
                "explanation": f"{customer.name} opted out of automated outreach. Collections are blocked until a human reviews the account.",
                "expected_financial_impact": 0.0,
                "policy_reasons": ["Customer opted out of automated outreach"],
            }

        stored_prediction = (
            db.query(RepaymentPrediction)
            .filter(RepaymentPrediction.invoice_id == invoice.id)
            .order_by(RepaymentPrediction.created_at.desc())
            .first()
        )
        if stored_prediction:
            prediction = {
                "repayment_probability_15d": stored_prediction.repayment_probability_15d,
                "expected_payment_days": stored_prediction.expected_payment_days,
                "confidence": stored_prediction.confidence_level,
            }
        else:
            prediction = ml_repayment_service.predict_invoice_repayment(customer, invoice.outstanding_amount, db)
        probability = prediction["repayment_probability_15d"]
        expected_days = prediction["expected_payment_days"]
        expected_recovery = invoice.outstanding_amount * probability

        if has_liquidity_crisis and min_projected_cash < min_buffer and customer.segment == "HIGH_RISK":
            action_type = "HUMAN_ESCALATION"
            status = "PAUSED_FOR_LIQUIDITY"
            requires_approval = True
            explanation = (
                f"{customer.name} owes INR {invoice.outstanding_amount:,.2f}, but the model estimates only "
                f"{int(probability * 100)}% repayment probability inside the 15-day period. Projected cash falls "
                f"to INR {min_projected_cash:,.2f}, below the INR {min_buffer:,.2f} safety buffer, so automated retry "
                "is paused and routed to a finance manager."
            )
        elif probability >= 0.85 and expected_days <= 5.0:
            action_type = "SEND_PAYMENT_LINK"
            status = "RECOMMENDED"
            requires_approval = False
            explanation = (
                f"{customer.name} has {int(probability * 100)}% predicted repayment probability and usually pays "
                f"in {expected_days} days. Sending a payment link is expected to recover INR {expected_recovery:,.2f} "
                "inside the liquidity window."
            )
        elif probability >= 0.65:
            action_type = "SEND_REMINDER"
            status = "RECOMMENDED"
            requires_approval = False
            explanation = (
                f"{customer.name} has {int(probability * 100)}% predicted repayment probability. A reminder is "
                "recommended because the expected value is positive and customer risk is moderate."
            )
        elif invoice.outstanding_amount > 150000.0 or customer.segment == "HIGH_RISK":
            action_type = "HUMAN_ESCALATION"
            status = "RECOMMENDED"
            requires_approval = True
            explanation = (
                f"{customer.name} has a high-value invoice of INR {invoice.outstanding_amount:,.2f} and "
                f"{int(probability * 100)}% repayment probability. Human review is required before collection action."
            )
        else:
            action_type = "WAIT"
            status = "RECOMMENDED"
            requires_approval = False
            explanation = (
                f"{customer.name} has {int(probability * 100)}% repayment probability. Waiting avoids unnecessary "
                "contact while higher-impact receivables are prioritized."
            )

        priority_score = round((expected_recovery / 10000.0) * probability * (1.0 if expected_days <= 5 else 0.7), 1)
        action = {
            "action_type": action_type,
            "target_type": "CUSTOMER",
            "target_id": customer.id,
            "target_name": customer.name,
            "amount": invoice.outstanding_amount,
            "priority_score": priority_score,
            "confidence": probability,
            "status": status,
            "requires_approval": requires_approval,
            "approval_reason": "High-value or low-confidence receivable requires human approval" if requires_approval else None,
            "explanation": explanation,
            "expected_financial_impact": round(expected_recovery, 2),
        }
        policy = PolicyEngine.evaluate_action_policy(action, min_projected_cash, min_buffer)
        if policy["requires_approval"]:
            action["requires_approval"] = True
            action["approval_reason"] = "; ".join(policy["policy_reasons"])
        action["policy_reasons"] = policy["policy_reasons"]
        return action

    @staticmethod
    def generate_daily_action_plan(db: Session, custom_buffer: float = None) -> Dict:
        merchant = db.query(Merchant).first()
        min_buffer = custom_buffer if custom_buffer is not None else (merchant.min_cash_buffer if merchant else 200000.0)

        cashflow = CashflowService.forecast_7_15_days(db, forecast_days=15, custom_buffer=min_buffer)
        has_liquidity_crisis = cashflow["has_liquidity_violation"]
        min_projected_cash = cashflow["min_projected_cash"]

        actions = []
        total_recovery_target = 0.0
        expected_recovery_accum = 0.0

        open_invoices = db.query(Invoice).filter(Invoice.outstanding_amount > 0).all()
        for invoice in open_invoices:
            customer = invoice.customer
            if not customer:
                continue

            action = DecisionEngine._customer_action(
                db,
                invoice,
                customer,
                has_liquidity_crisis,
                min_projected_cash,
                min_buffer,
            )
            total_recovery_target += invoice.outstanding_amount
            expected_recovery_accum += max(0.0, action.get("expected_financial_impact", 0.0))
            actions.append(DecisionEngine._persist_action(db, action))

        open_payables = db.query(SupplierPayable).filter(SupplierPayable.outstanding_amount > 0).all()
        for payable in open_payables:
            supplier = payable.supplier
            due_days = (payable.due_date.date() - datetime.utcnow().date()).days if payable.due_date else 99
            priority_score = 98.0 if payable.priority_level == "CRITICAL" else (82.0 if due_days <= 5 else 70.0)
            action = {
                "action_type": "PRIORITIZE_SUPPLIER",
                "target_type": "SUPPLIER",
                "target_id": supplier.id if supplier else payable.id,
                "target_name": supplier.name if supplier else "Supplier",
                "amount": payable.outstanding_amount,
                "priority_score": priority_score,
                "confidence": 0.95,
                "status": "RECOMMENDED",
                "requires_approval": payable.outstanding_amount > 50000.0,
                "approval_reason": "Supplier payment exceeds INR 50,000 policy threshold" if payable.outstanding_amount > 50000.0 else None,
                "explanation": (
                    f"Supplier payable of INR {payable.outstanding_amount:,.2f} to {supplier.name if supplier else 'Supplier'} "
                    f"is due in {due_days} day(s). Priority is {payable.priority_level}; schedule payment only after confirming "
                    "the cash buffer forecast."
                ),
                "expected_financial_impact": round(-payable.outstanding_amount, 2),
                "policy_reasons": ["Supplier payment approval threshold"] if payable.outstanding_amount > 50000.0 else [],
            }
            actions.append(DecisionEngine._persist_action(db, action))

        anomalous_expenses = db.query(Expense).filter(Expense.is_anomaly == True).all()
        for expense in anomalous_expenses:
            action = {
                "action_type": "REVIEW_EXPENSE",
                "target_type": "EXPENSE",
                "target_id": expense.id,
                "target_name": expense.title,
                "amount": expense.amount,
                "priority_score": 84.0,
                "confidence": 0.89,
                "status": "RECOMMENDED",
                "requires_approval": True,
                "approval_reason": "Unusual expense anomaly detected",
                "explanation": expense.anomaly_reason or f"{expense.title} is outside the merchant's normal expense profile.",
                "expected_financial_impact": round(-expense.amount, 2),
                "policy_reasons": ["Review before paying unusual expense"],
            }
            actions.append(DecisionEngine._persist_action(db, action))

        actions.sort(key=lambda item: item["priority_score"], reverse=True)
        db.commit()

        return {
            "liquidity_status": "LIQUIDITY_RISK" if has_liquidity_crisis else "HEALTHY",
            "current_cash": cashflow["current_cash"],
            "min_cash_buffer": min_buffer,
            "min_projected_cash": min_projected_cash,
            "total_receivables": round(total_recovery_target, 2),
            "expected_recovery": round(expected_recovery_accum, 2),
            "total_actions": len(actions),
            "action_items": actions,
        }

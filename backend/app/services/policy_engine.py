from typing import Dict
from datetime import datetime
from sqlalchemy.orm import Session
from ..database.models import AIAction, ActionApproval, AuditLog, Merchant

class PolicyEngine:
    POLICY_RULES = {
        "auto_approve_retry_under": 10000.0,
        "human_approval_required_over": 50000.0,
        "min_model_confidence_threshold": 0.60,
        "block_action_if_cash_below_buffer": True
    }

    @staticmethod
    def evaluate_action_policy(action_dict: Dict, current_cash: float, min_buffer: float) -> Dict:
        amount = action_dict.get("amount", 0.0)
        confidence = action_dict.get("confidence", 1.0)
        action_type = action_dict.get("action_type")

        reasons = []
        requires_approval = False

        if amount > PolicyEngine.POLICY_RULES["human_approval_required_over"]:
            requires_approval = True
            reasons.append(f"Transaction amount ₹{amount:,.2f} exceeds human approval limit (₹50,000)")

        if confidence < PolicyEngine.POLICY_RULES["min_model_confidence_threshold"]:
            requires_approval = True
            reasons.append(f"Model confidence ({int(confidence*100)}%) is below policy minimum threshold (60%)")

        if current_cash < min_buffer and action_type in ["SEND_PAYMENT_LINK", "SEND_REMINDER"]:
            if amount > 100000.0:
                requires_approval = True
                reasons.append(f"Merchant projected cash (₹{current_cash:,.2f}) is below safe buffer (₹{min_buffer:,.2f})")

        return {
            "allowed": True,
            "requires_approval": requires_approval,
            "policy_reasons": reasons
        }

    @staticmethod
    def approve_action(db: Session, action_id: str, reviewer: str = "User", notes: str = None):
        action = db.query(AIAction).filter(AIAction.id == action_id).first()
        if not action:
            return None

        action.status = "APPROVED"
        
        approval = db.query(ActionApproval).filter(ActionApproval.action_id == action_id).first()
        if not approval:
            approval = ActionApproval(action_id=action_id)
            db.add(approval)

        approval.status = "APPROVED"
        approval.reviewed_by = reviewer
        approval.review_notes = notes
        approval.reviewed_at = datetime.utcnow()

        audit = AuditLog(
            actor=reviewer,
            action="APPROVE_AI_ACTION",
            details=f"Approved AI Action #{action_id}: {action.action_type} for {action.target_name} (₹{action.amount:,.2f})"
        )
        db.add(audit)
        db.commit()
        return action

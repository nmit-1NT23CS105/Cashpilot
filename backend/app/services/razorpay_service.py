import os
import uuid
import json
import hmac
import hashlib
from datetime import datetime
from typing import Dict
from sqlalchemy.orm import Session
from ..database.models import RazorpayWebhookLog, Payment, Invoice, AuditLog
from .ledger_service import LedgerService

class RazorpayService:
    RAZORPAY_KEY_ID = os.getenv("RAZORPAY_KEY_ID", "rzp_test_cashpilot")
    RAZORPAY_KEY_SECRET = os.getenv("RAZORPAY_KEY_SECRET")

    @staticmethod
    def verify_webhook_signature(raw_body: bytes, signature: str | None) -> bool:
        if not RazorpayService.RAZORPAY_KEY_SECRET:
            return True
        if not signature:
            return False
        expected = hmac.new(RazorpayService.RAZORPAY_KEY_SECRET.encode(), raw_body, hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, signature)

    @staticmethod
    def build_follow_up_plan(invoice_id: str, customer_name: str, amount: float, due_date: str) -> Dict:
        due_iso = due_date or datetime.utcnow().strftime("%Y-%m-%d")
        return {
            "invoice_id": invoice_id,
            "customer_name": customer_name,
            "amount": amount,
            "due_date": due_iso,
            "channel": "Razorpay Payment Link",
            "recommended_message": (
                f"Hi {customer_name}, your outstanding invoice {invoice_id} for INR {amount:,.2f} is due on {due_iso}. "
                "Please complete payment using the secure payment link below."
            ),
            "follow_up_sequence": [
                "Send secure link with due-date reminder",
                "Trigger WhatsApp + email reminders after 24 hours",
                "Escalate to collections team if no payment in 3 days",
            ],
        }

    @staticmethod
    def create_payment_link(invoice_id: str, customer_name: str, amount: float, due_date: str) -> Dict:
        # Generates a realistic test payment link with fallback
        link_id = f"plink_{uuid.uuid4().hex[:12]}"
        short_url = f"https://rzp.io/i/{link_id[:8]}"
        follow_up = RazorpayService.build_follow_up_plan(invoice_id, customer_name, amount, due_date)
        
        return {
            "payment_link_id": link_id,
            "short_url": short_url,
            "invoice_id": invoice_id,
            "customer_name": customer_name,
            "amount": amount,
            "status": "created",
            "created_at": datetime.utcnow().isoformat(),
            "expire_by": due_date,
            "channel": follow_up["channel"],
            "recommended_message": follow_up["recommended_message"],
            "follow_up_sequence": follow_up["follow_up_sequence"],
        }

    @staticmethod
    def process_webhook(db: Session, event_payload: Dict) -> Dict:
        event_type = event_payload.get("event", "payment.captured")
        event_id = event_payload.get("event_id", f"evt_{uuid.uuid4().hex[:10]}")

        existing = db.query(RazorpayWebhookLog).filter(RazorpayWebhookLog.event_id == event_id).first()
        if existing:
            return {
                "status": "duplicate_ignored",
                "event_id": event_id,
                "event_type": existing.event_type,
            }

        # Store webhook log
        log = RazorpayWebhookLog(
            event_id=event_id,
            event_type=event_type,
            payload=event_payload,
            processed=True
        )
        db.add(log)

        # Handle Payment Event
        if event_type in ["payment.captured", "payment.authorized"]:
            payment_entity = event_payload.get("payload", {}).get("payment", {}).get("entity", {})
            invoice_id = payment_entity.get("notes", {}).get("invoice_id")
            amount = payment_entity.get("amount", 0) / 100.0 # convert paise to INR

            if invoice_id:
                inv = db.query(Invoice).filter(Invoice.id == invoice_id).first()
                if inv:
                    applied_amount = min(amount, inv.outstanding_amount)
                    inv.paid_amount += applied_amount
                    inv.outstanding_amount = max(0.0, inv.total_amount - inv.paid_amount)
                    if inv.outstanding_amount == 0:
                        inv.status = "PAID"
                    else:
                        inv.status = "PARTIALLY_PAID"

                    if inv.customer:
                        inv.customer.total_paid_val += applied_amount
                        inv.customer.current_outstanding = max(0.0, inv.customer.current_outstanding - applied_amount)

                    pmt = Payment(
                        invoice_id=inv.id,
                        customer_id=inv.customer_id,
                        amount=applied_amount,
                        payment_method="Razorpay",
                        status="SUCCESS",
                        razorpay_payment_id=payment_entity.get("id")
                    )
                    db.add(pmt)
                    db.flush()
                    LedgerService.post_entry(
                        db,
                        debit_account_code="1010",
                        credit_account_code="1020",
                        amount=applied_amount,
                        description=f"Razorpay payment captured for invoice {inv.invoice_number}",
                        source_type="PAYMENT",
                        source_id=pmt.id,
                        created_by="RAZORPAY_WEBHOOK",
                    )

        audit = AuditLog(
            actor="RAZORPAY_WEBHOOK",
            action="PROCESS_WEBHOOK",
            details=f"Received and processed Razorpay webhook event '{event_type}' (ID: {event_id})"
        )
        db.add(audit)
        db.commit()

        return {"status": "success", "event_id": event_id, "event_type": event_type}

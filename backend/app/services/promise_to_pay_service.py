import re
from datetime import datetime, timedelta

class PromiseToPayService:
    @staticmethod
    def extract_promise(text: str) -> dict:
        lower_text = text.lower()

        # Check for stop outreach / opt-out
        if re.search(r"don'?t contact|stop calling|remove me|opt out|do not call", lower_text):
            return {
                "has_promise": False,
                "opt_out": True,
                "already_paid": False,
                "amount": 0.0,
                "promised_date": None,
                "confidence": 1.0,
                "recommendation": "STOP_AUTOMATED_OUTREACH"
            }

        # Check for already paid statement
        if re.search(r"already paid|paid via|sent by bank|transferred yesterday|completed payment", lower_text):
            return {
                "has_promise": False,
                "opt_out": False,
                "already_paid": True,
                "amount": 0.0,
                "promised_date": None,
                "confidence": 0.95,
                "recommendation": "STOP_OUTREACH_AND_VERIFY_TRANSACTION"
            }

        # Match amount (e.g., ₹40,000 or 40000 or 40k)
        amount = 0.0
        amt_match = re.search(r"(?:₹|rs\.?|inr)?\s*([\d,]+)(?:\s*k)?", lower_text)
        if amt_match:
            val_str = amt_match.group(1).replace(",", "")
            try:
                amount = float(val_str)
                if "k" in amt_match.group(0):
                    amount *= 1000.0
            except ValueError:
                amount = 0.0

        # Match day / date
        promised_dt = datetime.utcnow() + timedelta(days=3)
        if "tomorrow" in lower_text:
            promised_dt = datetime.utcnow() + timedelta(days=1)
        elif "friday" in lower_text:
            promised_dt = datetime.utcnow() + timedelta(days=2)
        elif "monday" in lower_text:
            promised_dt = datetime.utcnow() + timedelta(days=5)

        has_promise = amount > 0 or "will pay" in lower_text or "promise" in lower_text or "by" in lower_text

        return {
            "has_promise": has_promise,
            "opt_out": False,
            "already_paid": False,
            "amount": amount,
            "promised_date": promised_dt.strftime("%Y-%m-%d"),
            "confidence": 0.92 if amount > 0 else 0.70,
            "recommendation": "RECORD_P2P_AND_PAUSE_REMINDERS" if has_promise else "CONTINUE_NORMAL_FLOW"
        }

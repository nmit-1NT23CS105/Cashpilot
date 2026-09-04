from sqlalchemy.orm import Session
from ..database.models import Customer, Invoice, Payment

class CustomerIntelligenceService:
    @staticmethod
    def calculate_reliability_score(customer: Customer) -> float:
        # Multi-factor score formula (0 - 100)
        # Factor 1: On-time payment rate (35%)
        f1_ontime = customer.on_time_payment_rate * 35.0

        # Factor 2: Average delay penalty (25%)
        # Delay 0 days = 25 pts, Delay >15 days = 0 pts
        f2_delay = max(0.0, 25.0 - (customer.avg_payment_delay_days * 1.66))

        # Factor 3: Overdue Ratio (20%)
        overdue_ratio = (customer.overdue_count / max(1, customer.total_transactions_count))
        f3_overdue = max(0.0, 20.0 * (1.0 - overdue_ratio))

        # Factor 4: Payment volume ratio paid (20%)
        paid_ratio = (customer.total_paid_val / max(1.0, customer.total_purchases_val))
        f4_paid = min(20.0, paid_ratio * 20.0)

        score = round(f1_ontime + f2_delay + f3_overdue + f4_paid, 1)
        return min(100.0, max(0.0, score))

    @staticmethod
    def update_customer_intelligence(db: Session, customer_id: str):
        cust = db.query(Customer).filter(Customer.id == customer_id).first()
        if not cust:
            return None

        invoices = db.query(Invoice).filter(Invoice.customer_id == customer_id).all()
        if not invoices:
            return cust

        total_inv = len(invoices)
        paid_inv = [i for i in invoices if i.status == "PAID"]
        overdue_inv = [i for i in invoices if i.status == "OVERDUE"]

        cust.total_transactions_count = total_inv
        cust.on_time_payment_rate = round(len(paid_inv) / max(1, total_inv), 2)
        cust.overdue_count = len(overdue_inv)

        cust.total_purchases_val = sum(i.total_amount for i in invoices)
        cust.total_paid_val = sum(i.paid_amount for i in invoices)
        cust.current_outstanding = sum(i.outstanding_amount for i in invoices)

        # Detect trend
        old_score = cust.reliability_score
        new_score = CustomerIntelligenceService.calculate_reliability_score(cust)
        cust.reliability_score = new_score

        if new_score < old_score - 10.0 or cust.avg_payment_delay_days > 10.0:
            cust.behavior_trend = "DETERIORATING"
            cust.segment = "HIGH_RISK" if new_score < 50 else "DETERIORATING"
        elif new_score > old_score + 10.0:
            cust.behavior_trend = "IMPROVING"
            cust.segment = "IMPROVING"
        else:
            cust.behavior_trend = "STABLE"

        db.commit()
        return cust

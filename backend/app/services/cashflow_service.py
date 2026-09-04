from collections import defaultdict
from datetime import datetime, timedelta
import math
from sqlalchemy.orm import Session
from ..database.models import Merchant, Invoice, SupplierPayable, Expense, LedgerAccount, RepaymentPrediction

class CashflowService:
    @staticmethod
    def forecast_7_15_days(db: Session, forecast_days: int = 15, custom_buffer: float = None):
        forecast_days = max(7, min(30, int(forecast_days)))
        merchant = db.query(Merchant).first()
        min_buffer = custom_buffer if custom_buffer is not None else (merchant.min_cash_buffer if merchant else 200000.0)

        cash_acct = db.query(LedgerAccount).filter(LedgerAccount.code == "1010").first()
        current_cash = float(merchant.current_cash or 0.0) if merchant else (float(cash_acct.balance or 0.0) if cash_acct else 450000.0)

        today = datetime.utcnow().date()
        daily_forecast = []
        running_cash = current_cash
        has_liquidity_violation = False
        min_projected_cash = current_cash
        first_violation_day = None

        open_invoices = db.query(Invoice).filter(Invoice.outstanding_amount > 0).all()
        open_payables = db.query(SupplierPayable).filter(SupplierPayable.outstanding_amount > 0).all()
        recurring_expenses = db.query(Expense).filter(Expense.is_recurring == True).all()

        total_expected_inflow = 0.0
        total_scheduled_outflow = 0.0

        collection_candidates = []
        for inv in open_invoices:
            cust = inv.customer
            if not cust or cust.opt_out_contact:
                continue

            pred = (
                db.query(RepaymentPrediction)
                .filter(RepaymentPrediction.invoice_id == inv.id)
                .order_by(RepaymentPrediction.created_at.desc())
                .first()
            )
            prob = pred.repayment_probability_15d if pred else min(0.98, max(0.15, cust.on_time_payment_rate))
            expected_days = pred.expected_payment_days if pred else max(1.0, cust.avg_payment_delay_days)

            promised_day = None
            if cust.has_active_p2p and cust.p2p_promised_date:
                try:
                    promised_date = datetime.strptime(cust.p2p_promised_date, "%Y-%m-%d").date()
                    promised_day = (promised_date - today).days
                except ValueError:
                    promised_day = None

            target_day = promised_day if promised_day is not None else int(math.ceil(expected_days))
            target_day = max(1, min(forecast_days - 1, target_day))
            expected_recovery = inv.outstanding_amount * prob
            overdue_boost = 1.3 if inv.status == "OVERDUE" else 1.0
            priority_score = (expected_recovery / max(1, target_day)) * overdue_boost

            collection_candidates.append({
                "invoice_id": inv.id,
                "customer_name": cust.name,
                "amount": expected_recovery,
                "probability": prob,
                "target_day": target_day,
                "priority_score": priority_score,
                "event": f"{cust.name}: expected collection ₹{expected_recovery:,.0f}",
            })

        scheduled_inflows = defaultdict(list)
        scheduled_ids = set()
        daily_collection_capacity = 2
        for day_offset in range(forecast_days):
            eligible = [
                c for c in collection_candidates
                if c["invoice_id"] not in scheduled_ids and c["target_day"] <= day_offset
            ]
            eligible.sort(key=lambda c: c["priority_score"], reverse=True)
            for candidate in eligible[:daily_collection_capacity]:
                scheduled_inflows[day_offset].append(candidate)
                scheduled_ids.add(candidate["invoice_id"])

        for day_offset in range(forecast_days):
            target_date = today + timedelta(days=day_offset)

            events = []
            inflow_today = sum(c["amount"] for c in scheduled_inflows[day_offset])
            events.extend(c["event"] for c in scheduled_inflows[day_offset][:3])

            outflow_today = 0.0
            for sp in open_payables:
                if sp.due_date and sp.due_date.date() == target_date:
                    outflow_today += sp.outstanding_amount
                    supplier_name = sp.supplier.name if sp.supplier else "Supplier"
                    events.append(f"{supplier_name}: payable due ₹{sp.outstanding_amount:,.0f}")

            # Accrue recurring monthly expenses across the forecast window instead of
            # pretending the whole monthly bill arrives on a single unknown date.
            if day_offset in [3, 7, 11, 15]:
                for exp in recurring_expenses:
                    if exp.frequency == "MONTHLY":
                        accrued = exp.amount / 4.0
                        outflow_today += accrued
                        if exp.is_anomaly:
                            events.append(f"{exp.title}: anomaly review accrual ₹{accrued:,.0f}")

            start_cash = running_cash
            running_cash = start_cash + inflow_today - outflow_today
            
            if running_cash < min_projected_cash:
                min_projected_cash = running_cash

            is_violation = running_cash < min_buffer
            if is_violation:
                has_liquidity_violation = True
                if first_violation_day is None:
                    first_violation_day = day_offset

            shortfall = max(0.0, min_buffer - running_cash)

            total_expected_inflow += inflow_today
            total_scheduled_outflow += outflow_today

            net_flow = inflow_today - outflow_today
            daily_record = {
                "day": day_offset,
                "day_offset": day_offset,
                "date": target_date.strftime("%Y-%m-%d"),
                "display_date": target_date.strftime("%b %d"),
                "starting_cash": round(start_cash, 2),
                "inflow_expected": round(inflow_today, 2),
                "outflow_scheduled": round(outflow_today, 2),
                "net_flow": round(net_flow, 2),
                "inflow": round(inflow_today, 2),
                "outflow": round(outflow_today, 2),
                "projected_cash": round(running_cash, 2),
                "safety_buffer": round(min_buffer, 2),
                "min_buffer": round(min_buffer, 2),
                "buffer_violation": is_violation,
                "is_violation": is_violation,
                "shortfall": round(shortfall, 2),
                "events": events,
            }
            daily_forecast.append(daily_record)

        return {
            "current_cash": round(current_cash, 2),
            "min_cash_buffer": round(min_buffer, 2),
            "forecast_days": forecast_days,
            "total_expected_inflow": round(total_expected_inflow, 2),
            "total_scheduled_outflow": round(total_scheduled_outflow, 2),
            "total_expected_outflow": round(total_scheduled_outflow, 2),
            "net_projected_change": round(total_expected_inflow - total_scheduled_outflow, 2),
            "min_projected_cash": round(min_projected_cash, 2),
            "has_liquidity_violation": has_liquidity_violation,
            "first_violation_day": first_violation_day,
            "max_shortfall": round(max(0.0, min_buffer - min_projected_cash), 2),
            "daily_forecast": daily_forecast,
            "daily_forecasts": daily_forecast,
        }

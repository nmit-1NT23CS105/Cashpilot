from collections import defaultdict
from datetime import datetime
import math
from typing import Callable, Dict, List

from sqlalchemy.orm import Session

from ..database.models import Expense, Invoice, LedgerAccount, SimulationRun, SupplierPayable
from .ml_repayment_service import ml_repayment_service


class SimulationService:
    @staticmethod
    def _prediction(invoice: Invoice) -> Dict:
        if invoice.predictions:
            prediction = sorted(invoice.predictions, key=lambda item: item.created_at, reverse=True)[0]
            return {
                "repayment_probability_15d": prediction.repayment_probability_15d,
                "expected_payment_days": prediction.expected_payment_days,
                "confidence": prediction.confidence_level,
            }
        customer = invoice.customer
        if not customer:
            return {"repayment_probability_15d": 0.0, "expected_payment_days": 15.0}
        return ml_repayment_service.predict_invoice_repayment(customer, invoice.outstanding_amount)

    @staticmethod
    def _expense_outflows(expenses: List[Expense], defer_noncritical: bool) -> Dict[int, float]:
        outflows = defaultdict(float)
        for expense in expenses:
            if not expense.is_recurring:
                continue
            if defer_noncritical and not expense.is_anomaly:
                day = 11
            else:
                day = 3 if expense.is_anomaly else 7
            outflows[day] += expense.amount / 4.0
        return outflows

    @staticmethod
    def _payable_outflows(payables: List[SupplierPayable], code: str) -> Dict[int, float]:
        today = datetime.utcnow().date()
        outflows = defaultdict(float)

        for payable in payables:
            due_day = (payable.due_date.date() - today).days if payable.due_date else 15
            due_day = max(0, min(14, due_day))

            if code == "CASHPILOT" and payable.priority_level == "CRITICAL" and due_day <= 1:
                outflows[1] += round(payable.outstanding_amount * 0.62, 2)
                outflows[4] += round(payable.outstanding_amount * 0.38, 2)
            elif code == "CASHPILOT" and payable.priority_level != "CRITICAL":
                outflows[max(due_day, 8)] += payable.outstanding_amount
            else:
                outflows[due_day] += payable.outstanding_amount

        return outflows

    @staticmethod
    def _run_strategy(
        db: Session,
        code: str,
        name: str,
        selector: Callable[[Invoice, Dict], bool],
        custom_buffer: float,
        action_cost: float,
        friction: str,
        accelerate: bool,
        defer_noncritical: bool,
    ) -> Dict:
        cash_account = db.query(LedgerAccount).filter(LedgerAccount.code == "1010").first()
        current_cash = cash_account.balance if cash_account else 450000.0
        invoices = db.query(Invoice).filter(Invoice.outstanding_amount > 0).all()
        payables = db.query(SupplierPayable).filter(SupplierPayable.outstanding_amount > 0).all()
        expenses = db.query(Expense).all()

        inflows = defaultdict(float)
        selected_actions = []

        for invoice in invoices:
            prediction = SimulationService._prediction(invoice)
            if not selector(invoice, prediction):
                continue

            probability = prediction["repayment_probability_15d"]
            expected_recovery = invoice.outstanding_amount * probability
            expected_day = int(math.ceil(prediction["expected_payment_days"]))
            day = max(1, min(14, expected_day - 1 if accelerate and probability >= 0.75 else expected_day))
            inflows[day] += expected_recovery
            selected_actions.append({
                "invoice_id": invoice.id,
                "customer": invoice.customer.name if invoice.customer else "Customer",
                "expected_recovery": round(expected_recovery, 2),
                "probability": probability,
                "day": day,
            })

        outflows = SimulationService._payable_outflows(payables, code)
        expense_outflows = SimulationService._expense_outflows(expenses, defer_noncritical)
        for day, amount in expense_outflows.items():
            outflows[day] += amount

        operating_cost = len(selected_actions) * action_cost
        running_cash = current_cash - operating_cost
        minimum_cash = running_cash
        liquidity_violations = 0
        cash_path = []

        for day in range(15):
            starting_cash = running_cash
            running_cash = running_cash + inflows[day] - outflows[day]
            minimum_cash = min(minimum_cash, running_cash)
            is_violation = running_cash < custom_buffer
            if is_violation:
                liquidity_violations += 1
            cash_path.append({
                "day": day,
                "starting_cash": round(starting_cash, 2),
                "inflow": round(inflows[day], 2),
                "outflow": round(outflows[day], 2),
                "ending_cash": round(running_cash, 2),
                "buffer_violation": is_violation,
            })

        gross_recovery = sum(action["expected_recovery"] for action in selected_actions)
        net_recovery = gross_recovery - operating_cost
        return {
            "name": name,
            "code": code,
            "gross_recovery": round(gross_recovery, 2),
            "net_recovery": round(net_recovery, 2),
            "expected_cash": round(running_cash, 2),
            "minimum_cash": round(minimum_cash, 2),
            "operational_cost": round(operating_cost, 2),
            "action_count": len(selected_actions),
            "customer_contact_count": len(selected_actions),
            "liquidity_violations": liquidity_violations,
            "customer_friction": friction,
            "roi": round(net_recovery / max(1.0, operating_cost), 2),
            "cash_path": cash_path,
            "selected_actions": selected_actions[:12],
        }

    @staticmethod
    def run_strategy_simulation(db: Session, custom_buffer: float = 200000.0) -> Dict:
        strategies = [
            SimulationService._run_strategy(
                db,
                "RETRY_ALL",
                "Retry Everyone",
                lambda invoice, prediction: bool(invoice.customer and not invoice.customer.opt_out_contact),
                custom_buffer,
                action_cost=120.0,
                friction="HIGH",
                accelerate=False,
                defer_noncritical=False,
            ),
            SimulationService._run_strategy(
                db,
                "CASHPILOT",
                "CashPilot Strategy",
                lambda invoice, prediction: bool(
                    invoice.customer
                    and not invoice.customer.opt_out_contact
                    and prediction["repayment_probability_15d"] >= 0.65
                ),
                custom_buffer,
                action_cost=30.0,
                friction="LOW",
                accelerate=True,
                defer_noncritical=True,
            ),
            SimulationService._run_strategy(
                db,
                "CONSERVATIVE",
                "Conservative Strategy",
                lambda invoice, prediction: bool(
                    invoice.customer
                    and not invoice.customer.opt_out_contact
                    and prediction["repayment_probability_15d"] >= 0.90
                ),
                custom_buffer,
                action_cost=20.0,
                friction="VERY_LOW",
                accelerate=False,
                defer_noncritical=True,
            ),
            SimulationService._run_strategy(
                db,
                "AGGRESSIVE",
                "Aggressive Recovery",
                lambda invoice, prediction: bool(
                    invoice.customer
                    and not invoice.customer.opt_out_contact
                    and (invoice.status == "OVERDUE" or invoice.outstanding_amount >= 100000.0)
                ),
                custom_buffer,
                action_cost=90.0,
                friction="HIGH",
                accelerate=True,
                defer_noncritical=False,
            ),
        ]

        db.add(SimulationRun(
            scenario_name="Strategy comparison",
            summary_json={
                "custom_buffer": custom_buffer,
                "strategy_count": len(strategies),
                "best_strategy": min(strategies, key=lambda item: (item["liquidity_violations"], -item["net_recovery"]))["code"],
            },
        ))
        db.commit()

        return {
            "custom_buffer": custom_buffer,
            "strategies": strategies,
            "disclaimer": "Simulation uses current synthetic/demo data and deterministic strategy assumptions.",
        }

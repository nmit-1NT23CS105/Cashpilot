import re
from datetime import datetime
from sqlalchemy.orm import Session
from .decision_engine import DecisionEngine
from .cashflow_service import CashflowService
from .ledger_service import LedgerService
from ..database.models import Customer, SupplierPayable, Expense, Invoice

class CopilotService:
    @staticmethod
    def query(db: Session, question: str) -> dict:
        question = (question or "").strip()
        if not question:
            return {"question": question, "answer": "Ask me about cash, customers, invoices, suppliers, expenses, payments, or business decisions.", "type": "HELP"}
        q = question.lower()

        if any(token in q for token in ["what can you do", "help", "capabilities", "how can you help"]):
            return {"question": question, "answer": "I can analyze your cash position, forecast liquidity, rank collections, explain customer risk, prioritize suppliers, review expenses, prepare payment-link recommendations, run business scenarios, and explain ledger numbers. I cannot move money or change records without your approval.", "type": "CAPABILITIES"}

        if any(token in q for token in ["payment link", "send payment link", "generate payment link", "collect payment", "payment reminder"]):
            plan = DecisionEngine.generate_daily_action_plan(db)
            customer_actions = [a for a in plan["action_items"] if a["target_type"] == "CUSTOMER" and a["action_type"] in {"SEND_PAYMENT_LINK", "SEND_REMINDER"}][:3]
            if not customer_actions:
                resp = "No high-confidence collections are ready for automated payment-link outreach right now. The next best move is to review the customer risk list and prioritize overdue invoices with the lowest reliability score."
            else:
                names = ", ".join(a["target_name"] for a in customer_actions)
                total_amt = sum(a["amount"] for a in customer_actions)
                resp = (
                    f"The AI copilot recommends action on {names}. "
                    f"These accounts represent INR {total_amt:,.2f} in collectable value with strong probability of recovery, "
                    "so the best play is to send a Razorpay payment link and follow up with a 24-hour reminder if not paid."
                )
            return {"question": question, "answer": resp, "type": "RAZORPAY_ACTION_RECOMMENDATION", "data": customer_actions}

        if any(token in q for token in ["cashflow", "cash flow", "forecast", "7 day", "15 day", "liquidity"]):
            cf = CashflowService.forecast_7_15_days(db, forecast_days=15)
            status = "healthy" if not cf["has_liquidity_violation"] else "at risk"
            resp = (
                f"Your projected liquidity is {status}. Current cash is ₹{cf['current_cash']:,.2f}, the minimum expected balance is ₹{cf['min_projected_cash']:,.2f}, "
                f"and the business buffer is ₹{cf['min_cash_buffer']:,.2f}. The model is flagging the highest pressure around Day {cf['first_violation_day'] or 'N/A'}."
            )
            return {"question": question, "answer": resp, "type": "LIQUIDITY_FORECAST", "data": cf}

        if any(token in q for token in ["supplier", "pay supplier", "manufacture", "vendor", "payables"]):
            plan = DecisionEngine.generate_daily_action_plan(db)
            supplier_actions = [a for a in plan["action_items"] if a["target_type"] == "SUPPLIER"][:3]
            resp = "Supplier scheduling should prioritize the highest-risk obligations first and only pay within the liquidity buffer."
            if supplier_actions:
                top = supplier_actions[0]
                resp = (
                    f"The best supplier action is {top['target_name']} for INR {top['amount']:,.2f}. "
                    "The engine is prioritizing urgency, discount leverage, and the cash-buffer constraint before pushing payments out."
                )
            return {"question": question, "answer": resp, "type": "SUPPLIER_PRIORITY", "data": supplier_actions}

        # Question 1: Who should I collect from today?
        if "who" in q and ("collect" in q or "today" in q or "prioritize" in q):
            plan = DecisionEngine.generate_daily_action_plan(db)
            customer_actions = [a for a in plan["action_items"] if a["target_type"] == "CUSTOMER"][:3]
            names = [a['target_name'] for a in customer_actions] or ["no open buyer invoices"]
            total_amt = sum(a['amount'] for a in customer_actions)
            
            resp = (
                f"I recommend prioritizing collection from **{', '.join(names)}** today. "
                f"Together they account for **₹{total_amt:,.2f}** in outstanding receivables. "
                f"The ranking uses each buyer's live repayment probability, invoice value, and expected payment timing."
            )
            return {"question": question, "answer": resp, "type": "COLLECTION_ADVICE", "data": customer_actions}

        if "why" in q and ("risk" in q or "customer" in q or "buyer" in q):
            customers = sorted(db.query(Customer).all(), key=lambda item: item.reliability_score)
            cust = customers[0] if customers else None
            if cust:
                resp = (f"**{cust.name}** has the lowest buyer reliability score at **{int(cust.reliability_score)}/100**. "
                        f"Average payment delay is {cust.avg_payment_delay_days:.1f} days, on-time rate is {cust.on_time_payment_rate:.0%}, "
                        f"and current outstanding balance is ₹{cust.current_outstanding:,.2f}.")
            else:
                resp = "No buyer history is available yet. Add buyers and sales to generate risk insights."
            return {"question": question, "answer": resp, "type": "RISK_EXPLANATION"}

        # Question 3: Will I have enough cash to pay Manufacturer X?
        if "manufacturer" in q or ("pay" in q and "enough cash" in q) or "supplier" in q:
            cf = CashflowService.forecast_7_15_days(db, forecast_days=7)
            if cf["has_liquidity_violation"]:
                due = sorted(db.query(SupplierPayable).filter(SupplierPayable.outstanding_amount > 0).all(), key=lambda item: item.due_date or datetime.max)
                payable = due[0] if due else None
                supplier_name = payable.supplier.name if payable and payable.supplier else "an upcoming supplier"
                resp = (f"**Not without action.** Projected cash falls **₹{cf['max_shortfall']:,.2f} below the ₹{cf['min_cash_buffer']:,.2f} buffer** "
                        f"on Day {cf['first_violation_day']}. The nearest obligation is **{supplier_name}**; review the ranked AI actions and collect the highest-value buyer invoice first.")
            else:
                resp = f"Yes, your current cash of ₹{cf['current_cash']:,.2f} is sufficient to cover upcoming supplier payments."
            return {"question": question, "answer": resp, "type": "LIQUIDITY_CHECK", "data": cf}

        # Question 4: What are my biggest expenses this month?
        if any(token in q for token in ["expense", "cost", "spend", "budget", "save money"]):
            expenses = db.query(Expense).all()
            expenses_sorted = sorted(expenses, key=lambda e: e.amount, reverse=True)[:4]
            exp_txt = ", ".join([f"**{e.title}** (₹{e.amount:,.2f})" for e in expenses_sorted])
            resp = f"Your largest recorded expenses are: {exp_txt or 'none yet'}." 
            return {"question": question, "answer": resp, "type": "EXPENSE_SUMMARY"}

        if any(token in q for token in ["summary", "overview", "health", "doing", "performance"]):
            kpis = {
                "cash": CashflowService.forecast_7_15_days(db, forecast_days=7),
                "plan": DecisionEngine.generate_daily_action_plan(db),
            }
            resp = (
                f"Your business currently has ₹{kpis['cash']['current_cash']:,.2f} cash and ₹{kpis['plan']['total_receivables']:,.2f} in open receivables. "
                f"The next 7 days are {'healthy' if not kpis['cash']['has_liquidity_violation'] else 'under liquidity pressure'}, with ₹{kpis['cash']['min_projected_cash']:,.2f} as the lowest projected balance. "
                f"There are {kpis['plan']['total_actions']} recommended actions in the queue."
            )
            return {"question": question, "answer": resp, "type": "BUSINESS_SUMMARY", "data": kpis["cash"]}

        # Default Intelligent Summary
        plan = DecisionEngine.generate_daily_action_plan(db)
        resp = (
            f"I can help with that, but I need a little more direction. Based on your live business data, cash is ₹{plan['current_cash']:,.2f}, "
            f"expected recovery is ₹{plan['expected_recovery']:,.2f}, and your safety buffer is ₹{plan['min_cash_buffer']:,.2f}. "
            "Try asking: 'Who should I collect from?', 'Can I pay this supplier?', 'Why is my cash falling?', or 'Give me a business summary.'"
        )
        return {"question": question, "answer": resp, "type": "GENERAL_GUIDANCE"}

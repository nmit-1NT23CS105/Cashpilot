import re
from typing import Tuple

class ExpenseService:
    CATEGORY_MAPPINGS = [
        (r"rent|warehouse|lease|premise", "Rent & Infrastructure", "FIXED"),
        (r"salary|wages|staff|payroll|labour|unloading", "Salaries & Payroll", "FIXED"),
        (r"electricity|power|bescom|mseb|board|light", "Electricity & Utilities", "VARIABLE"),
        (r"fuel|transport|freight|delivery|logistics|courier", "Delivery & Freight", "VARIABLE"),
        (r"software|zoho|tally|aws|google|cloud|subscription", "Software & Subscriptions", "TECH"),
        (r"wifi|internet|jio|airtel|telecom|phone", "Internet & Communication", "TECH"),
        (r"bank|interest|overdraft|charge|fee|loan", "Bank Charges & Interest", "FINANCIAL"),
        (r"gst|tds|tax|statutory|penalty", "GST & Statutory Taxes", "STATUTORY"),
        (r"office|stationery|tea|supplies|misc", "Office Supplies & Miscellaneous", "MISC")
    ]

    @staticmethod
    def classify_expense(description: str) -> Tuple[str, str]:
        text = description.lower()
        for pattern, cat_name, cat_type in ExpenseService.CATEGORY_MAPPINGS:
            if re.search(pattern, text):
                return cat_name, cat_type
        return "Office Supplies & Miscellaneous", "MISC"

    @staticmethod
    def check_anomaly(amount: float, historical_avg: float) -> Tuple[bool, str]:
        if not historical_avg or historical_avg <= 0:
            return False, None
        
        ratio = amount / historical_avg
        if ratio >= 1.75: # 75% or higher above average
            percent = int((ratio - 1.0) * 100)
            return True, f"Expense amount of ₹{amount:,.2f} is {percent}% above historical monthly average (₹{historical_avg:,.2f})."
        
        return False, None

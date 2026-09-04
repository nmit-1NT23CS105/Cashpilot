import random
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from ..database.models import (
    Merchant, Manufacturer, Supplier, Customer, ProductCategory, Product,
    Invoice, Payment, SupplierPayable, ExpenseCategory, Expense,
    LedgerAccount, LedgerEntry, RepaymentPrediction, AIAction, AuditLog
)

MANUFACTURERS_DATA = [
    {"name": "Apex FMCG Industries", "contact": "Rajesh Kumar", "email": "rajesh@apexfmcg.com", "phone": "+91 98765 43210"},
    {"name": "Titan Consumer Products", "contact": "Anita Sharma", "email": "anita@titanconsumer.com", "phone": "+91 98123 45678"},
    {"name": "Global Retail Wholesalers", "contact": "Vikram Sethi", "email": "vikram@globalretail.in", "phone": "+91 99887 76655"},
    {"name": "Pinnacle Dairy & Beverage Co.", "contact": "Suresh Patel", "email": "suresh@pinnacledairy.com", "phone": "+91 97654 32109"},
    {"name": "Zenith Personal Care Ltd.", "contact": "Meera Joshi", "email": "meera@zenithcare.in", "phone": "+91 96543 21098"}
]

SUPPLIERS_DATA = [
    {"name": "Apex FMCG Industries", "category": "FMCG Inventory", "criticality": "CRITICAL", "terms": "NET_15", "discount": 2.0, "penalty": 1.5},
    {"name": "Titan Packaging Solutions", "category": "Packaging & Materials", "criticality": "HIGH", "terms": "NET_15", "discount": 1.5, "penalty": 1.0},
    {"name": "Pinnacle Cold-Chain Logistics", "category": "Transportation & Logistics", "criticality": "HIGH", "terms": "NET_7", "discount": 1.0, "penalty": 2.0},
    {"name": "Metro Power & Utilities", "category": "Electricity Board", "criticality": "CRITICAL", "terms": "NET_7", "discount": 0.0, "penalty": 3.0},
    {"name": "CloudTech Enterprise Systems", "category": "Software Subscriptions", "criticality": "MEDIUM", "terms": "NET_30", "discount": 5.0, "penalty": 1.0}
]

EXPENSE_CATEGORIES_DATA = [
    ("Rent & Infrastructure", "FIXED"),
    ("Salaries & Payroll", "FIXED"),
    ("Electricity & Utilities", "VARIABLE"),
    ("Delivery & Freight", "VARIABLE"),
    ("Fuel & Maintenance", "VARIABLE"),
    ("Software & Subscriptions", "TECH"),
    ("Internet & Communication", "TECH"),
    ("Bank Charges & Interest", "FINANCIAL"),
    ("GST & Statutory Taxes", "STATUTORY"),
    ("Daily Wages & Casual Labour", "VARIABLE"),
    ("Office Supplies & Miscellaneous", "MISC")
]

LEDGER_ACCOUNTS_DATA = [
    ("1010", "Cash & Bank Account", "ASSET"),
    ("1020", "Accounts Receivable", "ASSET"),
    ("1030", "Inventory Account", "ASSET"),
    ("2010", "Accounts Payable", "LIABILITY"),
    ("2020", "GST Payable / Statutory", "LIABILITY"),
    ("3010", "Owner's Capital", "EQUITY"),
    ("4010", "Sales Revenue", "REVENUE"),
    ("5010", "Cost of Goods Sold", "EXPENSE"),
    ("5020", "Rent Expense", "EXPENSE"),
    ("5030", "Salaries Expense", "EXPENSE"),
    ("5040", "Utilities Expense", "EXPENSE"),
    ("5050", "Logistics & Delivery Expense", "EXPENSE"),
    ("5060", "Software & IT Expense", "EXPENSE"),
    ("5070", "Financial Charges", "EXPENSE"),
]

CUSTOMER_TYPES = [
    {"segment": "RELIABLE", "weight": 0.40, "on_time": (0.88, 0.98), "delay": (0.5, 3.0), "score": (85, 98)},
    {"segment": "SLOW_PAYER", "weight": 0.25, "on_time": (0.55, 0.75), "delay": (8.0, 18.0), "score": (55, 75)},
    {"segment": "HIGH_RISK", "weight": 0.15, "on_time": (0.25, 0.50), "delay": (15.0, 35.0), "score": (25, 50)},
    {"segment": "NEW_CUSTOMER", "weight": 0.10, "on_time": (0.70, 0.85), "delay": (2.0, 7.0), "score": (60, 75)},
    {"segment": "DETERIORATING", "weight": 0.05, "on_time": (0.40, 0.60), "delay": (10.0, 22.0), "score": (40, 60)},
    {"segment": "IMPROVING", "weight": 0.05, "on_time": (0.80, 0.92), "delay": (2.0, 5.0), "score": (78, 90)},
]

STORE_NAMES = [
    "Metro Supermarket", "City Retail Hub", "Vanguard Provisions", "Greenline Organics",
    "Apex Hypermarket", "Star General Store", "Sunshine Traders", "Royal Departmental",
    "Evergreen Mart", "Grand Wholesale Bazaar", "Zenith Grocery Store", "Prime Corner Shop",
    "Universal Mart", "Fortune Retailers", "Navrang Stores", "Shree Balaji Wholesalers",
    "Sai Ram Traders", "Mahaveer Superstore", "Golden Spices & Foods", "National Enterprise"
]

def generate_synthetic_data(db: Session):
    # Check if merchant already exists
    merchant = db.query(Merchant).first()
    if merchant:
        return merchant

    print("Generating realistic synthetic dataset for CashPilot AI...")

    # 1. Create Merchant
    merchant = Merchant(
        name="Apex Wholesalers & Distributors Ltd",
        business_type="FMCG & Consumer Goods Distributor",
        currency="INR",
        min_cash_buffer=200000.0 # ₹2,00,000 Safety Cash Buffer
    )
    db.add(merchant)
    db.flush()

    # 2. Create Ledger Accounts
    accounts_dict = {}
    for code, name, acct_type in LEDGER_ACCOUNTS_DATA:
        acct = LedgerAccount(code=code, name=name, type=acct_type, balance=0.0)
        db.add(acct)
        accounts_dict[code] = acct
    db.flush()

    # Initial Capital Injection Ledger Entry
    initial_cash_entry = LedgerEntry(
        entry_number="LEG-10001",
        transaction_date=datetime.utcnow() - timedelta(days=60),
        debit_account="1010",
        credit_account="3010",
        amount=450000.0,
        description="Opening Bank Cash Capital Injection",
        source_type="MANUAL",
        is_approved=True,
        created_by="SYSTEM"
    )
    accounts_dict["1010"].balance += 450000.0
    accounts_dict["3010"].balance += 450000.0
    db.add(initial_cash_entry)

    # 3. Create Manufacturers & Products
    mfg_objects = []
    for mdata in MANUFACTURERS_DATA:
        mfg = Manufacturer(
            merchant_id=merchant.id,
            name=mdata["name"],
            contact_person=mdata["contact"],
            email=mdata["email"],
            phone=mdata["phone"]
        )
        db.add(mfg)
        mfg_objects.append(mfg)
    db.flush()

    # 100 Products across manufacturers
    product_objects = []
    product_categories = ["Beverages", "Packaged Foods", "Personal Care", "Dairy Products", "Home Care"]
    for i in range(1, 101):
        mfg = random.choice(mfg_objects)
        cat = random.choice(product_categories)
        purchase = round(random.uniform(200, 1500), 2)
        selling = round(purchase * random.uniform(1.15, 1.35), 2)
        prod = Product(
            manufacturer_id=mfg.id,
            sku=f"SKU-{1000+i}",
            name=f"{mfg.name.split()[0]} {cat} Item #{i}",
            purchase_price=purchase,
            selling_price=selling,
            stock_quantity=random.randint(50, 1000)
        )
        db.add(prod)
        product_objects.append(prod)
    db.flush()

    # 4. Create Suppliers & Payables
    supplier_objects = []
    for sdata in SUPPLIERS_DATA:
        sup = Supplier(
            merchant_id=merchant.id,
            name=sdata["name"],
            category=sdata["category"],
            criticality=sdata["criticality"],
            payment_terms=sdata["terms"],
            early_discount_percent=sdata["discount"],
            late_penalty_percent=sdata["penalty"],
            current_payable=0.0
        )
        db.add(sup)
        supplier_objects.append(sup)
    db.flush()

    # Create 8 Supplier Payables (Including Manufacturer X ₹5L due tomorrow for main scenario)
    today = datetime.utcnow()
    mfg_x_payable = SupplierPayable(
        supplier_id=supplier_objects[0].id, # Apex FMCG
        bill_number="BILL-SUP-9001",
        purchase_date=today - timedelta(days=14),
        due_date=today + timedelta(days=1), # Due tomorrow!
        total_amount=500000.0,
        paid_amount=0.0,
        outstanding_amount=500000.0,
        priority_level="CRITICAL",
        status="UNPAID"
    )
    supplier_objects[0].current_payable += 500000.0
    db.add(mfg_x_payable)

    payables_sample = [
        (supplier_objects[1], 120000.0, 5, "HIGH"),
        (supplier_objects[2], 85000.0, 7, "HIGH"),
        (supplier_objects[3], 41000.0, 3, "CRITICAL"), # Electricity bill
        (supplier_objects[4], 25000.0, 12, "MEDIUM")
    ]
    for sup, amt, days_due, prio in payables_sample:
        sp = SupplierPayable(
            supplier_id=sup.id,
            bill_number=f"BILL-{random.randint(1000, 9999)}",
            purchase_date=today - timedelta(days=10),
            due_date=today + timedelta(days=days_due),
            total_amount=amt,
            paid_amount=0.0,
            outstanding_amount=amt,
            priority_level=prio,
            status="UNPAID"
        )
        sup.current_payable += amt
        db.add(sp)

    # 5. Create 200 Customers
    customer_objects = []
    for i in range(1, 201):
        c_type = random.choices(
            CUSTOMER_TYPES,
            weights=[t["weight"] for t in CUSTOMER_TYPES]
        )[0]
        base_name = random.choice(STORE_NAMES)
        cust_name = f"{base_name} #{i}" if i > 20 else base_name
        
        on_time = round(random.uniform(*c_type["on_time"]), 2)
        delay = round(random.uniform(*c_type["delay"]), 1)
        score = round(random.uniform(*c_type["score"]), 1)
        
        cust = Customer(
            merchant_id=merchant.id,
            name=cust_name,
            phone=f"+91 98{random.randint(10000000, 99999999)}",
            email=f"contact@customer{i}.com",
            address=f"Shop #{i}, Commercial Complex, Sector {random.randint(1, 50)}",
            credit_period_days=15,
            credit_limit=random.choice([200000, 300000, 500000, 800000]),
            reliability_score=score,
            on_time_payment_rate=on_time,
            avg_payment_delay_days=delay,
            max_payment_delay_days=round(delay * random.uniform(2.0, 3.5), 1),
            segment=c_type["segment"],
            behavior_trend="STABLE" if c_type["segment"] != "DETERIORATING" else "DETERIORATING"
        )
        db.add(cust)
        customer_objects.append(cust)
    db.flush()

    # Explicit Setup for Main Demo Story Customers (Customer A, B, C, D)
    # Customer A: Reliable, ₹2,00,000 outstanding, 96% prob, expected 3 days
    cust_a = customer_objects[0]
    cust_a.name = "Customer A (Prime Retailers)"
    cust_a.segment = "RELIABLE"
    cust_a.reliability_score = 96.0
    cust_a.on_time_payment_rate = 0.96
    cust_a.avg_payment_delay_days = 1.2
    
    # Customer B: High Risk / Deteriorating, ₹3,00,000 outstanding, 48% prob, expected 10 days
    cust_b = customer_objects[1]
    cust_b.name = "Customer B (Metro Marts)"
    cust_b.segment = "HIGH_RISK"
    cust_b.behavior_trend = "DETERIORATING"
    cust_b.reliability_score = 48.0
    cust_b.on_time_payment_rate = 0.45
    cust_b.avg_payment_delay_days = 14.5
    
    # Customer C: Medium/High Reliable, ₹1,00,000 outstanding, 91% prob, expected 4 days
    cust_c = customer_objects[2]
    cust_c.name = "Customer C (Sunshine Superstore)"
    cust_c.segment = "RELIABLE"
    cust_c.reliability_score = 91.0
    cust_c.on_time_payment_rate = 0.91
    cust_c.avg_payment_delay_days = 2.8

    # Customer D: Overdue / Slow, ₹2,00,000 outstanding, 32% prob, expected 14+ days
    cust_d = customer_objects[3]
    cust_d.name = "Customer D (City Bazaar)"
    cust_d.segment = "SLOW_PAYER"
    cust_d.reliability_score = 35.0
    cust_d.on_time_payment_rate = 0.32
    cust_d.avg_payment_delay_days = 18.0

    # Promise to Pay Customer Example
    cust_p2p = customer_objects[4]
    cust_p2p.name = "Customer E (Royal Provisions - P2P Active)"
    cust_p2p.has_active_p2p = True
    cust_p2p.p2p_amount = 40000.0
    cust_p2p.p2p_promised_date = (today + timedelta(days=2)).strftime("%Y-%m-%d")
    cust_p2p.p2p_confidence = 0.92

    # 6. Generate 1,000+ Invoices & Payments (Past 60 Days)
    invoice_count = 0
    pay_counter = 0
    total_receivables_accum = 0.0

    # First add specific invoices for Customer A, B, C, D for Main Demo Scenario
    demo_invoices = [
        (cust_a, 200000.0, 3, "ISSUED"),   # Due in 3 days
        (cust_b, 300000.0, -5, "OVERDUE"), # 5 days overdue
        (cust_c, 100000.0, 4, "ISSUED"),   # Due in 4 days
        (cust_d, 200000.0, -12, "OVERDUE"),# 12 days overdue
        (cust_p2p, 40000.0, -2, "OVERDUE") # P2P promise
    ]

    for cust, amt, due_offset, status in demo_invoices:
        invoice_count += 1
        inv_num = f"INV-2026-{1000+invoice_count}"
        inv_date = today + timedelta(days=due_offset - 15)
        due_dt = today + timedelta(days=due_offset)
        
        inv = Invoice(
            merchant_id=merchant.id,
            customer_id=cust.id,
            invoice_number=inv_num,
            issue_date=inv_date,
            due_date=due_dt,
            total_amount=amt,
            paid_amount=0.0,
            outstanding_amount=amt,
            status=status,
            payment_terms_days=15
        )
        db.add(inv)
        db.flush()

        # Update customer metrics
        cust.current_outstanding += amt
        cust.total_purchases_val += amt
        cust.total_transactions_count += 1
        if status == "OVERDUE":
            cust.overdue_count += 1
        
        # Add Repayment Prediction
        prob = 0.96 if cust == cust_a else (0.48 if cust == cust_b else (0.91 if cust == cust_c else 0.32))
        exp_days = 3.0 if cust == cust_a else (10.0 if cust == cust_b else (4.0 if cust == cust_c else 14.5))
        pred = RepaymentPrediction(
            invoice_id=inv.id,
            customer_id=cust.id,
            repayment_probability_15d=prob,
            expected_payment_days=exp_days,
            confidence_level="HIGH" if prob > 0.8 or prob < 0.4 else "MEDIUM",
            factors={
                "on_time_rate": cust.on_time_payment_rate,
                "avg_delay": cust.avg_payment_delay_days,
                "reliability_score": cust.reliability_score,
                "historical_transactions": cust.total_transactions_count
            }
        )
        db.add(pred)

    # Now generate background invoices for other customers
    for cust in customer_objects:
        num_past_inv = random.randint(3, 8)
        for _ in range(num_past_inv):
            invoice_count += 1
            inv_num = f"INV-2026-{1000+invoice_count}"
            past_days = random.randint(5, 55)
            inv_date = today - timedelta(days=past_days)
            due_dt = inv_date + timedelta(days=15)
            
            amt = round(random.uniform(15000, 120000), 2)
            
            # Determine payment behavior
            is_paid = random.random() < cust.on_time_payment_rate
            if is_paid:
                paid_amt = amt
                out_amt = 0.0
                status = "PAID"
            else:
                if due_dt < today:
                    status = "OVERDUE"
                    paid_amt = random.choice([0.0, round(amt * 0.3, 2)])
                    out_amt = amt - paid_amt
                    cust.overdue_count += 1
                else:
                    status = "ISSUED"
                    paid_amt = 0.0
                    out_amt = amt
            
            inv = Invoice(
                merchant_id=merchant.id,
                customer_id=cust.id,
                invoice_number=inv_num,
                issue_date=inv_date,
                due_date=due_dt,
                total_amount=amt,
                paid_amount=paid_amt,
                outstanding_amount=out_amt,
                status=status,
                payment_terms_days=15
            )
            db.add(inv)
            db.flush()

            cust.total_purchases_val += amt
            cust.total_paid_val += paid_amt
            cust.current_outstanding += out_amt
            cust.total_transactions_count += 1

            if paid_amt > 0:
                pmt = Payment(
                    invoice_id=inv.id,
                    customer_id=cust.id,
                    payment_date=inv_date + timedelta(days=random.randint(2, 18)),
                    amount=paid_amt,
                    payment_method=random.choice(["Razorpay", "Bank_Transfer", "UPI"]),
                    status="SUCCESS",
                    transaction_reference=f"PAY-{random.randint(100000, 999999)}"
                )
                db.add(pmt)
                
                # Ledger entry for payment
                pay_counter += 1
                pay_entry = LedgerEntry(
                    entry_number=f"LEG-PAY-{10000 + pay_counter}",
                    transaction_date=pmt.payment_date,
                    debit_account="1010",
                    credit_account="1020",
                    amount=paid_amt,
                    description=f"Customer Payment received for {inv.invoice_number}",
                    source_type="PAYMENT",
                    source_id=pmt.id,
                    is_approved=True
                )
                db.add(pay_entry)

            if out_amt > 0:
                prob = round(min(0.98, max(0.15, cust.on_time_payment_rate + random.uniform(-0.1, 0.1))), 2)
                exp_d = round(max(1.0, cust.avg_payment_delay_days + random.uniform(-1, 3)), 1)
                pred = RepaymentPrediction(
                    invoice_id=inv.id,
                    customer_id=cust.id,
                    repayment_probability_15d=prob,
                    expected_payment_days=exp_d,
                    confidence_level="HIGH" if prob > 0.75 else "MEDIUM"
                )
                db.add(pred)

    # 7. Create Expense Categories & Expenses
    exp_cat_objs = {}
    for name, cat_type in EXPENSE_CATEGORIES_DATA:
        ec = ExpenseCategory(name=name, type=cat_type)
        db.add(ec)
        exp_cat_objs[name] = ec
    db.flush()

    # Expenses including Electricity Spike Anomaly
    expenses_list = [
        (exp_cat_objs["Rent & Infrastructure"], "Warehouse & Office Rent", 35000.0, True, "MONTHLY", 35000.0, False, None),
        (exp_cat_objs["Salaries & Payroll"], "Staff Salaries & Daily Wages", 65000.0, True, "MONTHLY", 65000.0, False, None),
        (exp_cat_objs["Electricity & Utilities"], "Industrial Power & Electricity Board", 41000.0, True, "MONTHLY", 20000.0, True, "Electricity expense is 105% above historical monthly average range (₹18k-₹22k)."),
        (exp_cat_objs["Delivery & Freight"], "Local Transport & Fuel Charges", 18500.0, True, "MONTHLY", 16000.0, False, None),
        (exp_cat_objs["Software & Subscriptions"], "Zoho ERP & Cloud Subscriptions", 4999.0, True, "MONTHLY", 4999.0, False, None),
        (exp_cat_objs["Internet & Communication"], "Jio Fiber High-Speed Internet", 2499.0, True, "MONTHLY", 2499.0, False, None),
        (exp_cat_objs["Bank Charges & Interest"], "Overdraft Interest & Facility Fee", 8500.0, False, "ONE_TIME", 8000.0, False, None)
    ]

    for cat_obj, title, amt, rec, freq, hist_avg, is_anom, anom_rsn in expenses_list:
        exp = Expense(
            merchant_id=merchant.id,
            category_id=cat_obj.id,
            title=title,
            amount=amt,
            expense_date=today - timedelta(days=random.randint(1, 10)),
            is_recurring=rec,
            frequency=freq,
            historical_avg=hist_avg,
            is_anomaly=is_anom,
            anomaly_reason=anom_rsn
        )
        db.add(exp)

    # 8. Create Initial Recommended AI Actions
    ai_actions_data = [
        ("SEND_PAYMENT_LINK", "CUSTOMER", cust_a.id, cust_a.name, 200000.0, 95.0, 0.96,
         "Customer A has a 96% repayment probability and high reliability (96/100). Sending an automated Razorpay payment link is expected to collect ₹2.0L within 3 days, securing liquidity ahead of the ₹5.0L supplier payment due tomorrow.", False, None),
        ("SEND_REMINDER", "CUSTOMER", cust_c.id, cust_c.name, 100000.0, 88.0, 0.91,
         "Customer C has 91% repayment probability. A polite payment reminder notice is recommended to ensure payment arrives before Day 4.", False, None),
        ("HUMAN_ESCALATION", "CUSTOMER", cust_b.id, cust_b.name, 300000.0, 78.0, 0.48,
         "Customer B has 5 days overdue invoice of ₹3.0L with deteriorating payment behavior (48% probability). High-value risk requires human finance manager follow-up rather than aggressive automated retries.", True, "High-Value Overdue Invoice with Low Repayment Confidence"),
        ("WAIT", "CUSTOMER", cust_d.id, cust_d.name, 200000.0, 40.0, 0.32,
         "Customer D repayment probability is 32%. Retrying automated payment immediately will increase customer contact fatigue without securing liquidity. Paused per AI Policy limits.", False, None),
        ("PRIORITIZE_SUPPLIER", "SUPPLIER", supplier_objects[0].id, supplier_objects[0].name, 500000.0, 98.0, 0.95,
         "Critical supplier payment of ₹5.0L due tomorrow to Apex FMCG. Review collections schedule to ensure bank cash stays above minimum ₹2.0L buffer after payment.", True, "Supplier Payment Exceeds ₹50,000 Policy Guardrail"),
        ("REVIEW_EXPENSE", "EXPENSE", exp_cat_objs["Electricity & Utilities"].id, "Electricity Board Bill", 41000.0, 85.0, 0.89,
         "Electricity bill of ₹41,000 is 105% above historical range (₹18k-₹22k). Flagged for human operational review before approving disbursement.", True, "Unusual Expense Anomaly Detected")
    ]

    for act_type, tgt_type, tgt_id, tgt_name, amt, prio, conf, exp_txt, req_appr, appr_rsn in ai_actions_data:
        act = AIAction(
            action_type=act_type,
            target_type=tgt_type,
            target_id=tgt_id,
            target_name=tgt_name,
            amount=amt,
            priority_score=prio,
            confidence=conf,
            explanation=exp_txt,
            status="RECOMMENDED",
            requires_approval=req_appr,
            approval_reason=appr_rsn
        )
        db.add(act)

    # 9. Audit Log Initial Entry
    audit = AuditLog(
        actor="SYSTEM",
        action="DATASET_INITIALIZATION",
        details="Synthetic distributor dataset generated with 200 customers, 100 products, 5 suppliers, double-entry ledger accounts, and demo scenarios."
    )
    db.add(audit)

    db.commit()
    print("Synthetic dataset created successfully!")
    return merchant

export interface DashboardKPIs {
    current_cash: number;
    min_cash_buffer: number;
    total_receivables: number;
    total_payables: number;
    revenue_at_risk: number;
    expected_recovery_7d: number;
    min_7d_cash: number;
    liquidity_status: 'HEALTHY' | 'LIQUIDITY_RISK';
    financial_health_score: number;
    health_factors: {
        liquidity: number;
        receivable_quality: number;
        payable_pressure: number;
        expense_stability: number;
        customer_base_reliability: number;
    };
}

export interface AIInsights {
    liquidity_status: string;
    financial_health_score: number;
    top_actions: ActionItem[];
    recommended_focus: string[];
    smart_summary: string;
}

export interface AIOverview {
    agents: Array<{ name: string; status: string; focus: string }>;
    cashflow: CashflowSummary;
    action_plan: { total_actions: number; expected_recovery: number; liquidity_status: string; action_items: ActionItem[] };
    customer_risk: Array<{ customer_id: string; customer_name: string; risk_score: number; risk_band: string; outstanding: number; factors: string[]; recommended_action: string }>;
    supplier_optimization: Array<{ payable_id: string; supplier_name: string; amount: number; due_in_days: number; priority_score: number; early_discount_value: number; late_penalty_value: number; recommended_action: string; explanation: string }>;
    expense_signals: Array<{ title: string; amount: number; reason: string }>;
    explainability: { method: string; llm_controls: string; human_approval: string };
    model_quality: { observed_invoice_outcomes: number; data_quality: number; confidence_note: string };
}

export interface CashflowForecastDay {
    day: number;
    date: string;
    inflow_expected: number;
    outflow_scheduled: number;
    net_flow: number;
    projected_cash: number;
    safety_buffer: number;
    buffer_violation: boolean;
    shortfall: number;
    events: string[];
}

export interface CashflowSummary {
    forecast_days: number;
    current_cash: number;
    min_cash_buffer: number;
    total_expected_inflow: number;
    total_scheduled_outflow: number;
    net_projected_change: number;
    has_liquidity_violation: boolean;
    first_violation_day: number | null;
    max_shortfall: number;
    min_projected_cash: number;
    daily_forecast: CashflowForecastDay[];
}

export interface ReceivableItem {
    invoice_id: string;
    invoice_number: string;
    customer_id: string;
    customer_name: string;
    segment: 'RELIABLE' | 'MODERATE' | 'HIGH_RISK' | 'CRITICAL_RISK';
    outstanding_amount: number;
    total_amount: number;
    issue_date: string;
    due_date: string;
    status: 'UNPAID' | 'PARTIALLY_PAID' | 'OVERDUE' | 'PAID';
    reliability_score: number;
    repayment_probability_15d: number;
    expected_payment_days: number;
    priority_score: number;
    prediction_confidence: string;
    expected_recoverable_amount: number;
    suggested_action: string;
}

export interface CustomerListItem {
    id: string;
    name: string;
    phone: string;
    email: string;
    segment: string;
    behavior_trend: string;
    reliability_score: number;
    on_time_payment_rate: number;
    avg_payment_delay_days: number;
    current_outstanding: number;
    total_purchases_val: number;
    total_paid_val: number;
    overdue_count: number;
    total_transactions_count: number;
    has_active_p2p: boolean;
    opt_out_contact: boolean;
}

export interface CustomerProfile {
    customer: {
        id: string;
        name: string;
        phone: string;
        email: string;
        reliability_score: number;
        segment: string;
        behavior_trend: string;
        on_time_payment_rate: number;
        avg_payment_delay_days: number;
        max_payment_delay_days: number;
        total_purchases_val: number;
        total_paid_val: number;
        current_outstanding: number;
        overdue_count: number;
        total_transactions_count: number;
        has_active_p2p: boolean;
        p2p_amount: number | null;
        p2p_promised_date: string | null;
        opt_out_contact: boolean;
    };
    invoices: Array<{
        id: string;
        invoice_number: string;
        amount: number;
        outstanding: number;
        status: string;
        due_date: string;
    }>;
}

export interface PayableItem {
    id: string;
    supplier_id: string;
    supplier_name: string;
    bill_number: string;
    total_amount: number;
    outstanding_amount: number;
    due_date: string;
    priority_level: 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW';
    criticality: string;
    early_discount_percent: number;
    late_penalty_percent: number;
    payment_terms: string;
    recommended_action: string;
}

export interface ExpenseItem {
    id: string;
    title: string;
    category: string;
    category_type: string;
    amount: number;
    date: string;
    is_recurring: boolean;
    frequency: string;
    historical_avg: number;
    is_anomaly: boolean;
    anomaly_reason: string | null;
}

export interface ActionItem {
    id: string;
    action_type: string;
    target_type: 'CUSTOMER' | 'SUPPLIER' | 'EXPENSE';
    target_id: string;
    target_name: string;
    amount: number;
    priority_score: number;
    confidence: number;
    status: string;
    requires_approval: boolean;
    approval_reason?: string;
    explanation: string;
    expected_financial_impact?: number;
    policy_reasons?: string[];
}

export interface StrategyOption {
    name: string;
    code: string;
    gross_recovery: number;
    net_recovery: number;
    expected_cash: number;
    minimum_cash: number;
    operational_cost: number;
    action_count: number;
    customer_contact_count: number;
    liquidity_violations: number;
    customer_friction: string;
    roi: number;
    cash_path?: Array<{
        day: number;
        starting_cash: number;
        inflow: number;
        outflow: number;
        ending_cash: number;
        buffer_violation: boolean;
    }>;
}

export interface DemoScenario {
    id: string;
    name: string;
    description: string;
    tag: string;
}

export interface ReportItem {
    id: string;
    title: string;
    summary: string;
    metrics: Record<string, unknown>;
}

export interface SettingsPayload {
    merchant: {
        id: string | null;
        name: string;
        business_type: string;
        currency: string;
        min_cash_buffer: number;
    };
    policy_rules: Record<string, number | boolean>;
    security: Record<string, string>;
}

import {
    DashboardKPIs,
    CashflowSummary,
    ReceivableItem,
    CustomerListItem,
    CustomerProfile,
    PayableItem,
    ExpenseItem,
    ActionItem,
    AIInsights,
    AIOverview,
    StrategyOption,
    DemoScenario,
    ReportItem,
    SettingsPayload
} from '../types';

const API_BASE = '/api';

let authToken = localStorage.getItem('cashpilot_owner_token');

export const setAuthToken = (token: string | null) => {
    authToken = token;
    if (token) localStorage.setItem('cashpilot_owner_token', token);
    else localStorage.removeItem('cashpilot_owner_token');
};

async function fetchJson<T>(url: string, options?: RequestInit): Promise<T> {
    const isFormData = options?.body instanceof FormData;
    const res = await fetch(`${API_BASE}${url}`, {
        headers: {
            ...(isFormData ? {} : { 'Content-Type': 'application/json' }),
            ...(authToken ? { Authorization: `Bearer ${authToken}` } : {}),
            ...options?.headers,
        },
        ...options,
    });
    if (res.status === 401) {
        setAuthToken(null);
        window.dispatchEvent(new Event('cashpilot-auth-expired'));
    }
    if (!res.ok) {
        let detail = res.statusText;
        try {
            const body = await res.json();
            detail = body.detail || detail;
        } catch {
            // Keep the HTTP status text when the response is not JSON.
        }
        throw new Error(`API Error ${res.status}: ${detail}`);
    }
    return res.json();
}

export const api = {
    getAuthStatus: () => fetchJson<{ setup_required: boolean; username: string | null }>('/auth/status'),
    checkUsername: (username: string) => fetchJson<{ username: string; available: boolean; already_exists: boolean; setup_required: boolean }>(`/auth/username-availability?username=${encodeURIComponent(username)}`),
    setupOwner: (payload: { username: string; password: string; business_name: string; current_balance: number }) => fetchJson<{ token: string; username: string }>('/auth/setup', { method: 'POST', body: JSON.stringify(payload) }),
    login: (username: string, password: string) => fetchJson<{ token: string; username: string }>('/auth/login', { method: 'POST', body: JSON.stringify({ username, password }) }),
    logout: () => setAuthToken(null),
    createCustomer: (payload: Record<string, unknown>) => fetchJson<{ id: string; name: string }>('/owner/customers', { method: 'POST', body: JSON.stringify(payload) }),
    createSale: (payload: Record<string, unknown>) => fetchJson<{ id: string; invoice_number: string }>('/owner/sales', { method: 'POST', body: JSON.stringify(payload) }),
    createPurchase: (payload: Record<string, unknown>) => fetchJson<{ id: string; bill_number: string }>('/owner/purchases', { method: 'POST', body: JSON.stringify(payload) }),
    createExpense: (payload: Record<string, unknown>) => fetchJson<{ id: string; title: string }>('/owner/expenses', { method: 'POST', body: JSON.stringify(payload) }),
    recordCustomerPayment: (invoiceId: string, amount: number, paymentMethod = 'Bank_Transfer') => fetchJson<{ status: string; outstanding_amount: number }>(`/owner/invoices/${invoiceId}/payment`, { method: 'POST', body: JSON.stringify({ amount, payment_method: paymentMethod }) }),
    recordSupplierPayment: (payableId: string, amount: number, paymentMethod = 'Bank_Transfer') => fetchJson<{ status: string; outstanding_amount: number }>(`/owner/payables/${payableId}/payment`, { method: 'POST', body: JSON.stringify({ amount, payment_method: paymentMethod }) }),
    updateCustomer: (customerId: string, payload: Record<string, unknown>) => fetchJson<{ status: string }>(`/owner/customers/${customerId}`, { method: 'PUT', body: JSON.stringify(payload) }),
    updateInvoice: (invoiceId: string, payload: Record<string, unknown>) => fetchJson<{ status: string }>(`/owner/invoices/${invoiceId}`, { method: 'PUT', body: JSON.stringify(payload) }),
    updatePayable: (payableId: string, payload: Record<string, unknown>) => fetchJson<{ status: string }>(`/owner/payables/${payableId}`, { method: 'PUT', body: JSON.stringify(payload) }),
    updateExpense: (expenseId: string, payload: Record<string, unknown>) => fetchJson<{ status: string }>(`/owner/expenses/${expenseId}`, { method: 'PUT', body: JSON.stringify(payload) }),
    previewBusinessFile: (file: File) => { const form = new FormData(); form.append('file', file); return fetchJson<{ status: string; filename: string; rows: Array<Record<string, unknown>>; total_rows: number; valid_rows: number; invalid_rows: number }>('/owner/import', { method: 'POST', body: form }); },
    importBusinessFile: (file: File) => { const form = new FormData(); form.append('file', file); return fetchJson<{ status: string; imported: number; skipped: number; buyers: number; sellers: number; sales: number; purchases: number; expenses: number }>('/owner/import?commit=true', { method: 'POST', body: form }); },
    clearBusinessData: () => fetchJson<{ status: string }>('/owner/business-data', { method: 'DELETE' }),
    getKPIs: () => fetchJson<DashboardKPIs>('/dashboard/kpis'),

    getCashflowForecast: (days = 15, buffer?: number) => {
        const params = new URLSearchParams({ days: days.toString() });
        if (buffer !== undefined) params.append('buffer', buffer.toString());
        return fetchJson<CashflowSummary>(`/cashflow/forecast?${params.toString()}`);
    },

    getReceivables: () => fetchJson<{ receivables: ReceivableItem[] }>('/receivables'),

    getCustomers: () => fetchJson<{ customers: CustomerListItem[] }>('/customers'),

    getCustomerProfile: (customerId: string) => fetchJson<CustomerProfile>(`/customers/${customerId}`),

    getPayables: () => fetchJson<{ payables: PayableItem[] }>('/payables'),

    getExpenses: () => fetchJson<{ expenses: ExpenseItem[]; monthly_breakdown: Record<string, number> }>('/expenses'),

    getLedger: () => fetchJson<{
        balance_sheet: {
            assets: Record<string, number>;
            liabilities: Record<string, number>;
            equity: Record<string, number>;
            total_assets: number;
            total_liabilities: number;
            total_equity: number;
            total_revenue: number;
            total_expenses: number;
            revenue: Record<string, number>;
            expenses: Record<string, number>;
            is_balanced: boolean;
        };
        ledger_entries: Array<{
            id: string;
            date: string;
            transaction: string;
            debit_account: string;
            credit_account: string;
            debit: number;
            credit: number;
            source: string;
            status: string;
            created_by: string;
        }>;
        audit_trail: Array<{
            id: string;
            timestamp: string;
            actor: string;
            action: string;
            details: string;
        }>;
    }>('/ledger'),

    getTodayActions: (buffer?: number) => {
        const params = buffer ? `?buffer=${buffer}` : '';
        return fetchJson<{
            liquidity_status: string;
            current_cash: number;
            min_cash_buffer: number;
            min_projected_cash: number;
            total_receivables: number;
            expected_recovery: number;
            total_actions: number;
            action_items: ActionItem[];
        }>(`/actions/today${params}`);
    },

    approveAction: (actionId: string) => fetchJson<{ status: string; action_id: string }>(`/actions/approve/${actionId}`, {
        method: 'POST'
    }),

    executeAction: (actionId: string) => fetchJson<{ status: string; action_id: string; action_status: string; payment_link?: any }>(`/actions/execute/${actionId}`, {
        method: 'POST'
    }),

    rejectAction: (actionId: string) => fetchJson<{ status: string; action_id: string }>(`/actions/reject/${actionId}`, {
        method: 'POST',
        body: JSON.stringify({ notes: 'Rejected in CashPilot approval center' })
    }),

    getAIInsights: () => fetchJson<{
        liquidity_status: string;
        financial_health_score: number;
        top_actions: ActionItem[];
        recommended_focus: string[];
        smart_summary: string;
    }>('/ai/insights'),

    getAIOverview: () => fetchJson<AIOverview>('/ai/overview'),
    analyzeInvoice: (payload: Record<string, unknown>) => fetchJson<{ fields: Record<string, unknown>; confidence: number; duplicate_risk: string; warnings: string[]; recommended_action: string }>('/ai/invoice/analyze', { method: 'POST', body: JSON.stringify(payload) }),
    getAICompliance: () => fetchJson<{ gst_readiness: number; checks: Array<{ name: string; status: string; count: number }>; missing_due_dates: string[]; missing_customer_data: string[] }>('/ai/compliance'),
    runAIScenario: (payload: { collection_rate: number; sales_change_percent: number; expense_change_percent: number }) => fetchJson<{ current_cash: number; expected_recovery: number; projected_cash: number; buffer_gap: number; recommendation: string }>('/ai/scenario', { method: 'POST', body: JSON.stringify(payload) }),
    resolveVoiceIntent: (text: string) => fetchJson<{ intent: string; transcript: string; requires_confirmation: boolean; next_step: string }>('/ai/voice/intent', { method: 'POST', body: JSON.stringify({ text }) }),
    recordAIFeedback: (actionId: string, outcome: string, notes = '') => fetchJson<{ status: string }>('/ai/feedback', { method: 'POST', body: JSON.stringify({ action_id: actionId, outcome, notes }) }),

    runSimulation: (buffer = 200000) => fetchJson<{
        custom_buffer: number;
        strategies: StrategyOption[];
    }>('/simulator/run', {
        method: 'POST',
        body: JSON.stringify({ min_buffer: buffer })
    }),

    getBenchmark: () => fetchJson<{
        ml_model_metrics: any;
        decision_benchmark: any;
    }>('/evaluation/benchmark'),

    queryCopilot: (question: string) => fetchJson<{
        question: string;
        answer: string;
        type: string;
        data?: any;
    }>('/copilot/chat', {
        method: 'POST',
        body: JSON.stringify({ question })
    }),

    getDemoScenarios: () => fetchJson<{ scenarios: DemoScenario[] }>('/scenarios/list'),

    applyDemoScenario: (scenarioId: string) => fetchJson<{
        status: string;
        active_scenario_id: string;
        current_cash: number;
        min_buffer: number;
    }>(`/scenarios/apply/${scenarioId}`, {
        method: 'POST'
    }),

    createPaymentLink: (invoiceId: string, customerName: string, amount: number, dueDate: string) => fetchJson<{
        payment_link_id: string;
        short_url: string;
        invoice_id: string;
        customer_name: string;
        amount: number;
    }>('/razorpay/payment-link', {
        method: 'POST',
        body: JSON.stringify({ invoice_id: invoiceId, customer_name: customerName, amount, due_date: dueDate })
    }),

    getReports: () => fetchJson<{ reports: ReportItem[] }>('/reports'),

    getSettings: () => fetchJson<SettingsPayload>('/settings'),

    updateSettings: (minCashBuffer: number) => fetchJson<SettingsPayload>('/settings', {
        method: 'POST',
        body: JSON.stringify({ min_cash_buffer: minCashBuffer })
    }),

    extractDocument: (payload: {
        description: string;
        amount?: number;
        vendor?: string;
        invoice_number?: string;
        date?: string;
        tax?: number;
    }) => fetchJson<{
        vendor?: string;
        invoice_number?: string;
        date?: string;
        amount: number;
        tax: number;
        category: string;
        category_type: string;
        confidence: string;
        review_required: boolean;
        message: string;
    }>('/documents/structured-extract', {
        method: 'POST',
        body: JSON.stringify(payload)
    }),

    extractPromiseToPay: (message: string) => fetchJson<{
        has_promise: boolean;
        opt_out: boolean;
        already_paid: boolean;
        amount: number;
        promised_date: string | null;
        confidence: number;
        recommendation: string;
    }>('/promise-to-pay/extract', {
        method: 'POST',
        body: JSON.stringify({ message })
    })
};

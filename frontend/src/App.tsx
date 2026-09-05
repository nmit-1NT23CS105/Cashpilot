import React, { useEffect, useState } from 'react';
import { Navbar } from './components/Navbar';
import { DashboardOverview } from './components/DashboardOverview';
import { CashflowForecastView } from './components/CashflowForecastView';
import { ReceivablesView } from './components/ReceivablesView';
import { CustomersView } from './components/CustomersView';
import { PayablesView } from './components/PayablesView';
import { ExpensesView } from './components/ExpensesView';
import { LedgerView } from './components/LedgerView';
import { ActionsView } from './components/ActionsView';
import { SimulatorView } from './components/SimulatorView';
import { ReportsView } from './components/ReportsView';
import { CopilotPage } from './components/CopilotPage';
import { BenchmarkView } from './components/BenchmarkView';
import { SettingsView } from './components/SettingsView';
import { CustomerDrawer } from './components/CustomerDrawer';
import { LoginView } from './components/LoginView';
import { OwnerWorkspace } from './components/OwnerWorkspace';
import { AIWorkspace } from './components/AIWorkspace';
import { RouteErrorBoundary } from './components/RouteErrorBoundary';
import { StatusScreen } from './components/StatusScreen';
import {
    DashboardKPIs,
    CashflowSummary,
    ReceivableItem,
    CustomerListItem,
    PayableItem,
    ExpenseItem,
    ActionItem,
} from './types';
import { api, setAuthToken } from './services/api';

export function App() {
    const [activeTab, setActiveTab] = useState<string>('overview');

    const [kpis, setKpis] = useState<DashboardKPIs | null>(null);
    const [forecast, setForecast] = useState<CashflowSummary | null>(null);
    const [receivables, setReceivables] = useState<ReceivableItem[]>([]);
    const [customers, setCustomers] = useState<CustomerListItem[]>([]);
    const [payables, setPayables] = useState<PayableItem[]>([]);
    const [expenses, setExpenses] = useState<ExpenseItem[]>([]);
    const [monthlyBreakdown, setMonthlyBreakdown] = useState<Record<string, number>>({});
    const [actions, setActions] = useState<ActionItem[]>([]);

    const [selectedCustomerId, setSelectedCustomerId] = useState<string | null>(null);
    const [loading, setLoading] = useState<boolean>(true);
    const [authReady, setAuthReady] = useState<boolean>(false);
    const [ownerName, setOwnerName] = useState<string>('');
    const [setupRequired, setSetupRequired] = useState<boolean>(false);
    const [loadError, setLoadError] = useState('');
    const [actionError, setActionError] = useState('');

    const loadAllData = async () => {
        setLoading(true);
        setLoadError('');
        try {
            const [kpiRes, cfRes, recRes, custRes, payRes, expRes, actRes] = await Promise.all([
                api.getKPIs(),
                api.getCashflowForecast(15),
                api.getReceivables(),
                api.getCustomers(),
                api.getPayables(),
                api.getExpenses(),
                api.getTodayActions()
            ]);

            setKpis(kpiRes);
            setForecast(cfRes);
            setReceivables(recRes.receivables);
            setCustomers(custRes.customers);
            setPayables(payRes.payables);
            setExpenses(expRes.expenses);
            setMonthlyBreakdown(expRes.monthly_breakdown);
            setActions(actRes.action_items);
        } catch (err) {
            console.error('Failed to load application data:', err);
            setLoadError(err instanceof Error ? err.message.replace(/^API Error \d+:\s*/, '') : 'We could not load your business data.');
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        const expireSession = () => window.location.reload();
        window.addEventListener('cashpilot-auth-expired', expireSession);
        api.getAuthStatus().then((status) => {
            setSetupRequired(status.setup_required);
            const token = localStorage.getItem('cashpilot_owner_token');
            if (status.setup_required) {
                setAuthToken(null);
                setLoading(false);
            } else if (token) {
                setOwnerName(status.username || 'Owner');
                loadAllData();
            } else {
                setLoading(false);
            }
            setAuthReady(true);
        }).catch((err) => {
            setLoadError(err instanceof Error ? err.message : 'We could not connect to CashPilot.');
            setLoading(false);
        });
        return () => window.removeEventListener('cashpilot-auth-expired', expireSession);
    }, []);

    const handleAuthenticated = (username: string) => {
        setOwnerName(username);
        loadAllData();
    };

    const handleLogout = () => {
        setAuthToken(null);
        setOwnerName('');
        setActiveTab('overview');
    };

    const hasBusinessData = Boolean(
        customers.length || receivables.length || payables.length || expenses.length || actions.length ||
        (kpis && (kpis.current_cash > 0 || kpis.total_receivables > 0 || kpis.total_payables > 0))
    );

    const handleApproveAction = async (actionId: string) => {
        setActionError('');
        try {
            await api.approveAction(actionId);
            const updatedActions = await api.getTodayActions();
            setActions(updatedActions.action_items);
        } catch (err) {
            console.error('Failed to approve action:', err);
            setActionError(err instanceof Error ? err.message.replace(/^API Error \d+:\s*/, '') : 'We could not approve this suggestion.');
        }
    };

    const handleExecuteAction = async (actionId: string) => {
        setActionError('');
        try {
            await api.executeAction(actionId);
            const updatedActions = await api.getTodayActions();
            setActions(updatedActions.action_items);
        } catch (err) {
            console.error('Failed to execute action:', err);
            setActionError(err instanceof Error ? err.message.replace(/^API Error \d+:\s*/, '') : 'We could not complete this action.');
        }
    };

    const handleRejectAction = async (actionId: string) => {
        setActionError('');
        try {
            await api.rejectAction(actionId);
            const updatedActions = await api.getTodayActions();
            setActions(updatedActions.action_items);
        } catch (err) {
            console.error('Failed to reject action:', err);
            setActionError(err instanceof Error ? err.message.replace(/^API Error \d+:\s*/, '') : 'We could not dismiss this suggestion.');
        }
    };

    if (!authReady) {
        return <div className="min-h-screen bg-[#f4f1ed] flex items-center justify-center text-sm">Loading your business page...</div>;
    }

    if (!localStorage.getItem('cashpilot_owner_token')) {
        return <LoginView setupRequired={setupRequired} onAuthenticated={handleAuthenticated} />;
    }

    if (loading || !kpis) {
        if (loadError) {
            return (
                <StatusScreen
                    title="Your business data did not load"
                    message={`${loadError} Please check that the server is running, then try again.`}
                    onAction={loadAllData}
                    busy={loading}
                    tone="error"
                />
            );
        }
        return (
            <div className="min-h-screen bg-[#f9f9f9] flex flex-col items-center justify-center space-y-4">
                <div className="w-14 h-14 rounded-2xl bg-black p-[2px] animate-pulse flex items-center justify-center">
                    <span className="text-white font-extrabold text-xl" style={{ fontFamily: 'Manrope, Inter, system-ui, sans-serif' }}>CP</span>
                </div>
                <div className="text-[#5d5f5f] text-sm" style={{ fontFamily: 'Inter, system-ui, sans-serif' }}>Opening your business page...</div>
            </div>
        );
    }

    if (!hasBusinessData) {
        return (
            <div className="min-h-screen bg-[#f9f9f9] text-[#1b1b1b]" style={{ fontFamily: 'Inter, system-ui, sans-serif' }}>
                <Navbar
                    activeTab={activeTab}
                    setActiveTab={setActiveTab}
                    onOpenOwner={() => setActiveTab('owner')}
                    ownerName={ownerName}
                />
                <main className="max-w-6xl mx-auto px-4 py-8">
                    <StatusScreen
                        title="No business data yet"
                        message="Add your first buyer, create a sale, or import your business file to start tracking money, cash flow, and AI help."
                        actionLabel="Go to owner workspace"
                        onAction={() => setActiveTab('owner')}
                        tone="info"
                    />

                    <div className="mt-6 grid gap-4 md:grid-cols-3">
                        <div className="rounded-2xl border border-[#d9d2ca] bg-white p-5 shadow-sm">
                            <div className="text-sm font-bold text-[#1b1b1b]">Create a buyer</div>
                            <p className="mt-2 text-sm text-[#5d5f5f]">Add a customer name and payment details to start tracking who owes you money.</p>
                        </div>
                        <div className="rounded-2xl border border-[#d9d2ca] bg-white p-5 shadow-sm">
                            <div className="text-sm font-bold text-[#1b1b1b]">Create a sale</div>
                            <p className="mt-2 text-sm text-[#5d5f5f]">Record the sale amount and due date so the AI can forecast your cash.</p>
                        </div>
                        <div className="rounded-2xl border border-[#d9d2ca] bg-white p-5 shadow-sm">
                            <div className="text-sm font-bold text-[#1b1b1b]">Import a file</div>
                            <p className="mt-2 text-sm text-[#5d5f5f]">Upload CSV or Excel files to bulk add customers, sales, and payment records.</p>
                        </div>
                    </div>
                </main>
            </div>
        );
    }

    return (
        <div className="min-h-screen bg-[#f9f9f9] text-[#1b1b1b] overflow-x-hidden" style={{ fontFamily: 'Inter, system-ui, sans-serif' }}>
            {/* Top Navbar Header */}
            <Navbar
                activeTab={activeTab}
                setActiveTab={setActiveTab}
                onOpenOwner={() => setActiveTab('owner')}
                ownerName={ownerName}
            />

            {/* Main Content Area */}
            <main className="max-w-7xl mx-auto w-full px-4 sm:px-5 md:px-20 py-6">
                {loadError && (
                    <div role="alert" className="mb-4 flex flex-wrap items-center justify-between gap-3 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800">
                        <span>{loadError}</span>
                        <button type="button" onClick={loadAllData} className="rounded-lg bg-black px-3 py-2 text-xs font-bold text-white">Reload data</button>
                    </div>
                )}
                {actionError && (
                    <div role="alert" className="mb-4 flex flex-wrap items-center justify-between gap-3 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800">
                        <span>{actionError}</span>
                        <button type="button" onClick={() => setActionError('')} className="rounded-lg border border-red-300 px-3 py-2 text-xs font-bold">Close</button>
                    </div>
                )}
                {activeTab === 'overview' && (
                    <DashboardOverview
                        kpis={kpis}
                        actions={actions}
                        onApproveAction={handleApproveAction}
                        onSelectCustomer={(id) => setSelectedCustomerId(id)}
                        onOpenActions={() => setActiveTab('actions')}
                    />
                )}

                {activeTab === 'cashflow' && (
                    <CashflowForecastView
                        initialSummary={forecast}
                        onBufferChange={async (buf) => {
                            const updatedActions = await api.getTodayActions(buf);
                            setActions(updatedActions.action_items);
                        }}
                    />
                )}

                {activeTab === 'receivables' && (
                    <ReceivablesView
                        receivables={receivables}
                        onSelectCustomer={(id) => setSelectedCustomerId(id)}
                        onChanged={loadAllData}
                        />
                )}

                {activeTab === 'customers' && (
                    <CustomersView
                        customers={customers}
                        onSelectCustomer={(id) => setSelectedCustomerId(id)}
                        onChanged={loadAllData}
                        />
                )}

                {activeTab === 'payables' && (
                    <PayablesView payables={payables} onChanged={loadAllData} />
                )}

                {activeTab === 'expenses' && (
                    <ExpensesView
                        expenses={expenses}
                        monthlyBreakdown={monthlyBreakdown}
                            onChanged={loadAllData}
                    />
                )}

                {activeTab === 'ledger' && <LedgerView />}

                {activeTab === 'actions' && (
                    <ActionsView
                        actions={actions}
                        onApproveAction={handleApproveAction}
                        onExecuteAction={handleExecuteAction}
                        onRejectAction={handleRejectAction}
                    />
                )}

                {activeTab === 'simulator' && <SimulatorView />}

                {activeTab === 'reports' && <ReportsView />}

                {activeTab === 'ai' && <RouteErrorBoundary><AIWorkspace /></RouteErrorBoundary>}
                {activeTab === 'copilot' && <RouteErrorBoundary><AIWorkspace /></RouteErrorBoundary>}


                {activeTab === 'benchmark' && <BenchmarkView />}

                {activeTab === 'settings' && <SettingsView onSettingsSaved={loadAllData} />}
                {activeTab === 'owner' && <OwnerWorkspace customers={customers} onSaved={loadAllData} onLogout={handleLogout} username={ownerName} />}
            </main>

            <CustomerDrawer
                customerId={selectedCustomerId}
                onClose={() => setSelectedCustomerId(null)}
            />
        </div>
    );
}
export default App;

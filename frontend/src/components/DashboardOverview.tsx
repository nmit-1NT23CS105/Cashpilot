import React from 'react';
import {
    AlertTriangle,
    ArrowRight,
    BadgeCheck,
    Eye,
    EyeOff,
    Factory,
    ReceiptText,
    Send,
    ShieldCheck,
    Sparkles,
    TrendingUp,
    UserRoundCheck,
    Wallet,
} from 'lucide-react';
import { ActionItem, DashboardKPIs } from '../types';

interface DashboardOverviewProps {
    kpis: DashboardKPIs;
    actions: ActionItem[];
    onApproveAction: (actionId: string) => void;
    onSelectCustomer: (customerId: string) => void;
    onOpenActions: () => void;
}

const headingFont = 'Manrope, Inter, system-ui, sans-serif';
const monoFont = 'JetBrains Mono, ui-monospace, SFMono-Regular, Menlo, monospace';
const money = (value: number) => `₹${value.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;

const ActionGlyph: React.FC<{ type: string }> = ({ type }) => {
    if (type === 'SEND_PAYMENT_LINK') return <Send size={18} />;
    if (type === 'HUMAN_ESCALATION') return <ShieldCheck size={18} />;
    if (type === 'PRIORITIZE_SUPPLIER') return <Factory size={18} />;
    if (type === 'REVIEW_EXPENSE') return <ReceiptText size={18} />;
    return <UserRoundCheck size={18} />;
};

export const DashboardOverview: React.FC<DashboardOverviewProps> = ({
    kpis,
    actions,
    onApproveAction,
    onSelectCustomer,
    onOpenActions,
}) => {
    const [showFinancials, setShowFinancials] = React.useState(false);
    const pendingApprovals = actions.filter((action) => action.requires_approval && action.status !== 'APPROVED' && action.status !== 'REJECTED');

    return (
        <div className="space-y-6">
            <div className="flex flex-col md:flex-row md:justify-between md:items-end gap-4">
                <div>
                    <h1 className="text-[28px] md:text-[32px] font-bold tracking-tight text-black" style={{ fontFamily: headingFont }}>
                        Business home
                    </h1>
                </div>
                <button
                    type="button"
                    onClick={() => setShowFinancials((visible) => !visible)}
                    title={showFinancials ? 'Hide financial amounts' : 'Show financial amounts'}
                    aria-label={showFinancials ? 'Hide financial amounts' : 'Show financial amounts'}
                    className="self-start md:self-auto inline-flex items-center gap-2 border border-[#cfc4c5] bg-white/80 text-[#1b1b1b] rounded-lg px-3 py-2 text-xs font-bold hover:bg-white"
                >
                    {showFinancials ? <EyeOff size={16} /> : <Eye size={16} />}
                    {showFinancials ? 'Hide money' : 'Show money'}
                </button>
            </div>

            <div className="grid grid-cols-2 md:grid-cols-3 gap-3 md:gap-5">
                <div className="glass-panel p-5 rounded-xl flex flex-col justify-between h-[140px]">
                    <div className="flex justify-between items-start">
                        <span className="text-[13px] font-medium text-[#5d5f5f] uppercase tracking-wider">Cash in hand</span>
                        <Wallet size={19} className="text-[#5d5f5f]" />
                    </div>
                    <div>
                        <div className="text-[28px] md:text-[32px] font-bold text-black tracking-tight" style={{ fontFamily: headingFont }}>
                            {showFinancials ? money(kpis.current_cash) : '••••••••'}
                        </div>
                        <div className="text-[13px] text-emerald-600 mt-1 flex items-center gap-1">
                            <TrendingUp size={14} /> Ready to use
                        </div>
                    </div>
                </div>

                <div className="glass-panel p-5 rounded-xl flex flex-col justify-between h-[140px]">
                    <div className="flex justify-between items-start">
                        <span className="text-[13px] font-medium text-[#5d5f5f] uppercase tracking-wider">Money coming in</span>
                        <TrendingUp size={19} className="text-[#5d5f5f]" />
                    </div>
                    <div>
                        <div className="text-[28px] md:text-[32px] font-bold text-black tracking-tight" style={{ fontFamily: headingFont }}>
                            {showFinancials ? money(kpis.expected_recovery_7d) : '••••••••'}
                        </div>
                        <div className="text-[13px] text-[#5d5f5f] mt-1">7-day estimate</div>
                    </div>
                </div>

                <div className="glass-panel p-5 rounded-xl flex flex-col justify-between h-[140px]">
                    <div className="flex justify-between items-start">
                        <span className="text-[13px] font-medium text-[#5d5f5f] uppercase tracking-wider">Bills to pay</span>
                        <ReceiptText size={19} className="text-[#5d5f5f]" />
                    </div>
                    <div>
                        <div className="text-[28px] md:text-[32px] font-bold text-black tracking-tight" style={{ fontFamily: headingFont }}>
                            {showFinancials ? money(kpis.total_payables) : '••••••••'}
                        </div>
                        <div className="text-[13px] text-amber-600 mt-1 flex items-center gap-1">
                            <AlertTriangle size={14} /> Due soon
                        </div>
                    </div>
                </div>

            </div>

            <div className="grid grid-cols-1 md:grid-cols-12 gap-5">
                <div className="md:col-span-8 glass-panel p-6 rounded-xl">
                    <div className="flex flex-col sm:flex-row sm:justify-between sm:items-center gap-3 mb-5">
                        <h2 className="text-[20px] font-semibold text-black flex items-center gap-2" style={{ fontFamily: headingFont }}>
                            <Sparkles size={19} /> What to do next
                        </h2>
                        <div className="flex gap-2">
                            <span className="text-[13px] font-medium text-[#5d5f5f] glass-panel px-3 py-1 rounded-full">
                                Total: <span className="font-bold text-black">{actions.length}</span>
                            </span>
                            {pendingApprovals.length > 0 && (
                                <span className="text-[13px] font-medium text-amber-700 bg-amber-50 border border-amber-200 px-3 py-1 rounded-full">
                                    Waiting: <span className="font-bold">{pendingApprovals.length}</span>
                                </span>
                            )}
                        </div>
                    </div>

                    <div className="space-y-3">
                        {actions.map((action) => {
                            const isApproved = action.status === 'APPROVED';
                            return (
                                <div
                                    key={action.id}
                                    className={`p-4 border rounded-xl transition-all group ${action.status === 'PAUSED_FOR_LIQUIDITY'
                                            ? 'bg-amber-50/50 border-amber-200'
                                            : action.requires_approval && !isApproved
                                                ? 'bg-white border-black/10 shadow-sm'
                                                : 'bg-white/50 border-[#cfc4c5]/30 hover:bg-white'
                                        }`}
                                >
                                    <div className="flex flex-col lg:flex-row items-start lg:items-center justify-between gap-4">
                                        <div className="flex items-start gap-3 min-w-0">
                                            <div className={`w-10 h-10 rounded-xl flex items-center justify-center shrink-0 ${action.action_type === 'SEND_PAYMENT_LINK' ? 'bg-black/5' :
                                                    action.action_type === 'HUMAN_ESCALATION' ? 'bg-amber-50' :
                                                        action.action_type === 'PRIORITIZE_SUPPLIER' ? 'bg-emerald-50' : 'bg-[#e8e8e8]'
                                                }`}>
                                                <ActionGlyph type={action.action_type} />
                                            </div>
                                            <div className="min-w-0">
                                                <div className="flex items-center gap-2 flex-wrap">
                                                    <span className="font-semibold text-black text-sm">{action.target_name}</span>
                                                    <span className="text-[12px] text-[#5d5f5f]">({action.target_type === 'CUSTOMER' ? 'buyer' : action.target_type === 'SUPPLIER' ? 'supplier' : action.target_type})</span>
                                                    <span className="text-[13px] font-bold text-black" style={{ fontFamily: monoFont }}>
                                                        {money(action.amount)}
                                                    </span>
                                                    <span className={`text-[10px] uppercase font-bold px-2 py-0.5 rounded-full ${action.status === 'PAUSED_FOR_LIQUIDITY' ? 'bg-amber-100 text-amber-700 border border-amber-200' :
                                                            isApproved ? 'bg-emerald-50 text-emerald-700 border border-emerald-200' :
                                                                action.requires_approval ? 'bg-black text-white' : 'bg-[#e8e8e8] text-[#5d5f5f]'
                                                        }`}>
                                                        {action.status.replace(/_/g, ' ').toLowerCase() === 'recommended' ? 'good to do' : action.status.replace(/_/g, ' ')}
                                                    </span>
                                                </div>
                                                <p className="text-[13px] text-[#5d5f5f] mt-1 leading-relaxed">
                                                    {action.explanation}
                                                </p>
                                            </div>
                                        </div>

                                        <div className="flex items-center gap-3 shrink-0 self-end lg:self-center">
                                            <div className="text-right hidden sm:block">
                                                <div className="text-[10px] text-[#5d5f5f] uppercase tracking-wider">Priority</div>
                                                <div className="text-sm font-bold text-black" style={{ fontFamily: monoFont }}>{action.priority_score}</div>
                                            </div>

                                            {action.target_type === 'CUSTOMER' && (
                                                <button
                                                    onClick={() => onSelectCustomer(action.target_id)}
                                                    className="glass-panel text-[13px] font-medium text-black px-3 py-1.5 rounded-lg hover:bg-white/90 transition-all cursor-pointer"
                                                >
                                                    Open buyer
                                                </button>
                                            )}

                                            {action.requires_approval && !isApproved ? (
                                                <button
                                                    onClick={() => onApproveAction(action.id)}
                                                    className="bg-black text-white font-bold text-[13px] px-4 py-1.5 rounded-lg transition-all shadow-md cursor-pointer hover:opacity-90 active:scale-95"
                                                >
                                                    Approve
                                                </button>
                                            ) : action.action_type === 'SEND_PAYMENT_LINK' ? (
                                                <span className="glass-panel text-[13px] font-medium text-black px-3 py-1.5 rounded-lg flex items-center gap-1.5">
                                                    <BadgeCheck size={14} /> Ready
                                                </span>
                                            ) : null}
                                        </div>
                                    </div>
                                </div>
                            );
                        })}
                    </div>
                </div>

                <div className="md:col-span-4 flex flex-col gap-5">
                    <div className="glass-panel p-6 rounded-xl border-l-4 border-l-black relative overflow-hidden flex-1">
                        <div className="absolute -right-4 -top-4 opacity-5">
                            <ShieldCheck size={118} />
                        </div>
                        <h3 className="text-[13px] text-black uppercase tracking-wider font-medium flex items-center gap-1 mb-1">
                            <ShieldCheck size={15} /> Waiting for your approval
                        </h3>
                        <div className="text-[28px] font-bold text-black mt-3 mb-1" style={{ fontFamily: headingFont }}>
                            {pendingApprovals.length} items
                        </div>
                        <p className="text-[14px] text-[#5d5f5f]">Some bigger actions need your final yes or no.</p>
                        <button onClick={onOpenActions} className="mt-5 w-full glass-panel border border-black/10 py-2.5 rounded-full text-[13px] text-black font-bold hover:bg-white transition-colors flex justify-center items-center gap-1">
                            Check next steps <ArrowRight size={15} />
                        </button>
                    </div>

                    <div className="glass-panel p-5 rounded-xl">
                        <div className="flex justify-between items-start mb-3">
                            <span className="text-[13px] font-medium text-[#5d5f5f] uppercase tracking-wider">Money at risk</span>
                            <AlertTriangle size={18} className="text-[#ba1a1a]" />
                        </div>
                        <div className="text-[24px] font-bold text-[#ba1a1a]" style={{ fontFamily: headingFont }}>
                            {money(kpis.revenue_at_risk)}
                        </div>
                        <div className="text-[13px] text-[#5d5f5f] mt-1">
                            <span className="text-[#ba1a1a] font-medium">This needs attention soon</span>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
};

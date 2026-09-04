import React, { useMemo } from 'react';
import { CheckCircle2, CircleDollarSign, Clock3, ShieldAlert, XCircle } from 'lucide-react';
import { ActionItem } from '../types';

const headingFont = 'Manrope, Inter, system-ui, sans-serif';

interface ActionsViewProps {
    actions: ActionItem[];
    onApproveAction: (actionId: string) => void;
    onExecuteAction: (actionId: string) => void;
    onRejectAction: (actionId: string) => void;
}

const money = (value: number) => `${value < 0 ? '-' : ''}₹${Math.abs(value).toLocaleString()}`;

export const ActionsView: React.FC<ActionsViewProps> = ({ actions, onApproveAction, onExecuteAction, onRejectAction }) => {
    const pending = actions.filter((action) => action.requires_approval && action.status !== 'APPROVED' && action.status !== 'REJECTED');
    const approved = actions.filter((action) => action.status === 'APPROVED').length;
    const expectedImpact = actions.reduce((sum, action) => sum + (action.expected_financial_impact || 0), 0);

    const grouped = useMemo(() => ({
        customer: actions.filter((action) => action.target_type === 'CUSTOMER'),
        supplier: actions.filter((action) => action.target_type === 'SUPPLIER'),
        expense: actions.filter((action) => action.target_type === 'EXPENSE'),
    }), [actions]);

    const actionTone = (action: ActionItem) => {
        if (action.status === 'APPROVED') return 'bg-emerald-50 text-emerald-700 border-emerald-200';
        if (action.status === 'REJECTED') return 'bg-red-50 text-[#ba1a1a] border-red-200';
        if (action.requires_approval) return 'bg-amber-50 text-amber-700 border-amber-200';
        return 'bg-white text-black border-[#cfc4c5]/40';
    };

    return (
        <div className="space-y-6">
            <div className="glass-panel rounded-2xl p-6">
                <div className="flex flex-col lg:flex-row lg:items-end justify-between gap-5">
                    <div>
                        <h1 className="text-[24px] md:text-[30px] font-bold tracking-tight text-black" style={{ fontFamily: headingFont }}>
                            Today&apos;s AI Action Plan
                        </h1>
                        <p className="text-[13px] text-[#5d5f5f] mt-1 max-w-3xl">
                            Deterministic recommendations ranked by expected recovery, liquidity impact, policy limits, and customer behavior.
                        </p>
                    </div>
                    <div className="grid grid-cols-3 gap-3">
                        <div className="bg-white/70 border border-[#cfc4c5]/40 rounded-xl p-3 min-w-[140px]">
                            <div className="text-[10px] uppercase tracking-wider text-[#5d5f5f]">Pending Approval</div>
                            <div className="text-xl font-bold text-black">{pending.length}</div>
                        </div>
                        <div className="bg-white/70 border border-[#cfc4c5]/40 rounded-xl p-3 min-w-[140px]">
                            <div className="text-[10px] uppercase tracking-wider text-[#5d5f5f]">Approved</div>
                            <div className="text-xl font-bold text-black">{approved}</div>
                        </div>
                        <div className="bg-white/70 border border-[#cfc4c5]/40 rounded-xl p-3 min-w-[160px]">
                            <div className="text-[10px] uppercase tracking-wider text-[#5d5f5f]">Net Impact</div>
                            <div className="text-xl font-bold text-black">{money(expectedImpact)}</div>
                        </div>
                    </div>
                </div>
            </div>

            <div className="grid grid-cols-1 xl:grid-cols-3 gap-5">
                {[
                    ['Customer Collections', grouped.customer, CircleDollarSign],
                    ['Supplier Payments', grouped.supplier, Clock3],
                    ['Expense Reviews', grouped.expense, ShieldAlert],
                ].map(([title, items, Icon]) => (
                    <section key={title as string} className="glass-panel rounded-2xl p-5 space-y-4">
                        <div className="flex items-center justify-between">
                            <h2 className="text-sm font-bold text-black flex items-center gap-2">
                                {React.createElement(Icon as typeof CircleDollarSign, { size: 18 })}
                                {title as string}
                            </h2>
                            <span className="text-[11px] font-bold text-[#5d5f5f]">{(items as ActionItem[]).length} items</span>
                        </div>

                        <div className="space-y-3">
                            {(items as ActionItem[]).map((action) => (
                                <article key={action.id} className={`rounded-xl border p-4 ${actionTone(action)}`}>
                                    <div className="flex items-start justify-between gap-3">
                                        <div>
                                            <div className="font-bold text-sm text-black">{action.target_name}</div>
                                            <div className="text-[11px] text-[#5d5f5f] mt-0.5">{action.action_type.replace(/_/g, ' ')}</div>
                                        </div>
                                        <div className="text-right">
                                            <div className="font-bold font-mono text-sm">{money(action.amount)}</div>
                                            <div className="text-[10px] text-[#5d5f5f]">Priority {action.priority_score}</div>
                                        </div>
                                    </div>
                                    <p className="text-[12px] text-[#5d5f5f] leading-relaxed mt-3">{action.explanation}</p>
                                    <div className="mt-3 flex flex-wrap gap-2 text-[10px] font-bold">
                                        <span className="px-2 py-1 rounded-full bg-white/70 border border-[#cfc4c5]/40">
                                            Confidence {Math.round(action.confidence * 100)}%
                                        </span>
                                        <span className="px-2 py-1 rounded-full bg-white/70 border border-[#cfc4c5]/40">
                                            Impact {money(action.expected_financial_impact || 0)}
                                        </span>
                                        <span className="px-2 py-1 rounded-full bg-white/70 border border-[#cfc4c5]/40">
                                            {action.status.replace(/_/g, ' ')}
                                        </span>
                                    </div>
                                    {action.approval_reason && (
                                        <div className="mt-3 text-[11px] text-amber-700 bg-amber-100/60 border border-amber-200 rounded-lg p-2">
                                            {action.approval_reason}
                                        </div>
                                    )}
                                    {action.status === 'APPROVED' && action.action_type === 'SEND_PAYMENT_LINK' && (
                                        <div className="mt-3 grid grid-cols-1 gap-2">
                                            <button
                                                onClick={() => onExecuteAction(action.id)}
                                                className="inline-flex items-center justify-center gap-1.5 bg-emerald-600 text-white rounded-lg px-3 py-2 text-[12px] font-bold"
                                            >
                                                <CheckCircle2 size={14} /> Execute payment link
                                            </button>
                                        </div>
                                    )}
                                    {action.requires_approval && action.status !== 'APPROVED' && action.status !== 'REJECTED' && (
                                        <div className="mt-3 grid grid-cols-2 gap-2">
                                            <button
                                                onClick={() => onApproveAction(action.id)}
                                                className="inline-flex items-center justify-center gap-1.5 bg-black text-white rounded-lg px-3 py-2 text-[12px] font-bold"
                                            >
                                                <CheckCircle2 size={14} /> Approve
                                            </button>
                                            <button
                                                onClick={() => onRejectAction(action.id)}
                                                className="inline-flex items-center justify-center gap-1.5 bg-white text-[#ba1a1a] border border-red-200 rounded-lg px-3 py-2 text-[12px] font-bold"
                                            >
                                                <XCircle size={14} /> Reject
                                            </button>
                                        </div>
                                    )}
                                </article>
                            ))}
                        </div>
                    </section>
                ))}
            </div>
        </div>
    );
};

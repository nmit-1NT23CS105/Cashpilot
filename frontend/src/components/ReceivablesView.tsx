import React, { useState } from 'react';
import { ReceivableItem } from '../types';
import { api } from '../services/api';
import { BusinessActionModal } from './BusinessActionModal';

interface ReceivablesViewProps {
    receivables: ReceivableItem[];
    onSelectCustomer: (customerId: string) => void;
    onChanged?: () => Promise<void>;
}

export const ReceivablesView: React.FC<ReceivablesViewProps> = ({
    receivables,
    onSelectCustomer, onChanged
}) => {
    const [filterSegment, setFilterSegment] = useState<string>('ALL');
    const [generatedLinks, setGeneratedLinks] = useState<Record<string, string>>({});
    const [modal, setModal] = useState<{ type: 'payment' | 'edit-invoice'; invoice: ReceivableItem } | null>(null);

    const handleGenerateLink = async (inv: ReceivableItem) => {
        try {
            const linkData = await api.createPaymentLink(
                inv.invoice_id,
                inv.customer_name,
                inv.outstanding_amount,
                inv.due_date
            );
            setGeneratedLinks({
                ...generatedLinks,
                [inv.invoice_id]: linkData.short_url
            });
        } catch (err) {
            console.error('Failed to create payment link:', err);
        }
    };


    const filtered = filterSegment === 'ALL'
        ? receivables
        : receivables.filter((r) => r.segment === filterSegment);

    return (
        <div className="space-y-6">
            {/* Header & Segment Filter */}
            <div className="glass-panel rounded-2xl p-6 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
                <div>
                    <div className="flex items-center space-x-2">
                            <span className="px-2.5 py-0.5 text-xs font-bold rounded-full bg-black text-white rounded-full">
                            Customer Intelligence Matrix
                        </span>
                        <span className="text-xs text-[#5d5f5f]">ML repayment scoring</span>
                    </div>
                    <h2 className="text-xl font-bold text-black mt-1">Receivables</h2>
                </div>

                {/* Segment Filter Buttons */}
                <div className="flex items-center space-x-2 bg-[#f3f3f3] p-1 rounded-xl border border-[#cfc4c5]/40">
                    {['ALL', 'RELIABLE', 'MODERATE', 'HIGH_RISK'].map((seg) => (
                        <button
                            key={seg}
                            onClick={() => setFilterSegment(seg)}
                            className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all cursor-pointer ${filterSegment === seg
                                    ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/30'
                                    : 'text-[#5d5f5f] hover:text-black'
                                }`}
                        >
                            {seg.replace('_', ' ')}
                        </button>
                    ))}
                </div>
            </div>

            {/* Receivables Table */}
            <div className="glass-panel rounded-2xl overflow-hidden">
                <div className="overflow-x-auto">
                    <table className="w-full text-left text-xs text-[#1b1b1b]">
                        <thead className="bg-[#f3f3f3] text-[#5d5f5f] font-semibold border-b border-[#cfc4c5]/40 uppercase text-[10px] tracking-wider">
                            <tr>
                                <th className="px-4 py-3">Customer & Segment</th>
                                <th className="px-4 py-3">Invoice #</th>
                                <th className="px-4 py-3 text-right">Outstanding</th>
                                <th className="px-4 py-3 text-center">Reliability Score</th>
                                <th className="px-4 py-3 text-center">15D ML Repay Prob</th>
                                <th className="px-4 py-3 text-center">Priority Score</th>
                                <th className="px-4 py-3">Suggested Action</th>
                                <th className="px-4 py-3 text-right">Action</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-[#cfc4c5]/30 font-sans">
                            {filtered.map((inv) => {
                                const linkUrl = generatedLinks[inv.invoice_id];

                                return (
                                    <tr key={inv.invoice_id} className="hover:bg-white/70 transition-all">
                                        {/* Customer & Segment */}
                                        <td className="px-4 py-3">
                                            <button
                                                onClick={() => onSelectCustomer(inv.customer_id)}
                                                className="font-bold text-black hover:text-[#ba1a1a] text-left transition-colors cursor-pointer block"
                                            >
                                                {inv.customer_name}
                                            </button>
                                            <span className={`text-[9px] uppercase font-bold px-1.5 py-0.5 rounded-full inline-block mt-0.5 ${inv.segment === 'RELIABLE' ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' :
                                                    inv.segment === 'HIGH_RISK' ? 'bg-rose-500/10 text-rose-400 border border-rose-500/20' :
                                                        'bg-amber-500/10 text-amber-400 border border-amber-500/20'
                                                }`}>
                                                {inv.segment.replace('_', ' ')}
                                            </span>
                                        </td>

                                        {/* Invoice Number & Due Date */}
                                        <td className="px-4 py-3 font-mono">
                                            <div className="text-black">{inv.invoice_number}</div>
                                            <div className="text-[10px] text-[#5d5f5f]">Due: {inv.due_date}</div>
                                        </td>

                                        {/* Outstanding Amount */}
                                        <td className="px-4 py-3 text-right font-mono font-bold text-black">
                                            ₹{inv.outstanding_amount.toLocaleString()}
                                        </td>

                                        {/* Reliability Score */}
                                        <td className="px-4 py-3 text-center">
                                            <div className="inline-flex items-center space-x-1">
                                                <span className={`font-mono font-bold text-xs ${inv.reliability_score >= 80 ? 'text-emerald-400' :
                                                        inv.reliability_score >= 60 ? 'text-amber-400' : 'text-rose-400'
                                                    }`}>
                                                    {inv.reliability_score}
                                                </span>
                                                <span className="text-[10px] text-slate-500">/100</span>
                                            </div>
                                        </td>

                                        {/* 15D ML Repay Probability */}
                                        <td className="px-4 py-3 text-center">
                                            <div className="w-20 mx-auto space-y-1">
                                                <div className="flex justify-between text-[10px] font-mono">
                                                    <span className="text-cyan-400 font-bold">{Math.round(inv.repayment_probability_15d * 100)}%</span>
                                                    <span className="text-slate-500">{inv.expected_payment_days}d</span>
                                                </div>
                                                <div className="w-full h-1.5 bg-slate-800 rounded-full overflow-hidden">
                                                    <div
                                                        className={`h-full rounded-full ${inv.repayment_probability_15d >= 0.8 ? 'bg-emerald-400' :
                                                                inv.repayment_probability_15d >= 0.5 ? 'bg-amber-400' : 'bg-rose-400'
                                                            }`}
                                                        style={{ width: `${inv.repayment_probability_15d * 100}%` }}
                                                    ></div>
                                                </div>
                                            </div>
                                        </td>

                                        {/* Priority Score */}
                                        <td className="px-4 py-3 text-center font-mono font-bold text-cyan-300">
                                            {inv.priority_score}
                                        </td>

                                        {/* Suggested Action */}
                                        <td className="px-4 py-3">
                                            <span className={`text-[10px] font-semibold px-2 py-0.5 rounded-full ${inv.suggested_action === 'SEND_PAYMENT_LINK' ? 'bg-cyan-500/10 text-cyan-400 border border-cyan-500/20' :
                                                    inv.suggested_action === 'HUMAN_ESCALATION' ? 'bg-amber-500/10 text-amber-400 border border-amber-500/20' :
                                                        'bg-slate-800 text-slate-300'
                                                }`}>
                                                {inv.suggested_action.replace(/_/g, ' ')}
                                            </span>
                                        </td>

                                        {/* Action Button */}
                                        <td className="px-4 py-3 text-right">
                                            {linkUrl ? (
                                                <a
                                                    href={linkUrl}
                                                    target="_blank"
                                                    rel="noreferrer"
                                                    className="inline-block text-[11px] font-bold text-emerald-400 bg-emerald-500/10 border border-emerald-500/20 px-2.5 py-1 rounded-lg hover:underline"
                                                >
                                                    Razorpay Link
                                                </a>
                                            ) : (
                                                <button onClick={() => handleGenerateLink(inv)} className="bg-cyan-500/20 hover:bg-cyan-500/30 text-cyan-300 border border-cyan-500/30 font-semibold text-xs px-3 py-1 rounded-lg whitespace-nowrap">Razorpay Link</button>
                                            )}
                                            <button onClick={() => setModal({ type: 'payment', invoice: inv })} className="ml-1 border border-emerald-300 text-emerald-700 font-semibold text-xs px-2 py-1 rounded-lg">Record payment</button>
                                            <button onClick={() => setModal({ type: 'edit-invoice', invoice: inv })} className="ml-1 border border-black text-black font-semibold text-xs px-2 py-1 rounded-lg">Edit invoice</button>
                                        </td>
                                    </tr>
                                );
                            })}
                        </tbody>
                    </table>
                </div>
            </div>
            {modal && <BusinessActionModal title={modal.type === 'payment' ? `Record payment from ${modal.invoice.customer_name}` : `Edit ${modal.invoice.invoice_number}`} subtitle={modal.type === 'payment' ? 'Update the receivable and cash position with a traceable payment record.' : 'Update invoice value or due date without losing the audit trail.'} mode={modal.type} maximum={modal.type === 'payment' ? modal.invoice.outstanding_amount : undefined} initialAmount={modal.type === 'payment' ? modal.invoice.outstanding_amount : modal.invoice.total_amount} initialNumber={modal.invoice.invoice_number} initialDueDate={modal.invoice.due_date} onClose={() => setModal(null)} onSubmit={async (values) => { if (modal.type === 'payment') await api.recordCustomerPayment(modal.invoice.invoice_id, Number(values.amount), String(values.payment_method)); else await api.updateInvoice(modal.invoice.invoice_id, values); await onChanged?.(); }} />}
        </div>
    );
};

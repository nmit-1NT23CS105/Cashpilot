import React from 'react';
import { Factory, ShieldAlert } from 'lucide-react';
import { PayableItem } from '../types';
import { api } from '../services/api';
import { BusinessActionModal } from './BusinessActionModal';

const headingFont = 'Manrope, Inter, system-ui, sans-serif';

interface PayablesViewProps {
    payables: PayableItem[];
    onChanged?: () => Promise<void>;
}

const money = (value: number) => `₹${value.toLocaleString()}`;

export const PayablesView: React.FC<PayablesViewProps> = ({ payables, onChanged }) => {
    const [modal, setModal] = React.useState<{ type: 'payment' | 'edit-payable'; payable: PayableItem } | null>(null);
    const total = payables.reduce((sum, payable) => sum + payable.outstanding_amount, 0);
    const critical = payables.filter((payable) => payable.priority_level === 'CRITICAL').length;

    return (
        <div className="space-y-6">
            <div className="glass-panel rounded-2xl p-6">
                <div className="flex flex-col lg:flex-row lg:items-end justify-between gap-5">
                    <div>
                        <h1 className="text-[24px] md:text-[30px] font-bold tracking-tight text-black flex items-center gap-2" style={{ fontFamily: headingFont }}>
                            <Factory size={27} /> Supplier Payables
                        </h1>
                        <p className="text-[13px] text-[#5d5f5f] mt-1 max-w-3xl">
                            Manufacturer and supplier obligations ranked by due date, criticality, penalties, and liquidity-buffer pressure.
                        </p>
                    </div>
                    <div className="grid grid-cols-2 gap-3">
                        <div className="bg-white/70 border border-[#cfc4c5]/40 rounded-xl p-3 min-w-[150px]">
                            <div className="text-[10px] uppercase tracking-wider text-[#5d5f5f]">Payables</div>
                            <div className="text-xl font-bold text-black">{money(total)}</div>
                        </div>
                        <div className="bg-white/70 border border-[#cfc4c5]/40 rounded-xl p-3 min-w-[150px]">
                            <div className="text-[10px] uppercase tracking-wider text-[#5d5f5f]">Critical</div>
                            <div className="text-xl font-bold text-[#ba1a1a]">{critical}</div>
                        </div>
                    </div>
                </div>
            </div>

            {payables.some((payable) => payable.priority_level === 'CRITICAL') && (
                <div className="glass-card-danger rounded-2xl p-5 flex items-start gap-3">
                    <ShieldAlert size={20} className="text-[#ba1a1a] shrink-0" />
                    <div className="text-[13px] text-[#5d5f5f]">
                        A critical supplier payment is due inside the current forecast window. CashPilot recommends reviewing collection timing before releasing funds.
                    </div>
                </div>
            )}

            <div className="glass-panel rounded-2xl overflow-hidden">
                <div className="overflow-x-auto">
                    <table className="w-full text-left text-[13px]">
                        <thead className="bg-[#f3f3f3] text-[#5d5f5f] uppercase text-[10px] tracking-wider">
                            <tr>
                                <th className="px-4 py-3">Supplier</th>
                                <th className="px-4 py-3">Bill</th>
                                <th className="px-4 py-3 text-right">Outstanding</th>
                                <th className="px-4 py-3">Due Date</th>
                                <th className="px-4 py-3 text-center">Priority</th>
                                <th className="px-4 py-3 text-center">Terms</th>
                                <th className="px-4 py-3 text-right">Recommended Action</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-[#cfc4c5]/30">
                            {payables.map((payable) => (
                                <tr key={payable.id} className="hover:bg-white/70">
                                    <td className="px-4 py-3">
                                        <div className="font-bold text-black">{payable.supplier_name}</div>
                                        <div className="text-[11px] text-[#5d5f5f]">Criticality: {payable.criticality}</div>
                                    </td>
                                    <td className="px-4 py-3 font-mono text-[#5d5f5f]">{payable.bill_number}</td>
                                    <td className="px-4 py-3 text-right font-mono font-bold">{money(payable.outstanding_amount)}</td>
                                    <td className="px-4 py-3 font-mono">{payable.due_date}</td>
                                    <td className="px-4 py-3 text-center">
                                        <span className={`px-2 py-1 rounded-full text-[10px] font-bold ${payable.priority_level === 'CRITICAL' ? 'bg-red-50 text-[#ba1a1a]' : 'bg-amber-50 text-amber-700'}`}>
                                            {payable.priority_level}
                                        </span>
                                    </td>
                                    <td className="px-4 py-3 text-center text-[11px]">
                                        <div className="font-bold text-black">{payable.payment_terms}</div>
                                        <div className="text-[#5d5f5f]">{payable.early_discount_percent}% discount / {payable.late_penalty_percent}% penalty</div>
                                    </td>
                                    <td className="px-4 py-3 text-right">
                                        <span className="font-bold text-[11px] text-black">{payable.recommended_action.replace(/_/g, ' ')}</span>
                                        <div className="flex justify-end gap-1 mt-2"><button onClick={() => setModal({ type: 'payment', payable })} className="border border-emerald-300 text-emerald-700 px-2 py-1 rounded text-[10px] font-bold">Record payment</button><button onClick={() => setModal({ type: 'edit-payable', payable })} className="border border-black px-2 py-1 rounded text-[10px] font-bold">Edit bill</button></div>
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            </div>
            {modal && <BusinessActionModal title={modal.type === 'payment' ? `Pay ${modal.payable.supplier_name}` : `Edit ${modal.payable.bill_number}`} subtitle={modal.type === 'payment' ? 'Record a supplier settlement and update cash and accounts payable.' : 'Update bill value or due date with an audit record.'} mode={modal.type} maximum={modal.type === 'payment' ? modal.payable.outstanding_amount : undefined} initialAmount={modal.type === 'payment' ? modal.payable.outstanding_amount : modal.payable.total_amount} initialNumber={modal.payable.bill_number} initialDueDate={modal.payable.due_date} onClose={() => setModal(null)} onSubmit={async (values) => { if (modal.type === 'payment') await api.recordSupplierPayment(modal.payable.id, Number(values.amount), String(values.payment_method)); else await api.updatePayable(modal.payable.id, values); await onChanged?.(); }} />}
        </div>
    );
};

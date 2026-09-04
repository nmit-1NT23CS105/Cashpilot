import React, { useState } from 'react';
import { CalendarDays, Check, CreditCard, FilePenLine, Landmark, X } from 'lucide-react';

interface BusinessActionModalProps {
    title: string;
    subtitle: string;
    mode: 'payment' | 'edit-invoice' | 'edit-payable' | 'edit-expense';
    maximum?: number;
    initialAmount?: number;
    initialName?: string;
    initialNumber?: string;
    initialDueDate?: string;
    initialRecurring?: boolean;
    onClose: () => void;
    onSubmit: (values: Record<string, unknown>) => Promise<void>;
}

const today = new Date().toISOString().slice(0, 10);

export const BusinessActionModal: React.FC<BusinessActionModalProps> = ({ title, subtitle, mode, maximum, initialAmount = 0, initialName = '', initialNumber = '', initialDueDate = today, initialRecurring = false, onClose, onSubmit }) => {
    const [amount, setAmount] = useState(String(initialAmount));
    const [name, setName] = useState(initialName);
    const [number, setNumber] = useState(initialNumber);
    const [dueDate, setDueDate] = useState(initialDueDate);
    const [paymentDate, setPaymentDate] = useState(today);
    const [paymentMethod, setPaymentMethod] = useState('Bank Transfer');
    const [reference, setReference] = useState('');
    const [notes, setNotes] = useState('');
    const [recurring, setRecurring] = useState(initialRecurring);
    const [busy, setBusy] = useState(false);
    const isPayment = mode === 'payment';
    const submit = async (event: React.FormEvent) => { event.preventDefault(); const numericAmount = Number(amount); if (!numericAmount || numericAmount <= 0 || (maximum !== undefined && numericAmount > maximum + 0.01)) return; setBusy(true); try { await onSubmit({ amount: numericAmount, total_amount: numericAmount, name, invoice_number: number, bill_number: number, due_date: dueDate, payment_date: paymentDate, payment_method: paymentMethod, reference, notes, is_recurring: recurring }); onClose(); } finally { setBusy(false); } };
    return <div className="fixed inset-0 z-[60] bg-black/45 backdrop-blur-sm flex items-center justify-center p-4" role="dialog" aria-modal="true">
        <form onSubmit={submit} className="w-full max-w-lg bg-white rounded-2xl shadow-2xl border border-[#d9d2ca] overflow-hidden">
            <div className="px-6 py-5 border-b border-[#e6e0da] flex items-start justify-between"><div><div className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-[#5d5f5f]"><FilePenLine size={15} /> Business transaction</div><h2 className="text-xl font-bold text-black mt-1">{title}</h2><p className="text-sm text-[#5d5f5f] mt-1">{subtitle}</p></div><button type="button" onClick={onClose} aria-label="Close" className="p-2 rounded-lg hover:bg-[#f3f3f3] text-[#5d5f5f]"><X size={19} /></button></div>
            <div className="p-6 space-y-4 max-h-[70vh] overflow-y-auto">
                {!isPayment && <div className="grid grid-cols-1 sm:grid-cols-2 gap-4"><label className="text-xs font-bold text-[#1b1b1b]">{mode === 'edit-expense' ? 'Expense name' : mode === 'edit-invoice' ? 'Invoice number' : 'Bill number'}<input value={mode === 'edit-expense' ? name : number} onChange={(e) => mode === 'edit-expense' ? setName(e.target.value) : setNumber(e.target.value)} className="mt-1 w-full border border-[#cfc4c5] rounded-lg px-3 py-2.5 text-sm" required /></label><label className="text-xs font-bold">Amount (INR)<input type="number" min="0.01" step="0.01" value={amount} onChange={(e) => setAmount(e.target.value)} className="mt-1 w-full border border-[#cfc4c5] rounded-lg px-3 py-2.5 text-sm" required /></label></div>}
                {isPayment && <div><label className="text-xs font-bold">Amount received / paid (INR)<input type="number" min="0.01" max={maximum} step="0.01" value={amount} onChange={(e) => setAmount(e.target.value)} className="mt-1 w-full border border-[#cfc4c5] rounded-lg px-3 py-2.5 text-lg font-bold" required /></label><div className="text-xs text-[#5d5f5f] mt-1">Outstanding available: ₹{(maximum || 0).toLocaleString()}</div></div>}
                {!isPayment && mode !== 'edit-expense' && <label className="text-xs font-bold">Due date<input type="date" value={dueDate} onChange={(e) => setDueDate(e.target.value)} className="mt-1 w-full border border-[#cfc4c5] rounded-lg px-3 py-2.5 text-sm" required /></label>}
                {isPayment && <div className="grid grid-cols-1 sm:grid-cols-2 gap-4"><label className="text-xs font-bold"><span className="flex items-center gap-1"><CalendarDays size={14} /> Payment date</span><input type="date" value={paymentDate} onChange={(e) => setPaymentDate(e.target.value)} className="mt-1 w-full border border-[#cfc4c5] rounded-lg px-3 py-2.5 text-sm" required /></label><label className="text-xs font-bold"><span className="flex items-center gap-1"><CreditCard size={14} /> Payment method</span><select value={paymentMethod} onChange={(e) => setPaymentMethod(e.target.value)} className="mt-1 w-full border border-[#cfc4c5] rounded-lg px-3 py-2.5 text-sm"><option>Bank Transfer</option><option>Cash</option><option>UPI</option><option>Razorpay</option><option>Cheque</option></select></label></div>}
                {isPayment && <label className="text-xs font-bold"><span className="flex items-center gap-1"><Landmark size={14} /> Transaction reference</span><input value={reference} onChange={(e) => setReference(e.target.value)} placeholder="e.g. UTR, receipt number, Razorpay ID" className="mt-1 w-full border border-[#cfc4c5] rounded-lg px-3 py-2.5 text-sm" /></label>}
                {mode === 'edit-expense' && <label className="flex items-center gap-2 text-sm font-semibold"><input type="checkbox" checked={recurring} onChange={(e) => setRecurring(e.target.checked)} /> Recurring expense</label>}
                <label className="text-xs font-bold">Notes<textarea value={notes} onChange={(e) => setNotes(e.target.value)} placeholder="Add an internal note for the audit trail" rows={3} className="mt-1 w-full border border-[#cfc4c5] rounded-lg px-3 py-2.5 text-sm resize-none" /></label>
            </div>
            <div className="px-6 py-4 border-t border-[#e6e0da] bg-[#faf9f7] flex justify-end gap-2"><button type="button" onClick={onClose} className="border border-[#cfc4c5] rounded-lg px-4 py-2.5 text-sm font-bold">Cancel</button><button disabled={busy} className="bg-black text-white rounded-lg px-4 py-2.5 text-sm font-bold inline-flex items-center gap-2 disabled:opacity-50"><Check size={16} />{busy ? 'Saving...' : isPayment ? 'Confirm payment' : 'Save changes'}</button></div>
        </form>
    </div>;
};

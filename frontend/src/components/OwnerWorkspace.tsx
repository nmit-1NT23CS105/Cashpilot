import React, { useRef, useState } from 'react';
import { FileUp, Plus, Trash2 } from 'lucide-react';
import { CustomerListItem } from '../types';
import { api } from '../services/api';

interface OwnerWorkspaceProps { customers: CustomerListItem[]; onSaved: () => Promise<void>; onLogout: () => void; username: string; }
type EntryType = 'customer' | 'sale' | 'purchase' | 'expense';
const today = new Date().toISOString().slice(0, 10);

export const OwnerWorkspace: React.FC<OwnerWorkspaceProps> = ({ customers, onSaved, onLogout, username }) => {
    const [type, setType] = useState<EntryType>('sale');
    const [form, setForm] = useState<Record<string, string>>({ date: today, issue_date: today, due_date: today, purchase_date: today });
    const [message, setMessage] = useState('');
    const [importing, setImporting] = useState(false);
    const fileInputRef = useRef<HTMLInputElement>(null);
    const [pendingFile, setPendingFile] = useState<File | null>(null);
    const [preview, setPreview] = useState<{ total_rows: number; valid_rows: number; invalid_rows: number; rows: Array<Record<string, unknown>> } | null>(null);
    const update = (key: string, value: string) => setForm((current) => ({ ...current, [key]: value }));
    const input = (label: string, key: string, required = true, inputType = 'text') => <label className="block text-sm font-medium text-black">{label}<input required={required} type={inputType} value={form[key] || ''} onChange={(e) => update(key, e.target.value)} className="mt-1 w-full border border-[#d5d0ca] rounded-lg p-2.5 bg-white" /></label>;
    const submit = async (event: React.FormEvent) => {
        event.preventDefault(); setMessage('');
        try {
            if (type === 'customer') await api.createCustomer(form);
            if (type === 'sale') await api.createSale({ ...form, amount: Number(form.amount) });
            if (type === 'purchase') await api.createPurchase({ ...form, amount: Number(form.amount) });
            if (type === 'expense') await api.createExpense({ ...form, amount: Number(form.amount), is_recurring: form.is_recurring === 'true' });
            setMessage('Saved successfully.'); setForm({ date: today, issue_date: today, due_date: today, purchase_date: today }); await onSaved();
        } catch (err) { setMessage(err instanceof Error ? err.message : 'Unable to save record.'); }
    };
    const clear = async () => { if (!window.confirm('Delete all business and demo records? This cannot be undone.')) return; await api.clearBusinessData(); setMessage('All business data cleared.'); await onSaved(); };
    const previewFile = async (file: File) => { setMessage(''); setPendingFile(file); setPreview(null); try { const result = await api.previewBusinessFile(file); setPreview(result); } catch (err) { setPendingFile(null); setMessage(err instanceof Error ? err.message : 'Import failed.'); } finally { if (fileInputRef.current) fileInputRef.current.value = ''; } };
    const importFile = async () => { if (!pendingFile || importing) return; setMessage('Importing...'); setImporting(true); try { const result = await api.importBusinessFile(pendingFile); const skipped = result.skipped || 0; setMessage(`${result.imported} records imported${skipped ? `, ${skipped} skipped.` : '.'}`); setPendingFile(null); setPreview(null); await onSaved(); } catch (err) { setMessage(err instanceof Error ? err.message : 'Import failed.'); } finally { setImporting(false); } };

    return <div className="space-y-6">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-3"><div><h1 className="text-2xl font-bold">Owner</h1><span className="text-xs text-[#66615d]">{username}</span></div><div className="flex flex-wrap gap-2"><label className="border border-black rounded-lg px-3 py-2 text-sm font-bold cursor-pointer flex items-center gap-2"><FileUp size={15} /> Import file<input ref={fileInputRef} type="file" accept=".csv,.xlsx,.xlsm,.pdf,.docx,.png,.jpg,.jpeg,.webp" className="hidden" onChange={(e) => e.target.files?.[0] && previewFile(e.target.files[0])} /></label><button onClick={onLogout} className="border rounded-lg px-3 py-2 text-sm font-bold">Sign out</button><button onClick={clear} className="border border-red-200 text-red-700 rounded-lg px-3 py-2 text-sm font-bold flex items-center gap-2"><Trash2 size={15} /> Clear</button></div></div>
        {preview && <div className="glass-panel rounded-2xl p-5 space-y-3"><div className="flex items-center justify-between"><h2 className="font-bold">Import preview</h2><span className="text-sm text-[#5d5f5f]">{preview.valid_rows}/{preview.total_rows} valid</span></div><div className="max-h-40 overflow-auto text-xs"><table className="w-full text-left"><tbody>{preview.rows.slice(0, 5).map((row, index) => <tr key={index} className="border-b border-[#cfc4c5]/30">{Object.values(row).slice(0, 4).map((value, cell) => <td key={cell} className="p-2">{String(value ?? '')}</td>)}</tr>)}</tbody></table></div><div className="flex gap-2"><button onClick={importFile} disabled={!preview.valid_rows || importing} className="bg-black text-white rounded-lg px-4 py-2 text-sm font-bold disabled:opacity-40">{importing ? 'Importing...' : 'Confirm import'}</button><button onClick={() => { setPreview(null); setPendingFile(null); }} className="border rounded-lg px-4 py-2 text-sm font-bold">Cancel</button></div></div>}
        <div className="flex flex-wrap gap-2">{(['sale', 'purchase', 'expense', 'customer'] as EntryType[]).map((item) => <button key={item} onClick={() => { setType(item); setMessage(''); }} className={`px-4 py-2 rounded-lg text-sm font-bold border ${type === item ? 'bg-black text-white' : 'bg-white text-black'}`}><Plus size={15} className="inline mr-1" />{item[0].toUpperCase() + item.slice(1)}</button>)}</div>
        <form onSubmit={submit} className="bg-white border border-[#d9d2ca] rounded-2xl p-6 max-w-3xl grid md:grid-cols-2 gap-4">
            {type === 'customer' && <>{input('Buyer name', 'name')}{input('Phone', 'phone', false)}{input('Email', 'email', false, 'email')}{input('Address', 'address', false)}{input('Credit days', 'credit_period_days', false, 'number')}{input('Credit limit (INR)', 'credit_limit', false, 'number')}</>}
            {type === 'sale' && <>{customers.length ? <label className="block text-sm font-medium">Buyer<select required value={form.customer_id || ''} onChange={(e) => update('customer_id', e.target.value)} className="mt-1 w-full border rounded-lg p-2.5"><option value="">Select buyer</option>{customers.map((customer) => <option key={customer.id} value={customer.id}>{customer.name}</option>)}</select></label> : <p className="md:col-span-2 text-sm text-amber-700 bg-amber-50 p-3 rounded-lg">Add a buyer first.</p>}{input('Invoice #', 'invoice_number', false)}{input('Total (INR)', 'amount', true, 'number')}{input('Paid (INR)', 'paid_amount', false, 'number')}{input('Issued', 'issue_date', true, 'date')}{input('Due', 'due_date', true, 'date')}</>}
            {type === 'purchase' && <>{input('Seller name', 'supplier_name')}{input('Contact person', 'contact_person', false)}{input('Phone', 'phone', false)}{input('Email', 'email', false, 'email')}{input('Category', 'category', false)}{input('Bill #', 'bill_number', false)}{input('Total (INR)', 'amount', true, 'number')}{input('Paid (INR)', 'paid_amount', false, 'number')}{input('Bought', 'purchase_date', true, 'date')}{input('Due', 'due_date', true, 'date')}<label className="block text-sm font-medium">Criticality<select value={form.criticality || 'HIGH'} onChange={(e) => update('criticality', e.target.value)} className="mt-1 w-full border rounded-lg p-2.5"><option>CRITICAL</option><option>HIGH</option><option>MEDIUM</option><option>LOW</option></select></label><label className="block text-sm font-medium">Terms<select value={form.payment_terms || 'NET_15'} onChange={(e) => update('payment_terms', e.target.value)} className="mt-1 w-full border rounded-lg p-2.5"><option>NET_7</option><option>NET_15</option><option>NET_30</option></select></label></>}
            {type === 'expense' && <>{input('Expense', 'title')}{input('Category', 'category', false)}{input('Type', 'category_type', false)}{input('Amount (INR)', 'amount', true, 'number')}{input('Date', 'date', true, 'date')}<label className="block text-sm font-medium">Recurring<select value={form.is_recurring || 'false'} onChange={(e) => update('is_recurring', e.target.value)} className="mt-1 w-full border rounded-lg p-2.5"><option value="false">No</option><option value="true">Yes</option></select></label></>}
            <div className="md:col-span-2 flex items-center gap-4"><button disabled={type === 'sale' && !customers.length} className="bg-black text-white rounded-lg px-5 py-3 font-bold disabled:opacity-40">Save {type}</button>{message && <span className="text-sm text-[#66615d]">{message}</span>}</div>
        </form>
    </div>;
};

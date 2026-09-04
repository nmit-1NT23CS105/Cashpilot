import React from 'react';
import { AlertTriangle, ReceiptText } from 'lucide-react';
import { ExpenseItem } from '../types';
import { api } from '../services/api';
import { BusinessActionModal } from './BusinessActionModal';

const headingFont = 'Manrope, Inter, system-ui, sans-serif';

interface ExpensesViewProps {
    expenses: ExpenseItem[];
    monthlyBreakdown: Record<string, number>;
    onChanged?: () => Promise<void>;
}

const money = (value: number) => `₹${value.toLocaleString()}`;

export const ExpensesView: React.FC<ExpensesViewProps> = ({ expenses, monthlyBreakdown, onChanged }) => {
    const [editingExpense, setEditingExpense] = React.useState<ExpenseItem | null>(null);
    const total = expenses.reduce((sum, expense) => sum + expense.amount, 0);
    const anomalies = expenses.filter((expense) => expense.is_anomaly);
    const recurring = expenses.filter((expense) => expense.is_recurring);
    const breakdown = Object.entries(monthlyBreakdown).sort((a, b) => b[1] - a[1]);

    return (
        <div className="space-y-6">
            <div className="glass-panel rounded-2xl p-6">
                <div className="flex flex-col lg:flex-row lg:items-end justify-between gap-5">
                    <div>
                        <h1 className="text-[24px] md:text-[30px] font-bold tracking-tight text-black" style={{ fontFamily: headingFont }}>
                            Expense Intelligence
                        </h1>
                        <p className="text-[13px] text-[#5d5f5f] mt-1 max-w-3xl">
                            Categorized recurring expenses, unusual spend detection, and review-before-posting controls for cash protection.
                        </p>
                    </div>
                    <div className="grid grid-cols-3 gap-3">
                        <div className="bg-white/70 border border-[#cfc4c5]/40 rounded-xl p-3 min-w-[140px]">
                            <div className="text-[10px] uppercase tracking-wider text-[#5d5f5f]">Monthly Spend</div>
                            <div className="text-xl font-bold text-black">{money(total)}</div>
                        </div>
                        <div className="bg-white/70 border border-[#cfc4c5]/40 rounded-xl p-3 min-w-[140px]">
                            <div className="text-[10px] uppercase tracking-wider text-[#5d5f5f]">Recurring</div>
                            <div className="text-xl font-bold text-black">{recurring.length}</div>
                        </div>
                        <div className="bg-white/70 border border-[#cfc4c5]/40 rounded-xl p-3 min-w-[140px]">
                            <div className="text-[10px] uppercase tracking-wider text-[#5d5f5f]">Anomalies</div>
                            <div className="text-xl font-bold text-[#ba1a1a]">{anomalies.length}</div>
                        </div>
                    </div>
                </div>
            </div>

            {anomalies.map((expense) => (
                <div key={expense.id} className="glass-card-danger rounded-2xl p-5 flex items-start gap-3">
                    <AlertTriangle size={20} className="text-[#ba1a1a] shrink-0 mt-0.5" />
                    <div>
                        <div className="font-bold text-[#ba1a1a] text-sm">{expense.title}</div>
                        <div className="text-[13px] text-[#5d5f5f] mt-1">
                            {expense.anomaly_reason} Review this cost before it is paid or posted into the final ledger.
                        </div>
                    </div>
                </div>
            ))}

            <div className="grid grid-cols-1 lg:grid-cols-5 gap-5">
                <section className="lg:col-span-2 glass-panel rounded-2xl p-5">
                    <h2 className="text-sm font-bold text-black flex items-center gap-2 mb-4">
                        <ReceiptText size={18} /> Monthly Breakdown
                    </h2>
                    <div className="space-y-3">
                        {breakdown.map(([category, amount]) => {
                            const width = `${Math.max(8, (amount / Math.max(1, total)) * 100)}%`;
                            return (
                                <div key={category}>
                                    <div className="flex justify-between text-[12px] mb-1">
                                        <span className="font-medium text-black">{category}</span>
                                        <span className="font-mono text-[#5d5f5f]">{money(amount)}</span>
                                    </div>
                                    <div className="h-2 rounded-full bg-[#e8e8e8] overflow-hidden">
                                        <div className="h-full bg-black rounded-full" style={{ width }} />
                                    </div>
                                </div>
                            );
                        })}
                    </div>
                </section>

                <section className="lg:col-span-3 glass-panel rounded-2xl overflow-hidden">
                    <div className="px-5 py-4 border-b border-[#cfc4c5]/30">
                        <h2 className="text-sm font-bold text-black">Expense Register</h2>
                    </div>
                    <div className="overflow-x-auto">
                        <table className="w-full text-left text-[13px]">
                            <thead className="bg-[#f3f3f3] text-[#5d5f5f] uppercase text-[10px] tracking-wider">
                                <tr>
                                    <th className="px-4 py-3">Expense</th>
                                    <th className="px-4 py-3">Category</th>
                                    <th className="px-4 py-3 text-right">Amount</th>
                                    <th className="px-4 py-3 text-center">Recurrence</th>
                                    <th className="px-4 py-3 text-center">Review</th>
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-[#cfc4c5]/30">
                                {expenses.map((expense) => (
                                    <tr key={expense.id} className="hover:bg-white/70">
                                        <td className="px-4 py-3">
                                            <div className="font-bold text-black">{expense.title}</div>
                                            <div className="text-[11px] text-[#5d5f5f]">{expense.date}</div>
                                        </td>
                                        <td className="px-4 py-3">
                                            <div className="font-medium text-black">{expense.category}</div>
                                            <div className="text-[10px] text-[#5d5f5f]">{expense.category_type}</div>
                                        </td>
                                        <td className="px-4 py-3 text-right font-mono font-bold">{money(expense.amount)}</td>
                                        <td className="px-4 py-3 text-center text-[12px]">{expense.is_recurring ? expense.frequency : 'One-time'}</td>
                                        <td className="px-4 py-3 text-center">
                                            <span className={`px-2 py-1 rounded-full text-[10px] font-bold ${expense.is_anomaly ? 'bg-red-50 text-[#ba1a1a]' : 'bg-emerald-50 text-emerald-700'}`}>
                                                {expense.is_anomaly ? 'REVIEW' : 'NORMAL'}
                                            </span>
                                            <div className="flex justify-center gap-1 mt-2"><button onClick={() => setEditingExpense(expense)} className="border border-black px-2 py-1 rounded text-[10px] font-bold">Edit expense</button></div>
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                </section>
            </div>
            {editingExpense && <BusinessActionModal title={`Edit ${editingExpense.title}`} subtitle="Update the expense record and apply the cash correction automatically." mode="edit-expense" initialName={editingExpense.title} initialAmount={editingExpense.amount} initialRecurring={editingExpense.is_recurring} onClose={() => setEditingExpense(null)} onSubmit={async (values) => { await api.updateExpense(editingExpense.id, values); await onChanged?.(); }} />}
        </div>
    );
};

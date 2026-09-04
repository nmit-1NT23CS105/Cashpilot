import React, { useEffect, useState } from 'react';
import { api } from '../services/api';

export const LedgerView: React.FC = () => {
    const [data, setData] = useState<any>(null);
    const [loading, setLoading] = useState<boolean>(true);

    useEffect(() => {
        api.getLedger().then(res => {
            setData(res);
            setLoading(false);
        }).catch(err => {
            console.error('Failed to load ledger:', err);
            setLoading(false);
        });
    }, []);

    if (loading || !data) {
        return <div className="text-[#5d5f5f] text-sm p-6 text-center">Loading ledger...</div>;
    }

    const { balance_sheet, ledger_entries, audit_trail } = data;

    return (
        <div className="space-y-6">
            {/* Header & Accounting Proof Badge */}
            <div className="glass-panel rounded-2xl p-6 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
                <div>
                    <div className="flex items-center space-x-2">
                        <span className="px-2.5 py-0.5 text-xs font-bold rounded-full bg-black text-white">
                            Double-Entry Audit Engine
                        </span>
                        <span className="text-xs text-[#5d5f5f]">Debits = credits</span>
                    </div>
                    <h2 className="text-xl font-bold text-black mt-1">Ledger & audit log</h2>
                </div>

                {/* Verification Status Badge */}
                <div className={`px-4 py-2 rounded-xl font-bold text-xs flex items-center space-x-2 border ${balance_sheet.is_balanced
                        ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30'
                        : 'bg-rose-500/10 text-rose-400 border-rose-500/30'
                    }`}>
                    <span>{balance_sheet.is_balanced ? '✓ DEBITS == CREDITS BALANCED' : '❌ UNBALANCED LEDGER'}</span>
                </div>
            </div>

            {/* Balance Sheet Cards */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                {/* Assets */}
                <div className="glass-panel rounded-2xl p-5 space-y-3">
                    <div className="flex items-center justify-between border-b border-slate-800 pb-2">
                        <h3 className="text-sm font-bold text-black uppercase tracking-wider">Assets</h3>
                        <span className="text-sm font-mono font-bold text-cyan-400">
                            ₹{balance_sheet.total_assets.toLocaleString()}
                        </span>
                    </div>
                    <div className="space-y-2 text-xs font-mono">
                        {Object.entries(balance_sheet.assets).map(([acct, bal]: [string, any]) => (
                            <div key={acct} className="flex justify-between text-slate-300">
                                <span>{acct}</span>
                                <span className="font-bold text-black">₹{bal.toLocaleString()}</span>
                            </div>
                        ))}
                    </div>
                </div>

                {/* Liabilities */}
                <div className="glass-panel rounded-2xl p-5 space-y-3">
                    <div className="flex items-center justify-between border-b border-slate-800 pb-2">
                        <h3 className="text-sm font-bold text-black uppercase tracking-wider">Liabilities</h3>
                        <span className="text-sm font-mono font-bold text-amber-400">
                            ₹{balance_sheet.total_liabilities.toLocaleString()}
                        </span>
                    </div>
                    <div className="space-y-2 text-xs font-mono">
                        {Object.entries(balance_sheet.liabilities).map(([acct, bal]: [string, any]) => (
                            <div key={acct} className="flex justify-between text-slate-300">
                                <span>{acct}</span>
                                <span className="font-bold text-black">₹{bal.toLocaleString()}</span>
                            </div>
                        ))}
                    </div>
                </div>

                {/* Equity */}
                <div className="glass-panel rounded-2xl p-5 space-y-3">
                    <div className="flex items-center justify-between border-b border-slate-800 pb-2">
                        <h3 className="text-sm font-bold text-black uppercase tracking-wider">Equity</h3>
                        <span className="text-sm font-mono font-bold text-emerald-400">
                            ₹{balance_sheet.total_equity.toLocaleString()}
                        </span>
                    </div>
                    <div className="space-y-2 text-xs font-mono">
                        {Object.entries(balance_sheet.equity).map(([acct, bal]: [string, any]) => (
                            <div key={acct} className="flex justify-between text-slate-300">
                                <span>{acct}</span>
                                <span className="font-bold text-black">₹{bal.toLocaleString()}</span>
                            </div>
                        ))}
                    </div>
                </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div className="glass-panel rounded-2xl p-5 space-y-3">
                    <div className="flex items-center justify-between border-b border-slate-800 pb-2">
                        <h3 className="text-sm font-bold text-black uppercase tracking-wider">Revenue Accounts</h3>
                        <span className="text-sm font-mono font-bold text-emerald-600">₹{(balance_sheet.total_revenue || 0).toLocaleString()}</span>
                    </div>
                    <div className="space-y-2 text-xs font-mono">{Object.entries(balance_sheet.revenue || {}).map(([acct, bal]: [string, any]) => <div key={acct} className="flex justify-between"><span>{acct}</span><span className="font-bold">₹{bal.toLocaleString()}</span></div>)}</div>
                </div>
                <div className="glass-panel rounded-2xl p-5 space-y-3">
                    <div className="flex items-center justify-between border-b border-slate-800 pb-2">
                        <h3 className="text-sm font-bold text-black uppercase tracking-wider">Expense Accounts</h3>
                        <span className="text-sm font-mono font-bold text-red-700">₹{(balance_sheet.total_expenses || 0).toLocaleString()}</span>
                    </div>
                    <div className="space-y-2 text-xs font-mono">{Object.entries(balance_sheet.expenses || {}).map(([acct, bal]: [string, any]) => <div key={acct} className="flex justify-between"><span>{acct}</span><span className="font-bold">₹{bal.toLocaleString()}</span></div>)}</div>
                </div>
            </div>

            {/* Ledger Entries */}
            <div className="glass-panel rounded-2xl p-6 space-y-4">
                <h3 className="text-sm font-bold text-black">Debit / credit entries</h3>
                <div className="overflow-x-auto">
                    <table className="w-full text-left text-xs text-[#1b1b1b]">
                        <thead className="bg-[#f3f3f3] text-[#5d5f5f] font-semibold border-b border-[#cfc4c5]/40 uppercase text-[10px] tracking-wider">
                            <tr>
                                <th className="px-4 py-3">Date</th>
                                <th className="px-4 py-3">Transaction</th>
                                <th className="px-4 py-3">Debit Account</th>
                                <th className="px-4 py-3">Credit Account</th>
                                <th className="px-4 py-3 text-right">Debit</th>
                                <th className="px-4 py-3 text-right">Credit</th>
                                <th className="px-4 py-3">Source</th>
                                <th className="px-4 py-3">Status</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-[#cfc4c5]/30">
                            {ledger_entries.map((entry: any) => (
                                <tr key={entry.id} className="hover:bg-white/70 transition-all">
                                    <td className="px-4 py-2.5 font-mono text-slate-400">{entry.date}</td>
                                    <td className="px-4 py-2.5 text-slate-200">{entry.transaction}</td>
                                    <td className="px-4 py-2.5 text-cyan-300">{entry.debit_account}</td>
                                    <td className="px-4 py-2.5 text-amber-300">{entry.credit_account}</td>
                                    <td className="px-4 py-2.5 text-right font-mono">₹{entry.debit.toLocaleString()}</td>
                                    <td className="px-4 py-2.5 text-right font-mono">₹{entry.credit.toLocaleString()}</td>
                                    <td className="px-4 py-2.5 text-slate-400">{entry.source}</td>
                                    <td className="px-4 py-2.5">
                                        <span className="bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 rounded-full px-2 py-0.5 text-[10px] font-bold">
                                            {entry.status}
                                        </span>
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            </div>

            {/* Audit Log Trail */}
            <div className="glass-panel rounded-2xl p-6 space-y-4">
                <h3 className="text-sm font-bold text-black">Audit trail</h3>
                <div className="overflow-x-auto">
                    <table className="w-full text-left text-xs text-[#1b1b1b]">
                        <thead className="bg-[#f3f3f3] text-[#5d5f5f] font-semibold border-b border-[#cfc4c5]/40 uppercase text-[10px] tracking-wider">
                            <tr>
                                <th className="px-4 py-3">Timestamp</th>
                                <th className="px-4 py-3">Actor</th>
                                <th className="px-4 py-3">Action</th>
                                <th className="px-4 py-3">Details</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-[#cfc4c5]/30 font-mono text-[11px]">
                            {audit_trail.map((entry: any) => (
                                <tr key={entry.id} className="hover:bg-white/70 transition-all">
                                    <td className="px-4 py-2.5 text-slate-400">{entry.timestamp}</td>
                                    <td className="px-4 py-2.5 text-cyan-400 font-bold">{entry.actor}</td>
                                    <td className="px-4 py-2.5 text-amber-300 font-semibold">{entry.action}</td>
                                    <td className="px-4 py-2.5 text-slate-200 font-sans">{entry.details}</td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    );
};

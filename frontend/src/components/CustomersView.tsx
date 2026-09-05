import React, { useMemo, useState } from 'react';
import { AlertTriangle, Search, ShieldCheck, UserRoundCheck } from 'lucide-react';
import { CustomerListItem } from '../types';
import { api } from '../services/api';

const headingFont = 'Manrope, Inter, system-ui, sans-serif';

interface CustomersViewProps {
    customers: CustomerListItem[];
    onSelectCustomer: (customerId: string) => void;
    onChanged?: () => Promise<void>;
}

const money = (value: number) => `₹${(value / 100000).toFixed(2)}L`;

export const CustomersView: React.FC<CustomersViewProps> = ({ customers, onSelectCustomer, onChanged }) => {
    const [query, setQuery] = useState('');
    const [segment, setSegment] = useState('ALL');

    const segments = useMemo(() => ['ALL', ...Array.from(new Set(customers.map((c) => c.segment)))], [customers]);
    const filtered = customers.filter((customer) => {
        const matchesQuery = customer.name.toLowerCase().includes(query.toLowerCase());
        const matchesSegment = segment === 'ALL' || customer.segment === segment;
        return matchesQuery && matchesSegment;
    });

    const totalOutstanding = filtered.reduce((sum, item) => sum + item.current_outstanding, 0);
    const averageReliability = filtered.reduce((sum, item) => sum + item.reliability_score, 0) / Math.max(1, filtered.length);
    const riskyCustomers = filtered.filter((item) => item.segment === 'HIGH_RISK' || item.behavior_trend === 'DETERIORATING').length;

    return (
        <div className="space-y-6">
            <div className="glass-panel rounded-2xl p-6">
                <div className="flex flex-col xl:flex-row xl:items-end justify-between gap-5">
                    <div>
                        <h1 className="text-[24px] md:text-[30px] font-bold tracking-tight text-black" style={{ fontFamily: headingFont }}>
                            Buyer payment details
                        </h1>
                        <p className="text-[13px] text-[#5d5f5f] mt-1 max-w-3xl">
                            See who pays on time, who delays, and how much money is still due from each buyer.
                        </p>
                    </div>
                    <div className="grid grid-cols-3 gap-3 w-full xl:w-auto">
                        <div className="bg-white/70 border border-[#cfc4c5]/40 rounded-xl p-3 min-w-[150px]">
                            <div className="text-[10px] uppercase tracking-wider text-[#5d5f5f]">Buyers</div>
                            <div className="text-xl font-bold text-black">{filtered.length}</div>
                        </div>
                        <div className="bg-white/70 border border-[#cfc4c5]/40 rounded-xl p-3 min-w-[150px]">
                            <div className="text-[10px] uppercase tracking-wider text-[#5d5f5f]">Still due</div>
                            <div className="text-xl font-bold text-black">{money(totalOutstanding)}</div>
                        </div>
                        <div className="bg-white/70 border border-[#cfc4c5]/40 rounded-xl p-3 min-w-[150px]">
                            <div className="text-[10px] uppercase tracking-wider text-[#5d5f5f]">Average score</div>
                            <div className="text-xl font-bold text-black">{averageReliability.toFixed(1)}</div>
                        </div>
                    </div>
                </div>

                <div className="mt-5 flex flex-col md:flex-row gap-3">
                    <label className="flex-1 bg-white/80 border border-[#cfc4c5]/40 rounded-xl px-3 py-2 flex items-center gap-2">
                        <Search size={16} className="text-[#5d5f5f]" />
                        <input
                            value={query}
                            onChange={(event) => setQuery(event.target.value)}
                            placeholder="Search buyer"
                            className="bg-transparent outline-none text-sm text-black w-full"
                        />
                    </label>
                    <div className="flex gap-2 overflow-x-auto no-scrollbar">
                        {segments.map((item) => (
                            <button
                                key={item}
                                onClick={() => setSegment(item)}
                                className={`px-3 py-2 rounded-xl text-[12px] font-bold whitespace-nowrap border transition-all ${segment === item
                                        ? 'bg-black text-white border-black'
                                        : 'bg-white/70 text-[#5d5f5f] border-[#cfc4c5]/40 hover:text-black'
                                    }`}
                            >
                                {item.replace(/_/g, ' ')}
                            </button>
                        ))}
                    </div>
                </div>
            </div>

            {riskyCustomers > 0 && (
                <div className="glass-card-warning rounded-2xl p-4 flex items-center gap-3">
                    <AlertTriangle size={20} className="text-amber-600 shrink-0" />
                    <div className="text-sm text-[#5d5f5f]">
                        <span className="font-bold text-black">{riskyCustomers}</span> customer account(s) show high-risk or deteriorating payment behavior.
                    </div>
                </div>
            )}

            <div className="glass-panel rounded-2xl overflow-hidden">
                <div className="overflow-x-auto">
                    <table className="w-full text-left text-[13px]">
                        <thead className="bg-[#f3f3f3] text-[#5d5f5f] uppercase text-[10px] tracking-wider">
                            <tr>
                                <th className="px-4 py-3">Customer</th>
                                <th className="px-4 py-3 text-center">Reliability</th>
                                <th className="px-4 py-3 text-center">On-Time Rate</th>
                                <th className="px-4 py-3 text-center">Avg Delay</th>
                                <th className="px-4 py-3 text-right">Outstanding</th>
                                <th className="px-4 py-3 text-center">Signals</th>
                                <th className="px-4 py-3 text-right">Profile</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-[#cfc4c5]/30">
                            {filtered.map((customer) => (
                                <tr key={customer.id} className="hover:bg-white/70">
                                    <td className="px-4 py-3">
                                        <div className="font-bold text-black">{customer.name}</div>
                                        <div className="text-[11px] text-[#5d5f5f]">{customer.email}</div>
                                    </td>
                                    <td className="px-4 py-3 text-center">
                                        <span className={`font-bold ${customer.reliability_score >= 80 ? 'text-emerald-600' : customer.reliability_score >= 55 ? 'text-amber-600' : 'text-[#ba1a1a]'}`}>
                                            {customer.reliability_score}/100
                                        </span>
                                    </td>
                                    <td className="px-4 py-3 text-center font-mono">{customer.on_time_payment_rate}%</td>
                                    <td className="px-4 py-3 text-center font-mono">{customer.avg_payment_delay_days}d</td>
                                    <td className="px-4 py-3 text-right font-bold font-mono">{money(customer.current_outstanding)}</td>
                                    <td className="px-4 py-3">
                                        <div className="flex flex-wrap justify-center gap-1.5">
                                            <span className={`inline-flex items-center gap-1 px-2 py-1 rounded-full text-[10px] font-bold ${customer.segment === 'HIGH_RISK' ? 'bg-red-50 text-[#ba1a1a]' : 'bg-emerald-50 text-emerald-700'}`}>
                                                {customer.segment === 'HIGH_RISK' ? <AlertTriangle size={12} /> : <ShieldCheck size={12} />}
                                                {customer.segment.replace(/_/g, ' ')}
                                            </span>
                                            {customer.has_active_p2p && (
                                                <span className="px-2 py-1 rounded-full text-[10px] font-bold bg-cyan-50 text-cyan-700">P2P</span>
                                            )}
                                        </div>
                                    </td>
                                    <td className="px-4 py-3 text-right">
                                        <button
                                            onClick={() => onSelectCustomer(customer.id)}
                                            className="inline-flex items-center gap-1.5 bg-black text-white px-3 py-1.5 rounded-lg text-[12px] font-bold"
                                        >
                                            <UserRoundCheck size={14} /> Open
                                        </button>
                                        <button onClick={async () => { const name = window.prompt('Update customer name', customer.name); if (name?.trim()) { try { await api.updateCustomer(customer.id, { name }); await onChanged?.(); } catch (err) { window.alert(err instanceof Error ? err.message : 'Unable to update customer'); } } }} className="ml-1 border border-black text-black px-3 py-1.5 rounded-lg text-[12px] font-bold">Edit</button>
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    );
};

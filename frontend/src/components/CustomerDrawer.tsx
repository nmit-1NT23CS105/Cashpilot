import React, { useEffect, useState } from 'react';
import { CustomerProfile } from '../types';
import { api } from '../services/api';

interface CustomerDrawerProps {
    customerId: string | null;
    onClose: () => void;
}

export const CustomerDrawer: React.FC<CustomerDrawerProps> = ({ customerId, onClose }) => {
    const [profile, setProfile] = useState<CustomerProfile | null>(null);
    const [loading, setLoading] = useState<boolean>(false);

    useEffect(() => {
        if (!customerId) return;
        setLoading(true);
        api.getCustomerProfile(customerId).then((res) => {
            setProfile(res);
            setLoading(false);
        }).catch((err) => {
            console.error('Failed to load customer profile:', err);
            setLoading(false);
        });
    }, [customerId]);

    if (!customerId) return null;

    return (
        <div className="fixed inset-0 z-50 bg-slate-950/70 backdrop-blur-sm flex justify-end">
            <div className="w-full max-w-lg bg-[#0b0f19] border-l border-slate-800 h-full flex flex-col justify-between shadow-2xl overflow-y-auto">
                {/* Drawer Header */}
                <div className="p-5 border-b border-slate-800 flex items-center justify-between bg-slate-900/90">
                    <div>
                        <div className="flex items-center space-x-2">
                            <span className="px-2 py-0.5 text-[10px] uppercase font-bold rounded-full bg-cyan-500/10 text-cyan-400 border border-cyan-500/20">
                                Customer Intelligence Profile
                            </span>
                        </div>
                        <h3 className="font-bold text-white text-lg mt-1">{profile?.customer.name || 'Customer Profile'}</h3>
                    </div>
                    <button
                        onClick={onClose}
                        className="text-slate-400 hover:text-white p-1 rounded-lg hover:bg-slate-800 transition-all text-sm font-bold cursor-pointer"
                    >
                        ✕
                    </button>
                </div>

                {/* Drawer Content Body */}
                {loading || !profile ? (
                    <div className="p-8 text-center text-slate-400 text-sm">Loading Customer Intelligence...</div>
                ) : (
                    <div className="p-6 space-y-6 text-xs text-slate-300 font-sans">
                        {/* Reliability Score & Risk Segment */}
                        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-4 flex items-center justify-between">
                            <div>
                                <div className="text-[11px] text-slate-400 font-medium">Customer Reliability Score</div>
                                <div className="text-3xl font-bold font-mono text-cyan-400 mt-1">
                                    {profile.customer.reliability_score}
                                    <span className="text-sm text-slate-500 font-normal"> / 100</span>
                                </div>
                            </div>
                            <div className="text-right">
                                <span className={`text-xs uppercase font-bold px-3 py-1 rounded-full border ${profile.customer.segment === 'RELIABLE' ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20' :
                                        profile.customer.segment === 'HIGH_RISK' ? 'bg-rose-500/10 text-rose-400 border-rose-500/20' :
                                            'bg-amber-500/10 text-amber-400 border-amber-500/20'
                                    }`}>
                                    {profile.customer.segment.replace('_', ' ')}
                                </span>
                                <div className="text-[10px] text-slate-400 mt-1 font-mono">Trend: {profile.customer.behavior_trend}</div>
                            </div>
                        </div>

                        {/* Repayment Performance Stats */}
                        <div className="grid grid-cols-2 gap-3">
                            <div className="bg-slate-900/60 border border-slate-800/80 rounded-xl p-3">
                                <div className="text-[10px] text-slate-400">On-Time Payment Rate</div>
                                <div className="text-lg font-bold font-mono text-emerald-400 mt-1">
                                    {profile.customer.on_time_payment_rate}%
                                </div>
                            </div>
                            <div className="bg-slate-900/60 border border-slate-800/80 rounded-xl p-3">
                                <div className="text-[10px] text-slate-400">Avg Payment Delay</div>
                                <div className="text-lg font-bold font-mono text-amber-400 mt-1">
                                    {profile.customer.avg_payment_delay_days} Days
                                </div>
                            </div>
                        </div>

                        {/* Promise-to-Pay (P2P) Status if Active */}
                        {profile.customer.has_active_p2p && (
                            <div className="bg-cyan-500/10 border border-cyan-500/30 rounded-xl p-4 space-y-1">
                                <div className="flex items-center space-x-2 font-bold text-cyan-300 text-xs">
                                    <span>📌 Promise-to-Pay (P2P) Recorded</span>
                                </div>
                                <p className="text-xs text-cyan-200">
                                    Customer promised repayment of <strong>₹{(profile.customer.p2p_amount || 0).toLocaleString()}</strong> by <strong>{profile.customer.p2p_promised_date}</strong>.
                                </p>
                                <span className="text-[10px] text-emerald-400 font-semibold block pt-1">
                                    ✓ Automated outreach communications paused per AI policy guardrails.
                                </span>
                            </div>
                        )}

                        {/* Invoices List */}
                        <div className="space-y-3">
                            <h4 className="font-bold text-white text-xs">Invoice & Repayment History</h4>
                            <div className="space-y-2">
                                {profile.invoices.map((inv) => (
                                    <div key={inv.id} className="bg-slate-900/80 border border-slate-800 rounded-xl p-3 flex items-center justify-between font-mono text-xs">
                                        <div>
                                            <div className="font-bold text-white">{inv.invoice_number}</div>
                                            <div className="text-[10px] text-slate-500 font-sans">Due: {inv.due_date}</div>
                                        </div>
                                        <div className="text-right">
                                            <div className="font-bold text-cyan-300">₹{inv.outstanding.toLocaleString()}</div>
                                            <span className="text-[9px] uppercase font-bold px-1.5 py-0.5 rounded bg-slate-800 text-slate-300">
                                                {inv.status}
                                            </span>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
};

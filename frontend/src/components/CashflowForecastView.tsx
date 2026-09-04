import React, { useState, useEffect } from 'react';
import { CashflowSummary } from '../types';
import { api } from '../services/api';

interface CashflowForecastViewProps {
    initialSummary: CashflowSummary | null;
    onBufferChange?: (newBuffer: number) => void;
}

export const CashflowForecastView: React.FC<CashflowForecastViewProps> = ({
    initialSummary,
    onBufferChange
}) => {
    const [buffer, setBuffer] = useState<number>(initialSummary?.min_cash_buffer || 200000);
    const [summary, setSummary] = useState<CashflowSummary | null>(initialSummary);
    const [loading, setLoading] = useState<boolean>(false);
    const headingFont = 'Manrope, Inter, system-ui, sans-serif';
    const monoFont = 'JetBrains Mono, ui-monospace, SFMono-Regular, Menlo, monospace';

    const fetchForecast = async (newBuffer: number) => {
        setLoading(true);
        try {
            const res = await api.getCashflowForecast(15, newBuffer);
            setSummary(res);
            if (onBufferChange) onBufferChange(newBuffer);
        } catch (err) {
            console.error('Failed to update forecast:', err);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        if (initialSummary) {
            setBuffer(initialSummary.min_cash_buffer);
            setSummary(initialSummary);
        }
    }, [initialSummary]);

    const handleSliderChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        const val = Number(e.target.value);
        setBuffer(val);
        fetchForecast(val);
    };

    if (!summary || !summary.daily_forecast) {
        return <div className="text-[#5d5f5f] text-sm p-6 text-center">Loading Cash Flow Forecast...</div>;
    }

    const maxCashInForecast = Math.max(...summary.daily_forecast.map((d) => d.projected_cash), buffer * 1.5);

    return (
        <div className="space-y-6">
            {/* Header & Slider */}
            <div className="glass-panel rounded-2xl p-6">
                <div className="flex flex-col lg:flex-row items-start lg:items-center justify-between gap-6">
                    <div>
                        <div className="flex items-center gap-2">
                            <span className="px-3 py-1 text-[13px] font-bold rounded-full bg-black text-white">
                                15-Day Liquidity Autopilot
                            </span>
                            <span className="text-[13px] text-[#5d5f5f]">Deterministic Flow + ML Collection Timing</span>
                        </div>
                        <h2 className="text-[20px] font-bold text-black mt-2" style={{ fontFamily: headingFont }}>
                            Cash Flow & Safety Buffer Forecaster
                        </h2>
                        <p className="text-[13px] text-[#5d5f5f] mt-0.5">
                            Simulates daily inflows, scheduled supplier payables, and recurring operating expenses.
                        </p>
                    </div>

                    {/* Slider */}
                    <div className="glass-panel rounded-xl p-4 min-w-[300px] space-y-2 border border-[#cfc4c5]/30">
                        <div className="flex items-center justify-between">
                            <label className="text-[13px] font-bold text-black">Min Safe Cash Buffer:</label>
                            <span className="text-sm font-bold text-black" style={{ fontFamily: monoFont }}>₹{(buffer / 100000).toFixed(2)}L</span>
                        </div>
                        <input
                            type="range"
                            min="100000"
                            max="500000"
                            step="10000"
                            value={buffer}
                            onChange={handleSliderChange}
                            className="w-full h-2 bg-[#e8e8e8] rounded-lg appearance-none cursor-pointer accent-black"
                        />
                        <div className="flex items-center justify-between text-[10px] text-[#7e7576]">
                            <span>₹1.0L (Aggressive)</span>
                            <span>₹2.5L (Default)</span>
                            <span>₹5.0L (Conservative)</span>
                        </div>
                    </div>
                </div>

                {/* Summary Indicators */}
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-6 pt-4 border-t border-[#cfc4c5]/30">
                    <div>
                        <div className="text-[11px] text-[#5d5f5f] uppercase tracking-wider">Current Cash</div>
                        <div className="text-lg font-bold text-black" style={{ fontFamily: monoFont }}>₹{(summary.current_cash / 100000).toFixed(2)}L</div>
                    </div>
                    <div>
                        <div className="text-[11px] text-[#5d5f5f] uppercase tracking-wider">15D Expected Inflow</div>
                        <div className="text-lg font-bold text-emerald-600" style={{ fontFamily: monoFont }}>₹{(summary.total_expected_inflow / 100000).toFixed(2)}L</div>
                    </div>
                    <div>
                        <div className="text-[11px] text-[#5d5f5f] uppercase tracking-wider">Scheduled Payables</div>
                        <div className="text-lg font-bold text-amber-600" style={{ fontFamily: monoFont }}>₹{(summary.total_scheduled_outflow / 100000).toFixed(2)}L</div>
                    </div>
                    <div>
                        <div className="text-[11px] text-[#5d5f5f] uppercase tracking-wider">Min Projected Cash</div>
                        <div className={`text-lg font-bold ${summary.has_liquidity_violation ? 'text-[#ba1a1a]' : 'text-black'}`} style={{ fontFamily: monoFont }}>
                            ₹{(summary.min_projected_cash / 100000).toFixed(2)}L
                        </div>
                    </div>
                </div>
            </div>

            {/* Chart */}
            <div className="glass-panel rounded-2xl p-6 space-y-4">
                <h3 className="text-sm font-bold text-black flex items-center justify-between">
                    <span>15-Day Cash Balance vs Safety Threshold</span>
                    <span className="text-[12px] font-normal text-[#5d5f5f]">Black: Projected Cash | Red Line: Min Buffer</span>
                </h3>

                <div className="h-48 flex items-end justify-between gap-1 sm:gap-2 pt-6 pb-2 px-2 bg-[#f3f3f3] rounded-xl border border-[#cfc4c5]/30 relative">
                    <div
                        className="absolute left-0 right-0 border-b-2 border-dashed border-[#ba1a1a]/60 z-10 pointer-events-none"
                        style={{ bottom: `${(buffer / maxCashInForecast) * 100}%` }}
                    >
                        <span className="absolute right-2 -top-5 text-[10px] font-bold text-[#ba1a1a] bg-white px-1 rounded" style={{ fontFamily: monoFont }}>
                            Buffer: ₹{(buffer / 100000).toFixed(1)}L
                        </span>
                    </div>

                    {summary.daily_forecast.map((d) => {
                        const heightPercent = Math.max(10, Math.min(100, (d.projected_cash / maxCashInForecast) * 100));
                        return (
                            <div key={d.day} className="flex-1 flex flex-col items-center group relative">
                                <div className="absolute bottom-full mb-2 hidden group-hover:flex flex-col bg-white border border-[#cfc4c5] text-[10px] p-2 rounded-lg text-[#1b1b1b] z-30 shadow-xl whitespace-nowrap">
                                    <span className="font-bold text-black">Day {d.day} ({d.date})</span>
                                    <span>Cash: ₹{d.projected_cash.toLocaleString()}</span>
                                    <span className="text-emerald-600">+In: ₹{d.inflow_expected.toLocaleString()}</span>
                                    <span className="text-amber-600">-Out: ₹{d.outflow_scheduled.toLocaleString()}</span>
                                    {d.events.length > 0 && (
                                        <span className="text-[#ba1a1a] font-bold mt-1">📌 {d.events.join(', ')}</span>
                                    )}
                                </div>

                                <div
                                    className={`w-full max-w-[28px] rounded-t-sm transition-all ${d.buffer_violation
                                            ? 'bg-gradient-to-t from-[#ba1a1a] to-[#e04040] shadow-md'
                                            : 'bg-gradient-to-t from-black/80 to-black/40'
                                        }`}
                                    style={{ height: `${heightPercent}%` }}
                                ></div>

                                <span className="text-[10px] text-[#7e7576] mt-1" style={{ fontFamily: monoFont }}>D{d.day}</span>
                            </div>
                        );
                    })}
                </div>
            </div>

            {/* Daily Table */}
            <div className="glass-panel rounded-2xl overflow-hidden">
                <div className="px-6 py-4 border-b border-[#cfc4c5]/30 flex items-center justify-between">
                    <h3 className="text-sm font-bold text-black">Daily Cash Movement Schedule</h3>
                    <span className="text-[12px] text-[#5d5f5f]">15 Days Detailed Ledger Simulation</span>
                </div>

                <div className="overflow-x-auto">
                    <table className="w-full text-left text-[13px] text-[#1b1b1b]">
                        <thead className="bg-[#f3f3f3] text-[#5d5f5f] font-medium border-b border-[#cfc4c5]/30 uppercase text-[10px] tracking-wider">
                            <tr>
                                <th className="px-4 py-3">Day</th>
                                <th className="px-4 py-3">Date</th>
                                <th className="px-4 py-3 text-right">Expected Inflow</th>
                                <th className="px-4 py-3 text-right">Scheduled Outflow</th>
                                <th className="px-4 py-3 text-right">Net Daily Change</th>
                                <th className="px-4 py-3 text-right">Projected Cash</th>
                                <th className="px-4 py-3">Key Scheduled Events</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-[#cfc4c5]/20" style={{ fontFamily: monoFont }}>
                            {summary.daily_forecast.map((d) => (
                                <tr
                                    key={d.day}
                                    className={`hover:bg-white/40 transition-all ${d.buffer_violation ? 'bg-red-50 text-[#ba1a1a] font-bold' : ''
                                        }`}
                                >
                                    <td className="px-4 py-3 text-[#5d5f5f]">Day {d.day}</td>
                                    <td className="px-4 py-3">{d.date}</td>
                                    <td className="px-4 py-3 text-right text-emerald-600">
                                        {d.inflow_expected > 0 ? `+₹${d.inflow_expected.toLocaleString()}` : '-'}
                                    </td>
                                    <td className="px-4 py-3 text-right text-amber-600">
                                        {d.outflow_scheduled > 0 ? `-₹${d.outflow_scheduled.toLocaleString()}` : '-'}
                                    </td>
                                    <td className={`px-4 py-3 text-right ${d.net_flow >= 0 ? 'text-emerald-600' : 'text-[#ba1a1a]'}`}>
                                        {d.net_flow >= 0 ? `+₹${d.net_flow.toLocaleString()}` : `-₹${Math.abs(d.net_flow).toLocaleString()}`}
                                    </td>
                                    <td className="px-4 py-3 text-right font-bold text-black">
                                        ₹{d.projected_cash.toLocaleString()}
                                    </td>
                                    <td className="px-4 py-3 text-[11px] text-[#5d5f5f]" style={{ fontFamily: 'Inter, system-ui, sans-serif' }}>
                                        {d.events.length > 0 ? (
                                            <span className="text-amber-700 font-medium">{d.events.join('; ')}</span>
                                        ) : (
                                            <span className="text-[#cfc4c5]">Standard operating day</span>
                                        )}
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

import React, { useEffect, useState } from 'react';
import { StrategyOption } from '../types';
import { api } from '../services/api';

export const SimulatorView: React.FC = () => {
    const [strategies, setStrategies] = useState<StrategyOption[]>([]);
    const [loading, setLoading] = useState<boolean>(true);
    const [buffer, setBuffer] = useState<number>(200000);

    const runSim = (buf: number) => {
        setLoading(true);
        api.runSimulation(buf).then(res => {
            setStrategies(res.strategies);
            setLoading(false);
        }).catch(err => {
            console.error('Simulation failed:', err);
            setLoading(false);
        });
    };

    useEffect(() => {
        runSim(buffer);
    }, []);

    return (
        <div className="space-y-6">
            {/* Header & Buffer Control */}
            <div className="glass-panel rounded-2xl p-6 flex flex-col lg:flex-row items-start lg:items-center justify-between gap-6">
                <div>
                    <div className="flex items-center space-x-2">
                        <span className="px-2.5 py-0.5 text-xs font-bold rounded-full bg-black text-white">
                            Counterfactual Decision Simulator
                        </span>
                        <span className="text-xs text-[#5d5f5f]">Recovery vs liquidity</span>
                    </div>
                    <h2 className="text-xl font-bold text-black mt-1">Strategy simulator</h2>
                    <p className="text-xs text-[#5d5f5f] mt-0.5">
                        Compare expected financial outcomes across 4 distinct collection strategies.
                    </p>
                </div>

                {/* Safety Buffer Selector for Simulator */}
                <div className="flex items-center space-x-3 bg-[#f3f3f3] border border-[#cfc4c5]/40 rounded-xl p-3">
                    <span className="text-xs font-bold text-black">Safety buffer:</span>
                    <select
                        value={buffer}
                        onChange={(e) => {
                            const val = Number(e.target.value);
                            setBuffer(val);
                            runSim(val);
                        }}
                        className="bg-white text-xs font-bold text-black border border-[#cfc4c5] rounded-lg px-2.5 py-1 outline-none cursor-pointer"
                    >
                        <option value={150000}>₹1.5L (Aggressive)</option>
                        <option value={200000}>₹2.0L (Standard)</option>
                        <option value={300000}>₹3.0L (Conservative)</option>
                    </select>
                </div>
            </div>

            {/* Strategy Comparison Cards */}
            {loading ? (
                <div className="text-[#5d5f5f] text-sm p-6 text-center">Running simulation...</div>
            ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                    {strategies.map((strat) => {
                        const isCashpilot = strat.code === 'CASHPILOT';

                        return (
                            <div
                                key={strat.code}
                                className={`p-5 rounded-2xl border relative flex flex-col justify-between transition-all ${isCashpilot
                                        ? 'bg-white border-black shadow-lg scale-[1.02]'
                                        : 'bg-white/70 border-[#cfc4c5]'
                                    }`}
                            >
                                {isCashpilot && (
                                    <span className="absolute -top-3 left-4 bg-gradient-to-r from-cyan-500 to-emerald-500 text-slate-950 font-black text-[9px] uppercase px-2.5 py-0.5 rounded-full tracking-wider">
                                        Recommended Strategy
                                    </span>
                                )}

                                <div className="space-y-4">
                                    <div>
                                        <h3 className="font-bold text-black text-sm">{strat.name}</h3>
                                        <div className="text-2xl font-bold font-mono text-cyan-400 mt-2">
                                            ₹{(strat.net_recovery / 100000).toFixed(2)}L
                                        </div>
                                        <div className="text-[10px] text-slate-400">Net Recovered Cash</div>
                                    </div>

                                    <div className="space-y-2 border-t border-[#cfc4c5]/50 pt-3 text-xs">
                                        <div className="flex justify-between text-[#5d5f5f]">
                                            <span>Gross Recovery:</span>
                                            <span className="font-mono font-bold">₹{(strat.gross_recovery / 100000).toFixed(2)}L</span>
                                        </div>
                                        <div className="flex justify-between text-[#5d5f5f]">
                                            <span>Action Count:</span>
                                            <span className="font-mono font-bold">{strat.action_count}</span>
                                        </div>
                                        <div className="flex justify-between text-[#5d5f5f]">
                                            <span>Customer Friction:</span>
                                            <span className={`font-bold ${strat.customer_friction === 'LOW' || strat.customer_friction === 'VERY_LOW' ? 'text-emerald-400' : 'text-rose-400'}`}>
                                                {strat.customer_friction}
                                            </span>
                                        </div>
                                        <div className="flex justify-between text-[#5d5f5f]">
                                            <span>Liquidity Violations:</span>
                                            <span className={`font-mono font-bold ${strat.liquidity_violations === 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                                                {strat.liquidity_violations}
                                            </span>
                                        </div>
                                    </div>
                                </div>

                                {/* ROI Footer */}
                                <div className="mt-4 pt-3 border-t border-[#cfc4c5]/50 flex items-center justify-between">
                                    <span className="text-[11px] text-[#5d5f5f] font-medium">Estimated ROI:</span>
                                    <span className="text-sm font-bold font-mono text-emerald-400">{strat.roi}x</span>
                                </div>
                            </div>
                        );
                    })}
                </div>
            )}
        </div>
    );
};

import React, { useEffect, useState } from 'react';
import { api } from '../services/api';

export const BenchmarkView: React.FC = () => {
    const [data, setData] = useState<any>(null);
    const [loading, setLoading] = useState<boolean>(true);

    useEffect(() => {
        api.getBenchmark().then(res => {
            setData(res);
            setLoading(false);
        }).catch(err => {
            console.error('Failed to load benchmark:', err);
            setLoading(false);
        });
    }, []);

    if (loading || !data) {
        return <div className="text-slate-400 text-sm p-6 text-center">Loading Model Evaluation Metrics...</div>;
    }

    const { ml_model_metrics, decision_benchmark } = data;

    return (
        <div className="space-y-6">
            {/* Header */}
            <div className="bg-slate-900/90 border border-slate-800 rounded-2xl p-6">
                <div className="flex items-center space-x-2">
                    <span className="px-2.5 py-0.5 text-xs font-bold rounded-full bg-cyan-500/10 text-cyan-400 border border-cyan-500/20">
                        Rigorous Model Evaluation
                    </span>
                    <span className="text-xs text-slate-400">Scikit-Learn ML Metrics + Strategy Baselines</span>
                </div>
                <h2 className="text-xl font-bold text-white mt-1">Model & Strategy Benchmark Evaluation</h2>
            </div>

            {/* ML Model Performance Cards */}
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                {/* ROC AUC */}
                <div className="bg-slate-900/90 border border-slate-800 rounded-2xl p-4">
                    <div className="text-[11px] text-slate-400 font-medium">Repayment Predictor ROC-AUC</div>
                    <div className="text-2xl font-bold font-mono text-cyan-400 mt-2">
                        {ml_model_metrics.classifier_roc_auc}
                    </div>
                    <div className="text-[10px] text-emerald-400 font-semibold mt-1">High Discrimination Power</div>
                </div>

                {/* Precision */}
                <div className="bg-slate-900/90 border border-slate-800 rounded-2xl p-4">
                    <div className="text-[11px] text-slate-400 font-medium">Repayment Precision</div>
                    <div className="text-2xl font-bold font-mono text-emerald-400 mt-2">
                        {ml_model_metrics.classifier_precision}
                    </div>
                    <div className="text-[10px] text-slate-400 mt-1">Low False Recovery Alarm</div>
                </div>

                {/* Recall */}
                <div className="bg-slate-900/90 border border-slate-800 rounded-2xl p-4">
                    <div className="text-[11px] text-slate-400 font-medium">Repayment Recall</div>
                    <div className="text-2xl font-bold font-mono text-amber-400 mt-2">
                        {ml_model_metrics.classifier_recall}
                    </div>
                    <div className="text-[10px] text-slate-400 mt-1">High Risk Detection</div>
                </div>

                {/* MAE Days */}
                <div className="bg-slate-900/90 border border-slate-800 rounded-2xl p-4">
                    <div className="text-[11px] text-slate-400 font-medium">Timing MAE (Days)</div>
                    <div className="text-2xl font-bold font-mono text-cyan-300 mt-2">
                        {ml_model_metrics.regressor_mae_days}d
                    </div>
                    <div className="text-[10px] text-slate-400 mt-1">Mean Absolute Error</div>
                </div>
            </div>

            {/* Strategy Benchmark Comparison Table */}
            <div className="bg-slate-900/90 border border-slate-800 rounded-2xl p-6 space-y-4">
                <h3 className="text-sm font-bold text-white">Strategy Benchmark Comparison (Current Synthetic Dataset)</h3>
                <div className="overflow-x-auto">
                    <table className="w-full text-left text-xs text-slate-300">
                        <thead className="bg-slate-950 text-slate-400 font-semibold border-b border-slate-800 uppercase text-[10px] tracking-wider">
                            <tr>
                                <th className="px-4 py-3">Strategy Model</th>
                                <th className="px-4 py-3 text-center">Recovery Net Yield</th>
                                <th className="px-4 py-3 text-right">Net Recovered Cash</th>
                                <th className="px-4 py-3 text-center">Unnecessary Actions</th>
                                <th className="px-4 py-3 text-center">Liquidity Violations</th>
                                <th className="px-4 py-3 text-center">Human Approvals</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-800/60 font-sans">
                            {decision_benchmark.baselines.map((b: any, idx: number) => {
                                const isCashpilot = b.name.includes('CashPilot');

                                return (
                                    <tr
                                        key={idx}
                                        className={`hover:bg-slate-800/40 transition-all ${isCashpilot ? 'bg-cyan-950/20 font-bold text-white' : ''
                                            }`}
                                    >
                                        <td className="px-4 py-3">
                                            {b.name}
                                            {isCashpilot && (
                                                <span className="ml-2 text-[9px] uppercase font-bold px-2 py-0.5 rounded-full bg-cyan-500/20 text-cyan-300">
                                                    Winner
                                                </span>
                                            )}
                                        </td>
                                        <td className="px-4 py-3 text-center font-mono text-cyan-400">{b.recovery_rate}</td>
                                        <td className="px-4 py-3 text-right font-mono font-bold text-emerald-400">{b.net_recovered_cash}</td>
                                        <td className="px-4 py-3 text-center font-mono text-slate-300">{b.unnecessary_actions}</td>
                                        <td className={`px-4 py-3 text-center font-mono font-bold ${b.liquidity_violations === 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                                            {b.liquidity_violations}
                                        </td>
                                        <td className="px-4 py-3 text-center font-mono text-amber-300">{b.human_overrides}</td>
                                    </tr>
                                );
                            })}
                        </tbody>
                    </table>
                </div>
            </div>

            {decision_benchmark.forecast_metrics?.status === 'not_available' && (
                <div className="bg-slate-900/90 border border-slate-800 rounded-2xl p-5">
                    <h3 className="text-sm font-bold text-white">Forecast Backtest</h3>
                    <p className="text-xs text-slate-400 mt-2">
                        {decision_benchmark.forecast_metrics.reason}
                    </p>
                </div>
            )}
        </div>
    );
};

import React from 'react';
import { BrainCircuit, CheckCircle2, ShieldAlert, Target } from 'lucide-react';
import { AIInsights } from '../types';

interface IntelligencePanelProps {
    insights: AIInsights | null;
}

export const IntelligencePanel: React.FC<IntelligencePanelProps> = ({ insights }) => {
    if (!insights) return null;

    return (
        <section className="glass-panel rounded-xl p-6 border-l-4 border-l-cyan-500">
            <div className="flex flex-col lg:flex-row lg:items-start justify-between gap-5">
                <div className="max-w-2xl">
                    <div className="flex items-center gap-2 text-sm font-bold text-black">
                        <BrainCircuit size={18} /> CashPilot Intelligence
                    </div>
                    <p className="text-sm text-[#5d5f5f] mt-2 leading-relaxed">{insights.smart_summary}</p>
                </div>
                <div className="flex items-center gap-3 shrink-0">
                    <div className="text-right">
                        <div className="text-[10px] uppercase tracking-wider text-[#5d5f5f]">Health confidence</div>
                        <div className="text-2xl font-bold text-black">{Math.round(insights.financial_health_score)}<span className="text-sm text-[#5d5f5f]">/100</span></div>
                    </div>
                    <span className={`px-3 py-1.5 rounded-full text-[11px] font-bold ${insights.liquidity_status === 'HEALTHY' ? 'bg-emerald-50 text-emerald-700' : 'bg-amber-50 text-amber-700'}`}>
                        {insights.liquidity_status.replace('_', ' ')}
                    </span>
                </div>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-5">
                <div>
                    <div className="text-[10px] uppercase tracking-wider text-[#5d5f5f] mb-2 flex items-center gap-1"><Target size={13} /> Recommended focus</div>
                    <div className="space-y-2">
                        {insights.recommended_focus.map((item) => <div key={item} className="text-xs text-[#1b1b1b] flex gap-2"><CheckCircle2 size={14} className="text-emerald-600 shrink-0" />{item}</div>)}
                    </div>
                </div>
                <div>
                    <div className="text-[10px] uppercase tracking-wider text-[#5d5f5f] mb-2 flex items-center gap-1"><ShieldAlert size={13} /> Highest-impact decisions</div>
                    <div className="space-y-2">
                        {insights.top_actions.slice(0, 3).map((action) => <div key={action.id} className="text-xs text-[#1b1b1b] flex justify-between gap-3"><span className="truncate">{action.target_name} · {action.action_type.replace(/_/g, ' ')}</span><span className="font-bold shrink-0">{Math.round(action.confidence * 100)}%</span></div>)}
                    </div>
                </div>
            </div>
        </section>
    );
};
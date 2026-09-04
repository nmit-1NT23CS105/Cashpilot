import React from 'react';
import { PlayCircle } from 'lucide-react';
import { DemoScenario } from '../types';

const headingFont = 'Manrope, Inter, system-ui, sans-serif';

interface DemoScenariosViewProps {
    scenarios: DemoScenario[];
    activeScenarioId: string;
    onSelectScenario: (id: string) => void;
}

export const DemoScenariosView: React.FC<DemoScenariosViewProps> = ({ scenarios, activeScenarioId, onSelectScenario }) => (
    <div className="space-y-6">
        <div className="glass-panel rounded-2xl p-6">
            <h1 className="text-[24px] md:text-[30px] font-bold tracking-tight text-black" style={{ fontFamily: headingFont }}>
                Demo Scenarios
            </h1>
            <p className="text-[13px] text-[#5d5f5f] mt-1 max-w-3xl">
                Apply realistic distributor finance scenarios to test liquidity risk, payment prediction, policy enforcement, and approval behavior.
            </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-5">
            {scenarios.map((scenario) => {
                const active = scenario.id === activeScenarioId;
                return (
                    <article key={scenario.id} className={`rounded-2xl p-5 border ${active ? 'bg-black text-white border-black shadow-xl' : 'glass-panel text-black'}`}>
                        <div className="flex items-start justify-between gap-3">
                            <div>
                                <span className={`text-[10px] font-bold px-2 py-1 rounded-full ${active ? 'bg-white/15 text-white' : 'bg-[#f3f3f3] text-[#5d5f5f]'}`}>
                                    {scenario.tag}
                                </span>
                                <h2 className="text-lg font-bold mt-3 leading-tight" style={{ fontFamily: headingFont }}>{scenario.name}</h2>
                            </div>
                            {active && <span className="text-[10px] font-bold bg-emerald-400 text-black px-2 py-1 rounded-full">ACTIVE</span>}
                        </div>
                        <p className={`text-[13px] leading-relaxed mt-3 ${active ? 'text-white/70' : 'text-[#5d5f5f]'}`}>{scenario.description}</p>
                        <button
                            onClick={() => onSelectScenario(scenario.id)}
                            className={`mt-4 inline-flex items-center gap-2 rounded-xl px-4 py-2 text-[13px] font-bold ${active ? 'bg-white text-black' : 'bg-black text-white'}`}
                        >
                            <PlayCircle size={15} /> Apply Scenario
                        </button>
                    </article>
                );
            })}
        </div>
    </div>
);

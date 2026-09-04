import React, { useEffect, useState } from 'react';
import { FileSearch, Save, Settings, ShieldCheck } from 'lucide-react';
import { api } from '../services/api';
import { SettingsPayload } from '../types';

const headingFont = 'Manrope, Inter, system-ui, sans-serif';

export const SettingsView: React.FC<{ onSettingsSaved?: () => void }> = ({ onSettingsSaved }) => {
    const [settings, setSettings] = useState<SettingsPayload | null>(null);
    const [buffer, setBuffer] = useState(200000);
    const [docText, setDocText] = useState('Jio Fiber internet bill 2499 for warehouse Wi-Fi');
    const [docAmount, setDocAmount] = useState(2499);
    const [docResult, setDocResult] = useState<any>(null);
    const [promiseText, setPromiseText] = useState('I will pay Rs 40000 on Friday');
    const [promiseResult, setPromiseResult] = useState<any>(null);

    useEffect(() => {
        api.getSettings().then((response) => {
            setSettings(response);
            setBuffer(response.merchant.min_cash_buffer);
        });
    }, []);

    const saveBuffer = async () => {
        const response = await api.updateSettings(buffer);
        setSettings(response);
        onSettingsSaved?.();
    };

    const extractDocument = async () => {
        setDocResult(await api.extractDocument({ description: docText, amount: docAmount }));
    };

    const extractPromise = async () => {
        setPromiseResult(await api.extractPromiseToPay(promiseText));
    };

    if (!settings) {
        return <div className="glass-panel rounded-2xl p-8 text-center text-sm text-[#5d5f5f]">Loading settings...</div>;
    }

    return (
        <div className="space-y-6">
            <div className="glass-panel rounded-2xl p-6">
                <h1 className="text-[24px] md:text-[30px] font-bold tracking-tight text-black flex items-center gap-2" style={{ fontFamily: headingFont }}>
                    <Settings size={27} /> Settings
                </h1>
                <p className="text-[13px] text-[#5d5f5f] mt-1 max-w-3xl">
                    Configure liquidity policy, inspect guardrails, and test document/message understanding before posting anything to the ledger.
                </p>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
                <section className="glass-panel rounded-2xl p-5 space-y-4">
                    <h2 className="text-sm font-bold text-black flex items-center gap-2">
                        <ShieldCheck size={18} /> Liquidity And Policy
                    </h2>
                    <div className="bg-white/70 border border-[#cfc4c5]/40 rounded-xl p-4">
                        <div className="flex items-center justify-between mb-2">
                            <label className="text-[13px] font-bold text-black">Minimum Safe Cash Buffer</label>
                            <span className="font-mono font-bold">₹{buffer.toLocaleString()}</span>
                        </div>
                        <input
                            type="range"
                            min="100000"
                            max="500000"
                            step="10000"
                            value={buffer}
                            onChange={(event) => setBuffer(Number(event.target.value))}
                            className="w-full accent-black"
                        />
                        <button
                            onClick={saveBuffer}
                            className="mt-3 inline-flex items-center gap-2 bg-black text-white px-4 py-2 rounded-xl text-[13px] font-bold"
                        >
                            <Save size={15} /> Save Buffer
                        </button>
                    </div>

                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                        {Object.entries(settings.policy_rules).map(([key, value]) => (
                            <div key={key} className="bg-white/70 border border-[#cfc4c5]/40 rounded-xl p-4">
                                <div className="text-[10px] uppercase tracking-wider text-[#5d5f5f]">{key.replace(/_/g, ' ')}</div>
                                <div className="text-sm font-bold text-black mt-1">{String(value)}</div>
                            </div>
                        ))}
                    </div>
                </section>

                <section className="glass-panel rounded-2xl p-5 space-y-4">
                    <h2 className="text-sm font-bold text-black flex items-center gap-2">
                        <FileSearch size={18} /> Review Before Posting
                    </h2>
                    <div className="space-y-3 bg-white/70 border border-[#cfc4c5]/40 rounded-xl p-4">
                        <input
                            value={docText}
                            onChange={(event) => setDocText(event.target.value)}
                            className="w-full bg-white border border-[#cfc4c5]/40 rounded-xl px-3 py-2 text-sm outline-none focus:border-black"
                        />
                        <input
                            type="number"
                            value={docAmount}
                            onChange={(event) => setDocAmount(Number(event.target.value))}
                            className="w-full bg-white border border-[#cfc4c5]/40 rounded-xl px-3 py-2 text-sm outline-none focus:border-black"
                        />
                        <button onClick={extractDocument} className="bg-black text-white px-4 py-2 rounded-xl text-[13px] font-bold">
                            Classify Expense
                        </button>
                        {docResult && (
                            <div className="text-[12px] text-[#5d5f5f] bg-[#f3f3f3] rounded-xl p-3">
                                Category <strong className="text-black">{docResult.category}</strong>, confidence <strong>{docResult.confidence}</strong>. {docResult.message}
                            </div>
                        )}
                    </div>

                    <div className="space-y-3 bg-white/70 border border-[#cfc4c5]/40 rounded-xl p-4">
                        <textarea
                            value={promiseText}
                            onChange={(event) => setPromiseText(event.target.value)}
                            className="w-full min-h-[86px] bg-white border border-[#cfc4c5]/40 rounded-xl px-3 py-2 text-sm outline-none focus:border-black"
                        />
                        <button onClick={extractPromise} className="bg-black text-white px-4 py-2 rounded-xl text-[13px] font-bold">
                            Extract Promise
                        </button>
                        {promiseResult && (
                            <div className="text-[12px] text-[#5d5f5f] bg-[#f3f3f3] rounded-xl p-3">
                                Recommendation <strong className="text-black">{promiseResult.recommendation}</strong>; amount ₹{promiseResult.amount.toLocaleString()}; confidence {Math.round(promiseResult.confidence * 100)}%.
                            </div>
                        )}
                    </div>
                </section>
            </div>
        </div>
    );
};

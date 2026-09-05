import React, { useEffect, useRef, useState } from 'react';
import { BrainCircuit, CheckCircle2, ChevronRight, Copy, Mic, RefreshCw, SendHorizontal, ShieldCheck, Sparkles, TrendingDown, Trash2 } from 'lucide-react';
import { AIOverview } from '../types';
import { api } from '../services/api';
import { StatusScreen } from './StatusScreen';

const money = (value: number) => `₹${Math.round(value).toLocaleString()}`;
const emptyCashflow = { current_cash: 0, min_projected_cash: 0, min_cash_buffer: 0, forecast_days: 15, total_expected_inflow: 0, total_scheduled_outflow: 0, total_expected_outflow: 0, net_projected_change: 0, has_liquidity_violation: false, first_violation_day: null, max_shortfall: 0, daily_forecast: [], daily_forecasts: [] };

export const AIWorkspace: React.FC = () => {
    const [overview, setOverview] = useState<AIOverview | null>(null);
    const [scenario, setScenario] = useState({ collection_rate: 0.8, sales_change_percent: 0, expense_change_percent: 0 });
    const [scenarioResult, setScenarioResult] = useState<{ projected_cash: number; buffer_gap: number; recommendation: string } | null>(null);
    const [voiceText, setVoiceText] = useState('');
    const [voiceResult, setVoiceResult] = useState<{ intent: string; next_step: string } | null>(null);
    const [compliance, setCompliance] = useState<{ gst_readiness: number; checks: Array<{ name: string; status: string; count: number }> } | null>(null);
    const [invoiceText, setInvoiceText] = useState({ vendor: '', invoice_number: '', description: '', amount: '', tax: '' });
    const [invoiceResult, setInvoiceResult] = useState<{ confidence: number; duplicate_risk: string; warnings: string[]; recommended_action: string } | null>(null);
    const [chatInput, setChatInput] = useState('');
    const [chatMessages, setChatMessages] = useState<Array<{ id: string; sender: 'owner' | 'intelligence'; text: string; type?: string; time: string }>>([
        { id: 'welcome', sender: 'intelligence', text: 'I can check your sales, bills, costs, cash, and customer payments. Ask me what needs attention today.', time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) },
    ]);
    const [chatLoading, setChatLoading] = useState(false);
    const chatEndRef = useRef<HTMLDivElement>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');

    const loadOverview = async () => { setLoading(true); setError(''); try { const response = await api.getAIOverview(); setOverview({ ...response, cashflow: response.cashflow || emptyCashflow, agents: response.agents || [], customer_risk: response.customer_risk || [], supplier_optimization: response.supplier_optimization || [], expense_signals: response.expense_signals || [], model_quality: response.model_quality || { observed_invoice_outcomes: 0, data_quality: 0, confidence_note: 'Model evidence will appear as payment outcomes accumulate.' }, explainability: response.explainability || { method: 'Rules and historical behavior', llm_controls: 'No direct ledger mutation', human_approval: 'Required for high-value actions' } }); } catch (err) { setError(err instanceof Error ? err.message : 'Unable to load intelligence'); } finally { setLoading(false); } };
    const retrainModel = async () => {
        setLoading(true);
        setError('');
        try {
            const result = await api.retrainAIModel();
            const nextMessage = result.status === 'trained' ? `AI learned from ${result.sample_size} live business records.` : 'AI model refresh finished.';
            setChatMessages((messages) => [...messages, { id: `${Date.now()}-training`, sender: 'intelligence', text: nextMessage, time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) }]);
            await loadOverview();
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Unable to retrain model');
        } finally {
            setLoading(false);
        }
    };
    useEffect(() => { loadOverview(); }, []);
    const askIntelligence = async (question = chatInput) => {
        const trimmed = question.trim();
        if (!trimmed || chatLoading) return;
        const time = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
        setChatMessages((messages) => [...messages, { id: `${Date.now()}-owner`, sender: 'owner', text: trimmed, time }]);
        setChatInput('');
        setChatLoading(true);
        try {
            const response = await api.queryCopilot(trimmed);
            setChatMessages((messages) => [...messages, { id: `${Date.now()}-intelligence`, sender: 'intelligence', text: response.answer, type: response.type, time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) }]);
        } catch (err) {
            setChatMessages((messages) => [...messages, { id: `${Date.now()}-error`, sender: 'intelligence', text: err instanceof Error ? err.message : 'Unable to retrieve live financial intelligence.', time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) }]);
        } finally { setChatLoading(false); }
    };
    useEffect(() => { chatEndRef.current?.scrollIntoView({ behavior: 'smooth' }); }, [chatMessages, chatLoading]);
    if (loading && !overview) return <div className="glass-panel rounded-2xl p-6 text-sm text-[#5d5f5f]">Loading your business details...</div>;
    if (!overview) return <StatusScreen title="AI help is not ready" message={error || 'We could not load your business details. Please check the backend and try again.'} onAction={loadOverview} busy={loading} tone="error" />;
    if (overview.customer_risk.length === 0 && overview.action_plan.action_items.length === 0) {
        return (
            <StatusScreen
                title="No AI data yet"
                message="Add buyers, sales, or imported files to give the AI enough live business data to predict payment risk and cash needs."
                actionLabel="Refresh data"
                onAction={loadOverview}
                busy={loading}
                tone="info"
            />
        );
    }

    return <div className="space-y-6">
        <header className="glass-panel rounded-2xl p-6 border-l-4 border-l-cyan-500">
            <div className="flex flex-col md:flex-row md:items-end justify-between gap-4">
                <div><div className="flex items-center gap-2 text-sm font-bold"><BrainCircuit size={18} /> CashPilot AI</div><h1 className="text-2xl md:text-3xl font-bold mt-2">Simple business help</h1><p className="text-sm text-[#5d5f5f] mt-2 max-w-3xl">This AI checks your sales, bills, cash, buyers, and costs. It helps you know what to do next in simple words.</p></div>
                <div className="flex items-center gap-2">
                    <button onClick={loadOverview} disabled={loading} className="border border-black rounded-lg px-3 py-2 text-sm font-bold inline-flex items-center gap-2"><RefreshCw size={15} className={loading ? 'animate-spin' : ''} /> Refresh</button>
                    <button onClick={retrainModel} disabled={loading} className="bg-black text-white rounded-lg px-3 py-2 text-sm font-bold inline-flex items-center gap-2"><BrainCircuit size={15} /> Learn from live data</button>
                </div>
                <div className="text-right"><div className="text-[10px] uppercase tracking-wider text-[#5d5f5f]">Cash needed for 15 days</div><div className="text-2xl font-bold">{money(overview.cashflow.min_projected_cash)}</div></div>
            </div>
        </header>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">{overview.agents.map((agent) => <div key={agent.name} className="bg-white border border-[#d9d2ca] rounded-xl p-4"><div className="flex items-center justify-between"><span className="font-bold text-sm">{agent.name}</span><CheckCircle2 size={16} className="text-emerald-600" /></div><div className="text-xs text-[#5d5f5f] mt-2">{agent.focus}</div></div>)}</div>
        <section className="glass-panel rounded-2xl overflow-hidden">
            <div className="p-5 border-b border-[#d9d2ca] flex flex-col sm:flex-row sm:items-center justify-between gap-3"><div><h2 className="font-bold flex items-center gap-2"><BrainCircuit size={17} /> Ask CashPilot</h2><p className="text-xs text-[#5d5f5f] mt-1">Ask about money, payments, risks, and next steps. Answers are based on your live numbers.</p></div><div className="flex items-center gap-2"><span className="text-[10px] font-bold uppercase tracking-wider text-emerald-700 bg-emerald-50 px-2.5 py-1 rounded-full">Live business data</span><button onClick={() => setChatMessages([chatMessages[0]])} title="Clear conversation" aria-label="Clear conversation" className="p-2 border border-[#cfc4c5] rounded-lg"><Trash2 size={15} /></button></div></div>
            <div className="p-5 min-h-[210px] max-h-[360px] overflow-y-auto space-y-3">{chatMessages.map((message) => <div key={message.id} className={`flex ${message.sender === 'owner' ? 'justify-end' : 'justify-start'}`}><div className={`max-w-[85%] rounded-2xl px-4 py-3 text-sm leading-relaxed ${message.sender === 'owner' ? 'bg-black text-white rounded-br-sm' : 'bg-white border border-[#d9d2ca] text-[#1b1b1b] rounded-bl-sm'}`}><div className="whitespace-pre-wrap">{message.text.split(/(\*\*.*?\*\*)/g).map((part, index) => part.startsWith('**') && part.endsWith('**') ? <strong key={index}>{part.slice(2, -2)}</strong> : part)}</div><div className="mt-2 flex items-center justify-between gap-4 text-[10px] opacity-60"><span>{message.time}</span>{message.sender === 'intelligence' && <button onClick={() => navigator.clipboard?.writeText(message.text)} title="Copy response" aria-label="Copy response"><Copy size={12} /></button>}</div>{message.type && <div className="mt-2 text-[10px] uppercase tracking-wider font-bold text-cyan-700">{message.type.replace(/_/g, ' ')}</div>}</div></div>)}{chatLoading && <div className="text-xs text-[#5d5f5f]">Analyzing your ledger and cash forecast...</div>}<div ref={chatEndRef} /></div>
            <div className="px-5 pb-3 flex gap-2 overflow-x-auto no-scrollbar">{['Give me a business summary', 'Who should I collect from today?', 'What is my liquidity forecast?', 'Which supplier should I pay first?', 'What can you do?'].map((question) => <button key={question} onClick={() => askIntelligence(question)} className="shrink-0 border border-[#cfc4c5] bg-white rounded-full px-3 py-1.5 text-xs font-bold text-[#1b1b1b]">{question}</button>)}</div>
            <div className="p-4 border-t border-[#d9d2ca] bg-white/60 flex gap-2"><textarea rows={2} value={chatInput} onChange={(event) => setChatInput(event.target.value)} onKeyDown={(event) => { if (event.key === 'Enter' && !event.shiftKey) { event.preventDefault(); askIntelligence(); } }} placeholder="Ask anything about cash, collections, risk, payables, expenses, or decisions..." className="flex-1 border border-[#cfc4c5] rounded-xl px-4 py-3 text-sm outline-none focus:border-black resize-none" /><button onClick={() => askIntelligence()} disabled={chatLoading} className="bg-black text-white rounded-xl px-4 py-3 self-end inline-flex items-center gap-2 text-sm font-bold disabled:opacity-50"><SendHorizontal size={16} /> Ask</button></div>
        </section>
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
            <section className="glass-panel rounded-2xl p-5"><h2 className="font-bold flex items-center gap-2"><TrendingDown size={17} /> Customer default radar</h2><div className="space-y-3 mt-4">{overview.customer_risk.slice(0, 5).map((customer) => <div key={customer.customer_id} className="border-b border-[#d9d2ca] pb-3"><div className="flex justify-between text-sm"><span className="font-bold">{customer.customer_name}</span><span className={customer.risk_band === 'HIGH' ? 'text-red-700 font-bold' : 'text-amber-700 font-bold'}>{customer.risk_band} · {Math.round(customer.risk_score)}%</span></div><div className="text-xs text-[#5d5f5f] mt-1">{customer.factors.join(' · ')}</div></div>)}</div></section>
            <section className="glass-panel rounded-2xl p-5"><h2 className="font-bold flex items-center gap-2"><ChevronRight size={17} /> Supplier payment optimizer</h2><div className="space-y-3 mt-4">{overview.supplier_optimization.slice(0, 5).map((supplier) => <div key={supplier.payable_id} className="border-b border-[#d9d2ca] pb-3"><div className="flex justify-between text-sm"><span className="font-bold">{supplier.supplier_name}</span><span className="font-bold">{money(supplier.amount)}</span></div><div className="text-xs text-[#5d5f5f] mt-1">{supplier.recommended_action} · due in {supplier.due_in_days} days · late-risk value {money(supplier.late_penalty_value)}</div></div>)}</div></section>
        </div>
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
            <section className="glass-panel rounded-2xl p-5 lg:col-span-2"><h2 className="font-bold flex items-center gap-2"><Sparkles size={17} /> What-if cash simulator</h2><div className="grid grid-cols-1 md:grid-cols-3 gap-3 mt-4">{[['collection_rate', 'Collection rate'], ['sales_change_percent', 'Sales change %'], ['expense_change_percent', 'Expense change %']].map(([key, label]) => <label key={key} className="text-xs font-bold">{label}<input type="number" step="0.05" value={scenario[key as keyof typeof scenario]} onChange={(event) => setScenario({ ...scenario, [key]: Number(event.target.value) })} className="mt-1 w-full border rounded-lg p-2" /></label>)}</div><button onClick={() => api.runAIScenario(scenario).then(setScenarioResult)} className="mt-4 bg-black text-white rounded-lg px-4 py-2 text-sm font-bold">Run AI scenario</button>{scenarioResult && <div className="mt-4 bg-white rounded-xl border p-4 text-sm">Projected cash: <b>{money(scenarioResult.projected_cash)}</b> · buffer gap: <b>{money(scenarioResult.buffer_gap)}</b> · <b>{scenarioResult.recommendation.replace(/_/g, ' ')}</b></div>}</section>
            <section className="glass-panel rounded-2xl p-5"><h2 className="font-bold flex items-center gap-2"><Mic size={17} /> Voice-ready commands</h2><p className="text-xs text-[#5d5f5f] mt-2">Type a command now; microphone input can be connected without changing the intent engine.</p><input value={voiceText} onChange={(event) => setVoiceText(event.target.value)} placeholder="Show my risky customers" className="mt-4 w-full border rounded-lg p-2.5 text-sm" /><button onClick={() => api.resolveVoiceIntent(voiceText).then(setVoiceResult)} className="mt-2 w-full border border-black rounded-lg px-3 py-2 text-sm font-bold">Resolve command</button>{voiceResult && <div className="mt-3 text-xs bg-white border rounded-lg p-3"><b>{voiceResult.intent.replace(/_/g, ' ')}</b><p className="mt-1">{voiceResult.next_step}</p></div>}</section>
        </div>
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
            <section className="glass-panel rounded-2xl p-5"><h2 className="font-bold flex items-center gap-2"><ShieldCheck size={17} /> GST and compliance monitor</h2><div className="flex items-center gap-4 mt-4"><div className="text-3xl font-bold">{compliance ? Math.round(compliance.gst_readiness) : '--'}<span className="text-sm text-[#5d5f5f]">/100</span></div><button onClick={() => api.getAICompliance().then(setCompliance)} className="border border-black rounded-lg px-3 py-2 text-sm font-bold">Run checks</button></div>{compliance && <div className="space-y-2 mt-4">{compliance.checks.map((check) => <div key={check.name} className="flex justify-between text-xs"><span>{check.name}</span><span className={check.status === 'PASS' ? 'text-emerald-700 font-bold' : 'text-amber-700 font-bold'}>{check.status} · {check.count}</span></div>)}</div>}</section>
            <section className="glass-panel rounded-2xl p-5"><h2 className="font-bold flex items-center gap-2"><BrainCircuit size={17} /> Invoice intelligence</h2><div className="grid grid-cols-2 gap-2 mt-4">{[['vendor', 'Vendor'], ['invoice_number', 'Invoice #'], ['description', 'Description'], ['amount', 'Amount'], ['tax', 'Tax']].map(([key, label]) => <input key={key} placeholder={label} value={invoiceText[key as keyof typeof invoiceText]} onChange={(event) => setInvoiceText({ ...invoiceText, [key]: event.target.value })} className="border rounded-lg p-2 text-xs" />)}</div><button onClick={() => api.analyzeInvoice({ ...invoiceText, amount: Number(invoiceText.amount), tax: Number(invoiceText.tax) }).then(setInvoiceResult)} className="mt-3 border border-black rounded-lg px-3 py-2 text-sm font-bold">Analyze invoice</button>{invoiceResult && <div className="mt-3 text-xs"><b>{invoiceResult.recommended_action.replace(/_/g, ' ')}</b> · confidence {Math.round(invoiceResult.confidence * 100)}% · duplicate risk {invoiceResult.duplicate_risk}{invoiceResult.warnings.length > 0 && <div className="text-amber-700 mt-1">{invoiceResult.warnings.join(' · ')}</div>}</div>}</section>
        </div>
        <div className="text-xs text-[#5d5f5f] flex items-center gap-2"><ShieldCheck size={14} /> {overview.explainability.method}. {overview.explainability.llm_controls}. {overview.explainability.human_approval}.</div>
        <div className="text-xs text-[#5d5f5f]">Model evidence: {overview.model_quality.observed_invoice_outcomes} observed invoice outcomes. {overview.model_quality.confidence_note}</div>
    </div>;
};
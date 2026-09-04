import React, { useState } from 'react';
import { Bot, SendHorizontal, Sparkles } from 'lucide-react';
import { api } from '../services/api';

const headingFont = 'Manrope, Inter, system-ui, sans-serif';

interface ChatMessage {
    id: string;
    sender: 'user' | 'copilot';
    text: string;
}

export const CopilotPage: React.FC = () => {
    const [messages, setMessages] = useState<ChatMessage[]>([
        {
            id: 'welcome',
            sender: 'copilot',
            text: 'Ask a finance question. I will answer from the ledger, forecasts, receivables, payables, and action plan rather than inventing numbers.',
        },
    ]);
    const [input, setInput] = useState('');
    const [loading, setLoading] = useState(false);

    const questions = [
        'Who should I collect from today?',
        'Why is Customer B high risk?',
        'Will I have enough cash to pay Manufacturer X?',
        'What happens if I collect high-probability customers?',
        'What are my biggest expenses this month?',
    ];

    const send = async (question: string) => {
        const trimmed = question.trim();
        if (!trimmed) return;
        setMessages((current) => [...current, { id: `${Date.now()}-u`, sender: 'user', text: trimmed }]);
        setInput('');
        setLoading(true);
        try {
            const response = await api.queryCopilot(trimmed);
            setMessages((current) => [...current, { id: `${Date.now()}-c`, sender: 'copilot', text: response.answer }]);
        } catch {
            setMessages((current) => [...current, { id: `${Date.now()}-e`, sender: 'copilot', text: 'I could not retrieve the financial data for that question. Please try again.' }]);
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="space-y-6">
            <div className="glass-panel rounded-2xl p-6">
                <h1 className="text-[24px] md:text-[30px] font-bold tracking-tight text-black flex items-center gap-2" style={{ fontFamily: headingFont }}>
                    <Bot size={28} /> CashPilot Intelligence
                </h1>
                <p className="text-[13px] text-[#5d5f5f] mt-1 max-w-3xl">
                    Natural language answers backed by ledger, forecast, risk, and policy services. Intelligence explains the numbers and recommends the next action.
                </p>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-12 gap-5">
                <aside className="lg:col-span-4 glass-panel rounded-2xl p-5 space-y-3">
                    <h2 className="text-sm font-bold text-black flex items-center gap-2">
                        <Sparkles size={17} /> Suggested Questions
                    </h2>
                    {questions.map((question) => (
                        <button
                            key={question}
                            onClick={() => send(question)}
                            className="w-full text-left bg-white/70 hover:bg-white border border-[#cfc4c5]/40 rounded-xl p-3 text-[13px] font-medium text-black"
                        >
                            {question}
                        </button>
                    ))}
                </aside>

                <section className="lg:col-span-8 glass-panel rounded-2xl min-h-[560px] flex flex-col overflow-hidden">
                    <div className="flex-1 p-5 space-y-4 overflow-y-auto">
                        {messages.map((message) => (
                            <div key={message.id} className={`flex ${message.sender === 'user' ? 'justify-end' : 'justify-start'}`}>
                                <div className={`max-w-[82%] rounded-2xl p-4 text-sm leading-relaxed ${message.sender === 'user'
                                        ? 'bg-black text-white rounded-tr-sm'
                                        : 'bg-white border border-[#cfc4c5]/40 text-[#1b1b1b] rounded-tl-sm'
                                    }`}>
                                    <div dangerouslySetInnerHTML={{ __html: message.text.replace(/\n/g, '<br/>') }} />
                                </div>
                            </div>
                        ))}
                        {loading && (
                            <div className="text-[13px] text-[#5d5f5f]">Analyzing CashPilot data...</div>
                        )}
                    </div>

                    <div className="border-t border-[#cfc4c5]/30 p-4 flex gap-2 bg-white/60">
                        <input
                            value={input}
                            onChange={(event) => setInput(event.target.value)}
                            onKeyDown={(event) => event.key === 'Enter' && send(input)}
                            placeholder="Ask about cash, collections, payables, risk, or expenses"
                            className="flex-1 bg-white border border-[#cfc4c5]/40 rounded-xl px-4 py-3 text-sm outline-none focus:border-black"
                        />
                        <button
                            onClick={() => send(input)}
                            className="bg-black text-white rounded-xl px-4 py-3 inline-flex items-center gap-2 text-sm font-bold"
                        >
                            <SendHorizontal size={16} /> Send
                        </button>
                    </div>
                </section>
            </div>
        </div>
    );
};

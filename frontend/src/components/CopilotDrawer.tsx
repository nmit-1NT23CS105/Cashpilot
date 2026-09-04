import React, { useState } from 'react';
import { api } from '../services/api';

interface CopilotDrawerProps {
    isOpen: boolean;
    onClose: () => void;
}

interface ChatMessage {
    id: string;
    sender: 'user' | 'copilot';
    text: string;
    type?: string;
    data?: any;
}

export const CopilotDrawer: React.FC<CopilotDrawerProps> = ({ isOpen, onClose }) => {
    const [messages, setMessages] = useState<ChatMessage[]>([
        {
            id: '1',
            sender: 'copilot',
            text: 'Hello! I am CashPilot Intelligence. Ask me about collections, supplier timing, liquidity forecasts, customer risk, or the next best financial action.'
        }
    ]);
    const [input, setInput] = useState<string>('');
    const [loading, setLoading] = useState<boolean>(false);

    const sampleQuestions = [
        'Who should I collect from today?',
        'Why is Customer B high risk?',
        'What is my liquidity forecast for the next 15 days?',
        'Which payment link should I send today?',
        'Will I have enough cash to pay Manufacturer X?',
        'What are my biggest expenses this month?'
    ];

    const handleSend = async (questionText: string) => {
        const q = questionText || input;
        if (!q.trim()) return;

        const userMsg: ChatMessage = { id: Date.now().toString(), sender: 'user', text: q };
        setMessages((prev) => [...prev, userMsg]);
        setInput('');
        setLoading(true);

        try {
            const res = await api.queryCopilot(q);
            const copilotMsg: ChatMessage = {
                id: (Date.now() + 1).toString(),
                sender: 'copilot',
                text: res.answer,
                type: res.type,
                data: res.data
            };
            setMessages((prev) => [...prev, copilotMsg]);
        } catch (err) {
            console.error('Copilot query error:', err);
            setMessages((prev) => [
                ...prev,
                {
                    id: (Date.now() + 1).toString(),
                    sender: 'copilot',
                    text: 'Apologies, I encountered an issue retrieving financial data. Please try again.'
                }
            ]);
        } finally {
            setLoading(false);
        }
    };

    if (!isOpen) return null;

    return (
        <div className="fixed inset-0 z-50 bg-slate-950/70 backdrop-blur-sm flex justify-end">
            <div className="w-full max-w-md bg-[#0b0f19] border-l border-slate-800 h-full flex flex-col justify-between shadow-2xl">
                {/* Drawer Header */}
                <div className="p-4 border-b border-slate-800 flex items-center justify-between bg-slate-900/90">
                    <div className="flex items-center space-x-2">
                        <div className="w-8 h-8 rounded-lg bg-gradient-to-tr from-cyan-500 to-emerald-400 p-[1.5px]">
                            <div className="w-full h-full bg-[#0b0f19] rounded-[6px] flex items-center justify-center font-bold text-cyan-400 text-xs">
                                AI
                            </div>
                        </div>
                        <div>
                            <h3 className="font-bold text-white text-sm">CashPilot Intelligence</h3>
                            <span className="text-[10px] text-emerald-400 font-medium">● Online & Connected to Ledger</span>
                        </div>
                    </div>
                    <button
                        onClick={onClose}
                        className="text-slate-400 hover:text-white p-1 rounded-lg hover:bg-slate-800 transition-all text-sm font-bold cursor-pointer"
                    >
                        ✕
                    </button>
                </div>

                {/* Chat Messages Body */}
                <div className="flex-1 overflow-y-auto p-4 space-y-4 font-sans text-xs">
                    {messages.map((m) => (
                        <div
                            key={m.id}
                            className={`flex flex-col ${m.sender === 'user' ? 'items-end' : 'items-start'}`}
                        >
                            <div
                                className={`max-w-[85%] rounded-2xl p-3 leading-relaxed ${m.sender === 'user'
                                        ? 'bg-cyan-500 text-slate-950 font-medium rounded-tr-none'
                                        : 'bg-slate-900 border border-slate-800 text-slate-200 rounded-tl-none shadow-md'
                                    }`}
                            >
                                <div dangerouslySetInnerHTML={{ __html: m.text.replace(/\n/g, '<br/>') }} />
                            </div>
                        </div>
                    ))}

                    {loading && (
                        <div className="flex items-center space-x-2 text-slate-400 text-xs p-2">
                            <span className="w-2 h-2 rounded-full bg-cyan-400 animate-ping"></span>
                            <span>Intelligence is analyzing ledger & cash forecasts...</span>
                        </div>
                    )}
                </div>

                {/* Quick Question Prompts */}
                <div className="px-4 py-2 bg-slate-950 border-t border-slate-800 flex items-center gap-1.5 overflow-x-auto no-scrollbar">
                    {sampleQuestions.map((sq, idx) => (
                        <button
                            key={idx}
                            onClick={() => handleSend(sq)}
                            className="text-[10px] font-medium text-cyan-300 bg-cyan-500/10 border border-cyan-500/20 px-2.5 py-1 rounded-full whitespace-nowrap hover:bg-cyan-500/20 transition-all cursor-pointer"
                        >
                            {sq}
                        </button>
                    ))}
                </div>

                {/* Chat Input Bar */}
                <div className="p-3 border-t border-slate-800 bg-slate-900/90 flex items-center space-x-2">
                    <input
                        type="text"
                        placeholder="Ask about cash flow, risk, or payables..."
                        value={input}
                        onChange={(e) => setInput(e.target.value)}
                        onKeyDown={(e) => e.key === 'Enter' && handleSend(input)}
                        className="flex-1 bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs text-white outline-none focus:border-cyan-500/50"
                    />
                    <button
                        onClick={() => handleSend(input)}
                        className="bg-gradient-to-r from-cyan-500 to-emerald-500 text-slate-950 font-bold text-xs px-3 py-2 rounded-xl hover:from-cyan-400 hover:to-emerald-400 transition-all cursor-pointer"
                    >
                        Send
                    </button>
                </div>
            </div>
        </div>
    );
};

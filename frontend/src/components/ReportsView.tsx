import React, { useEffect, useState } from 'react';
import { Download, FileText, RefreshCw } from 'lucide-react';
import { api } from '../services/api';
import { ReportItem } from '../types';

const headingFont = 'Manrope, Inter, system-ui, sans-serif';

const formatMetric = (value: unknown): string => {
    if (typeof value === 'number') return value >= 10000 ? `₹${value.toLocaleString()}` : value.toLocaleString();
    if (typeof value === 'string') return value;
    if (value && typeof value === 'object') return Object.entries(value as Record<string, unknown>).map(([key, item]) => `${key}: ${formatMetric(item)}`).join(' | ');
    return 'Not available';
};

export const ReportsView: React.FC = () => {
    const [reports, setReports] = useState<ReportItem[]>([]);
    const [selectedId, setSelectedId] = useState<string>('');
    const [loading, setLoading] = useState(true);

    const loadReports = async () => {
        setLoading(true);
        try {
            const response = await api.getReports();
            setReports(response.reports);
            setSelectedId((current) => current || response.reports[0]?.id || '');
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        loadReports();
    }, []);

    const selected = reports.find((report) => report.id === selectedId) || reports[0];

    return (
        <div className="space-y-6">
            <div className="glass-panel rounded-2xl p-6 flex flex-col md:flex-row md:items-end justify-between gap-4">
                <div>
                    <h1 className="text-[24px] md:text-[30px] font-bold tracking-tight text-black" style={{ fontFamily: headingFont }}>
                        Reports
                    </h1>
                    <p className="text-[13px] text-[#5d5f5f] mt-1 max-w-3xl">
                        Viewable financial reports generated from the database, model outputs, decision engine, and simulation results.
                    </p>
                </div>
                <button
                    onClick={loadReports}
                    className="inline-flex items-center justify-center gap-2 bg-black text-white rounded-xl px-4 py-2 text-[13px] font-bold"
                >
                    <RefreshCw size={15} /> Refresh
                </button>
            </div>

            {loading || !selected ? (
                <div className="glass-panel rounded-2xl p-8 text-center text-sm text-[#5d5f5f]">Loading reports...</div>
            ) : (
                <div className="grid grid-cols-1 lg:grid-cols-12 gap-5">
                    <aside className="lg:col-span-4 glass-panel rounded-2xl p-3 space-y-2">
                        {reports.map((report) => (
                            <button
                                key={report.id}
                                onClick={() => setSelectedId(report.id)}
                                className={`w-full text-left rounded-xl p-4 border transition-all ${selected.id === report.id
                                        ? 'bg-black text-white border-black'
                                        : 'bg-white/70 text-black border-[#cfc4c5]/40 hover:bg-white'
                                    }`}
                            >
                                <div className="flex items-center gap-2 font-bold text-sm">
                                    <FileText size={16} />
                                    {report.title}
                                </div>
                                <div className={`text-[11px] mt-1 leading-relaxed ${selected.id === report.id ? 'text-white/70' : 'text-[#5d5f5f]'}`}>
                                    {report.summary}
                                </div>
                            </button>
                        ))}
                    </aside>

                    <section className="lg:col-span-8 glass-panel rounded-2xl p-6">
                        <div className="flex flex-col md:flex-row md:items-start justify-between gap-4 border-b border-[#cfc4c5]/30 pb-4">
                            <div>
                                <h2 className="text-xl font-bold text-black" style={{ fontFamily: headingFont }}>{selected.title}</h2>
                                <p className="text-[13px] text-[#5d5f5f] mt-1">{selected.summary}</p>
                            </div>
                            <button
                                onClick={() => window.print()}
                                className="inline-flex items-center justify-center gap-2 bg-white border border-[#cfc4c5]/40 rounded-xl px-4 py-2 text-[13px] font-bold text-black"
                            >
                                <Download size={15} /> Print
                            </button>
                        </div>

                        <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mt-5">
                            {Object.entries(selected.metrics).map(([key, value]) => (
                                <div key={key} className="bg-white/70 border border-[#cfc4c5]/40 rounded-xl p-4">
                                    <div className="text-[10px] uppercase tracking-wider text-[#5d5f5f]">{key.replace(/_/g, ' ')}</div>
                                    <div className="text-sm font-bold text-black mt-2 leading-relaxed">{formatMetric(value)}</div>
                                </div>
                            ))}
                        </div>
                    </section>
                </div>
            )}
        </div>
    );
};

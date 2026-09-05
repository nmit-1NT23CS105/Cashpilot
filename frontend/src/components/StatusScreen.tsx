import React from 'react';
import { AlertTriangle, CheckCircle2, Info, RefreshCw } from 'lucide-react';

interface StatusScreenProps {
    title: string;
    message: string;
    actionLabel?: string;
    onAction?: () => void;
    busy?: boolean;
    tone?: 'error' | 'warning' | 'success' | 'info';
}

export const StatusScreen: React.FC<StatusScreenProps> = ({
    title,
    message,
    actionLabel = 'Try again',
    onAction,
    busy = false,
    tone = 'error',
}) => {
    const palette = {
        error: { shell: 'border-red-200 bg-white', icon: 'bg-red-50 text-red-700', button: 'bg-black text-white' },
        warning: { shell: 'border-amber-200 bg-white', icon: 'bg-amber-50 text-amber-700', button: 'bg-amber-700 text-white' },
        success: { shell: 'border-emerald-200 bg-white', icon: 'bg-emerald-50 text-emerald-700', button: 'bg-emerald-700 text-white' },
        info: { shell: 'border-cyan-200 bg-white', icon: 'bg-cyan-50 text-cyan-700', button: 'bg-black text-white' },
    };

    const Icon = tone === 'success' ? CheckCircle2 : tone === 'info' ? Info : AlertTriangle;

    return (
        <main className="min-h-[280px] flex items-center justify-center p-6">
            <section role="alert" className={`w-full max-w-lg border rounded-2xl p-6 text-center shadow-sm ${palette[tone].shell}`}>
                <div className={`mx-auto w-11 h-11 rounded-full flex items-center justify-center ${palette[tone].icon}`}>
                    <Icon size={21} />
                </div>
                <h1 className="mt-4 text-lg font-bold text-[#1b1b1b]">{title}</h1>
                <p className="mt-2 text-sm leading-6 text-[#5d5f5f]">{message}</p>
                {onAction && (
                    <button
                        type="button"
                        onClick={onAction}
                        disabled={busy}
                        className={`mt-5 inline-flex items-center gap-2 rounded-lg px-4 py-2.5 text-sm font-bold disabled:opacity-50 ${palette[tone].button}`}
                    >
                        <RefreshCw size={15} className={busy ? 'animate-spin' : ''} />
                        {busy ? 'Trying again...' : actionLabel}
                    </button>
                )}
            </section>
        </main>
    );
};

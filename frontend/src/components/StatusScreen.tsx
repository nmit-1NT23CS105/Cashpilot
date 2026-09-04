import React from 'react';
import { AlertTriangle, RefreshCw } from 'lucide-react';

interface StatusScreenProps {
    title: string;
    message: string;
    actionLabel?: string;
    onAction?: () => void;
    busy?: boolean;
}

export const StatusScreen: React.FC<StatusScreenProps> = ({
    title,
    message,
    actionLabel = 'Try again',
    onAction,
    busy = false,
}) => (
    <main className="min-h-[280px] flex items-center justify-center p-6">
        <section role="alert" className="w-full max-w-lg bg-white border border-red-200 rounded-2xl p-6 text-center shadow-sm">
            <div className="mx-auto w-11 h-11 rounded-full bg-red-50 text-red-700 flex items-center justify-center">
                <AlertTriangle size={21} />
            </div>
            <h1 className="mt-4 text-lg font-bold text-[#1b1b1b]">{title}</h1>
            <p className="mt-2 text-sm leading-6 text-[#5d5f5f]">{message}</p>
            {onAction && (
                <button
                    type="button"
                    onClick={onAction}
                    disabled={busy}
                    className="mt-5 inline-flex items-center gap-2 bg-black text-white rounded-lg px-4 py-2.5 text-sm font-bold disabled:opacity-50"
                >
                    <RefreshCw size={15} className={busy ? 'animate-spin' : ''} />
                    {busy ? 'Trying again...' : actionLabel}
                </button>
            )}
        </section>
    </main>
);

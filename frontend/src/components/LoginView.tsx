import React, { useEffect, useState } from 'react';
import { LockKeyhole, UserRound } from 'lucide-react';
import { api, setAuthToken } from '../services/api';

interface LoginViewProps {
    onAuthenticated: (username: string) => void;
    setupRequired: boolean;
}

export const LoginView: React.FC<LoginViewProps> = ({ onAuthenticated, setupRequired }) => {
    const [mode, setMode] = useState<'login' | 'signup'>(setupRequired ? 'signup' : 'login');
    const [username, setUsername] = useState('');
    const [password, setPassword] = useState('');
    const [businessName, setBusinessName] = useState('');
    const [currentBalance, setCurrentBalance] = useState('200000');
    const [error, setError] = useState('');
    const [usernameMessage, setUsernameMessage] = useState('');
    const [usernameExists, setUsernameExists] = useState(false);
    const [busy, setBusy] = useState(false);

    useEffect(() => {
        if (mode !== 'signup' || username.trim().length < 3) {
            setUsernameMessage('');
            setUsernameExists(false);
            return;
        }
        let active = true;
        const timer = window.setTimeout(async () => {
            try {
                const result = await api.checkUsername(username.trim());
                if (!active) return;
                if (result.already_exists) {
                    setUsernameExists(true);
                    setUsernameMessage(`Username '${username.trim()}' already exists. Choose another username.`);
                } else {
                    setUsernameExists(false);
                    setUsernameMessage('Username is available.');
                }
            } catch {
                if (active) setUsernameMessage('Unable to check username availability.');
            }
        }, 350);
        return () => { active = false; window.clearTimeout(timer); };
    }, [mode, username]);

    const submit = async (event: React.FormEvent) => {
        event.preventDefault();
        setError('');
        if (mode === 'signup' && usernameExists) {
            setError(`Username '${username.trim()}' already exists. Choose another username.`);
            return;
        }
        setBusy(true);
        try {
            if (mode === 'signup') {
                await api.setupOwner({ username, password, business_name: businessName, current_balance: Number(currentBalance) });
                setMode('login');
                setPassword('');
                setError('Account created. Sign in to continue.');
            } else {
                const result = await api.login(username, password);
                setAuthToken(result.token);
                onAuthenticated(result.username);
            }
        } catch (err) {
            const message = err instanceof Error ? err.message : 'Unable to authenticate';
            if (mode === 'signup' && message.includes('409')) {
                if (message.toLowerCase().includes('username') && message.toLowerCase().includes('already exists')) {
                    setUsernameExists(true);
                    setUsernameMessage(`Username '${username.trim()}' already exists. Choose another username.`);
                    setError(`Username '${username.trim()}' already exists. Choose another username.`);
                } else setError(message.replace(/^API Error \d+: /, ''));
            } else {
                setError(message.replace(/^API Error \d+: /, ''));
            }
        } finally {
            setBusy(false);
        }
    };

    return (
        <main className="min-h-screen bg-[#f4f1ed] flex items-center justify-center px-4">
            <form onSubmit={submit} className="w-full max-w-md bg-white border border-[#d9d2ca] rounded-2xl p-8 shadow-xl space-y-5">
                <div>
                    <div className="w-12 h-12 rounded-xl bg-black text-white flex items-center justify-center mb-5"><LockKeyhole size={22} /></div>
                    <h1 className="text-2xl font-bold text-black">{mode === 'signup' ? 'Create owner account' : 'Owner sign in'}</h1>
                    <p className="text-sm text-[#66615d] mt-2">{mode === 'signup' ? 'Set up your business workspace.' : 'Sign in to manage CashPilot.'}</p>
                </div>
                {mode === 'signup' && <>
                    <label className="block text-sm font-medium">Company name<input required value={businessName} onChange={(e) => setBusinessName(e.target.value)} className="mt-1 w-full border rounded-lg p-3" autoComplete="organization" /></label>
                    <label className="block text-sm font-medium">Current balance (INR)<input required min="0" type="number" value={currentBalance} onChange={(e) => setCurrentBalance(e.target.value)} className="mt-1 w-full border rounded-lg p-3" /></label>
                </>}
                <label className="block text-sm font-medium">Username<input required value={username} onChange={(e) => setUsername(e.target.value)} className={`mt-1 w-full border rounded-lg p-3 ${usernameExists ? 'border-red-500 bg-red-50' : ''}`} autoComplete="username" />{mode === 'signup' && usernameMessage && <span className={`block mt-1 text-xs ${usernameExists ? 'text-red-700' : usernameMessage.includes('available') ? 'text-emerald-700' : 'text-amber-700'}`}>{usernameMessage}</span>}</label>
                <label className="block text-sm font-medium">Password<input required type="password" value={password} onChange={(e) => setPassword(e.target.value)} className="mt-1 w-full border rounded-lg p-3" autoComplete="current-password" /></label>
                {error && <p className={`text-sm rounded-lg p-3 ${error.startsWith('Account created') ? 'text-emerald-700 bg-emerald-50 border border-emerald-100' : 'text-red-700 bg-red-50 border border-red-100'}`}>{error}</p>}
                <button disabled={busy} className="w-full bg-black text-white rounded-lg py-3 font-bold disabled:opacity-50">{busy ? 'Please wait...' : mode === 'signup' ? 'Create account' : 'Sign in'}</button>
                <button type="button" onClick={() => { setMode(mode === 'login' ? 'signup' : 'login'); setError(''); }} className="w-full text-sm font-bold text-[#5d5f5f] hover:text-black">{mode === 'login' ? 'Sign up' : 'Back to sign in'}</button>
                <div className="flex items-center gap-2 text-xs text-[#66615d]"><UserRound size={14} /> Owner access only</div>
            </form>
        </main>
    );
};

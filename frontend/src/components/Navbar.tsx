import React from 'react';
import {
    Activity,
    Bot,
    ClipboardList,
    FileText,
    Gauge,
    LayoutDashboard,
    LineChart,
    ReceiptText,
    Scale,
    Settings,
    UsersRound,
    WalletCards,
} from 'lucide-react';

interface NavbarProps {
    activeTab: string;
    setActiveTab: (tab: string) => void;
    onOpenOwner: () => void;
    ownerName: string;
}

const headingFont = 'Manrope, Inter, system-ui, sans-serif';

const tabs = [
    { id: 'overview', label: 'Dashboard', icon: LayoutDashboard },
    { id: 'cashflow', label: 'Cash Flow', icon: LineChart },
    { id: 'receivables', label: 'Money to collect', icon: WalletCards },
    { id: 'customers', label: 'Customers', icon: UsersRound },
    { id: 'payables', label: 'Bills to pay', icon: ReceiptText },
    { id: 'expenses', label: 'Expenses', icon: ClipboardList },
    { id: 'ledger', label: 'Money record', icon: Scale },
    { id: 'actions', label: 'AI suggestions', icon: Activity },
    { id: 'simulator', label: 'Simulator', icon: Gauge },
    { id: 'reports', label: 'Reports', icon: FileText },
    { id: 'ai', label: 'Ask AI', icon: Bot },
    { id: 'settings', label: 'Settings', icon: Settings },
];

export const Navbar: React.FC<NavbarProps> = ({
    activeTab,
    setActiveTab,
    onOpenOwner, ownerName
}) => {
    return (
        <header className="sticky top-0 z-40 bg-white/55 backdrop-blur-xl border-b border-white/50 shadow-[0px_8px_28px_rgba(31,42,39,0.06)] px-4 md:px-10 xl:px-20 py-4 overflow-x-hidden">
            <div className="max-w-7xl mx-auto w-full min-w-0 flex flex-col xl:flex-row items-stretch xl:items-center justify-between gap-4">
                <div className="flex items-center gap-4 min-w-0 w-full xl:w-auto">
                    <span className="text-[22px] font-extrabold tracking-tight text-black whitespace-nowrap" style={{ fontFamily: headingFont }}>
                        CashPilot AI
                    </span>
                    <div className="h-6 w-px bg-[#cfc4c5] hidden xl:block" />
                    <nav className="hidden lg:flex gap-1 overflow-x-auto no-scrollbar min-w-0">
                        {tabs.map((tab) => {
                            const Icon = tab.icon;
                            return (
                                <button
                                    key={tab.id}
                                    onClick={() => setActiveTab(tab.id)}
                                    className={`flex items-center gap-1.5 px-3 py-1.5 text-[13px] font-medium rounded transition-all cursor-pointer whitespace-nowrap ${activeTab === tab.id
                                            ? 'text-black font-bold border-b-2 border-black'
                                            : 'text-[#5d5f5f] hover:bg-[#e8e8e8]/50'
                                        }`}
                                >
                                    <Icon size={16} strokeWidth={2} />
                                    <span>{tab.label}</span>
                                </button>
                            );
                        })}
                    </nav>
                </div>

                <div className="flex items-center gap-2 overflow-x-auto no-scrollbar pb-1 xl:pb-0 min-w-0 w-full xl:w-auto max-w-full">
                    <button onClick={onOpenOwner} className="border border-black text-black text-[13px] font-bold px-3 py-2 rounded-full hover:bg-black hover:text-white transition-all whitespace-nowrap">Owner: {ownerName}</button>
                </div>
            </div>

            <div className="lg:hidden max-w-7xl mx-auto w-full min-w-0 mt-3 pt-2 border-t border-[#cfc4c5]/30 flex items-center gap-1 overflow-x-auto no-scrollbar">
                {tabs.map((tab) => {
                    const Icon = tab.icon;
                    return (
                        <button
                            key={tab.id}
                            onClick={() => setActiveTab(tab.id)}
                            className={`flex items-center gap-1.5 px-3 py-2 rounded text-[13px] font-medium transition-all whitespace-nowrap cursor-pointer ${activeTab === tab.id
                                    ? 'bg-black text-white shadow-md'
                                    : 'text-[#5d5f5f] hover:bg-[#e8e8e8]/50'
                                }`}
                        >
                            <Icon size={15} strokeWidth={2} />
                            <span>{tab.label}</span>
                        </button>
                    );
                })}
            </div>
        </header>
    );
};

'use client';

import { useState, useEffect } from 'react';
import { Bell, Search, RefreshCw, ChevronDown, Sparkles } from 'lucide-react';
import { OptimizeRoutesDialog } from './optimize-routes-dialog';

export function Header() {
    const [currentTime, setCurrentTime] = useState<Date | null>(null);
    const [isRefreshing, setIsRefreshing] = useState(false);
    const [mounted, setMounted] = useState(false);
    const [showOptimizeDialog, setShowOptimizeDialog] = useState(false);

    useEffect(() => {
        setMounted(true);
        setCurrentTime(new Date());
        const timer = setInterval(() => setCurrentTime(new Date()), 1000);
        return () => clearInterval(timer);
    }, []);

    const handleRefresh = () => {
        setIsRefreshing(true);
        setTimeout(() => setIsRefreshing(false), 1000);
    };

    return (
        <>
            <header className="h-16 bg-stone-900 border-b border-stone-800 flex items-center justify-between px-6">
                {/* Left - Search */}
                <div className="flex items-center gap-4">
                    <div className="relative">
                        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-stone-500" />
                        <input
                            type="text"
                            placeholder="Search orders, drivers, routes..."
                            className="w-80 h-10 pl-10 pr-4 bg-stone-800 border border-stone-700 rounded-lg text-sm text-stone-100 placeholder-stone-500 focus:outline-none focus:ring-2 focus:ring-emerald-500/50 focus:border-emerald-500 transition-all hover:border-stone-600"
                        />
                    </div>
                </div>

                {/* Center - Status */}
                <div className="flex items-center gap-6">
                    <div className="flex items-center gap-2">
                        <div className="w-2 h-2 bg-emerald-500 rounded-full animate-pulse shadow-[0_0_10px_2px_rgba(16,185,129,0.3)]" />
                        <span className="text-sm text-stone-400">System Online</span>
                    </div>
                    <div className="h-4 w-px bg-stone-700" />
                    <div className="flex items-center gap-2 text-sm text-stone-400">
                        <span className="font-mono text-emerald-500">
                            {mounted && currentTime ? currentTime.toLocaleTimeString('en-US', {
                                hour: '2-digit',
                                minute: '2-digit',
                                second: '2-digit'
                            }) : '--:--:--'}
                        </span>
                        <span className="text-stone-600">|</span>
                        <span>
                            {mounted && currentTime ? currentTime.toLocaleDateString('en-US', {
                                weekday: 'short',
                                month: 'short',
                                day: 'numeric'
                            }) : '---'}
                        </span>
                    </div>
                </div>

                {/* Right - Actions */}
                <div className="flex items-center gap-3">
                    {/* Refresh Button */}
                    <button
                        onClick={handleRefresh}
                        className="p-2 hover:bg-stone-800 rounded-lg transition-colors group"
                    >
                        <RefreshCw className={`w-5 h-5 text-stone-400 group-hover:text-emerald-500 transition-colors ${isRefreshing ? 'animate-spin' : ''}`} />
                    </button>

                    {/* Notifications */}
                    <button className="relative p-2 hover:bg-stone-800 rounded-lg transition-colors group">
                        <Bell className="w-5 h-5 text-stone-400 group-hover:text-emerald-500 transition-colors" />
                        <span className="absolute top-1 right-1 w-2 h-2 bg-emerald-500 rounded-full shadow-lg shadow-emerald-500/50 border border-stone-900" />
                    </button>

                    {/* Date Selector */}
                    <button className="flex items-center gap-2 h-10 px-4 bg-stone-800 border border-stone-700 rounded-lg text-sm text-stone-100 hover:bg-stone-700 hover:border-stone-600 transition-colors">
                        <span>Today</span>
                        <ChevronDown className="w-4 h-4 text-stone-400" />
                    </button>

                    {/* Optimize Button */}
                    <button
                        onClick={() => setShowOptimizeDialog(true)}
                        className="flex items-center gap-2 h-10 px-4 bg-gradient-to-r from-emerald-600 to-emerald-500 rounded-lg text-sm font-semibold text-stone-900 hover:scale-105 transition-all shadow-lg shadow-emerald-900/30 border border-emerald-500/20"
                    >
                        <Sparkles className="w-4 h-4" />
                        Run Optimization
                    </button>
                </div>
            </header>

            {/* Optimization Dialog */}
            <OptimizeRoutesDialog
                isOpen={showOptimizeDialog}
                onClose={() => setShowOptimizeDialog(false)}
            />
        </>
    );
}

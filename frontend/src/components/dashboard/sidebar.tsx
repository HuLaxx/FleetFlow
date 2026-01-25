'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import {
    LayoutDashboard,
    Map,
    Truck,
    Package,
    Users,
    Settings,
    BarChart3,
    Route,
    Zap,
    ArrowLeft,
    ExternalLink,
    Home
} from 'lucide-react';
import { cn } from '@/lib/utils';

const navigation = [
    { name: 'Dashboard', href: '/demo', icon: LayoutDashboard },
    { name: 'Fleet Map', href: '/demo', icon: Map },
    { name: 'Routes', href: '/demo', icon: Route },
    { name: 'Orders', href: '/demo', icon: Package },
    { name: 'Drivers', href: '/demo', icon: Users },
    { name: 'Vehicles', href: '/demo', icon: Truck },
    { name: 'Analytics', href: '/demo', icon: BarChart3 },
    { name: 'Optimization', href: '/demo', icon: Zap },
];

const portfolioLinks = [
    { name: 'Home', href: '/', icon: Home },
    { name: 'Architecture', href: '/architecture', icon: LayoutDashboard },
    { name: 'Tech Stack', href: '/tech-stack', icon: Zap },
];

export function Sidebar() {
    const pathname = usePathname();

    return (
        <aside className="w-64 bg-stone-900 border-r border-stone-800 flex flex-col">
            {/* Back to Portfolio */}
            <div className="px-3 py-3 border-b border-stone-800">
                <Link
                    href="/"
                    className="flex items-center gap-2 px-3 py-2.5 rounded-lg text-sm font-medium bg-stone-800 text-stone-300 hover:text-emerald-400 hover:bg-stone-700 transition-all group border border-transparent hover:border-emerald-500/20"
                >
                    <ArrowLeft className="w-4 h-4 group-hover:-translate-x-0.5 transition-transform" />
                    Back to Portfolio
                </Link>
            </div>

            {/* Navigation */}
            <nav className="flex-1 px-3 py-2 space-y-1">
                {navigation.map((item, index) => {
                    const isActive = index === 0; // Dashboard is active by default
                    return (
                        <Link
                            key={item.name}
                            href={item.href}
                            className={cn(
                                'flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-all duration-200',
                                isActive
                                    ? 'bg-gradient-to-r from-emerald-900/40 to-emerald-800/20 text-emerald-500 border border-emerald-500/30 shadow-lg shadow-emerald-900/20'
                                    : 'text-stone-400 hover:text-stone-100 hover:bg-stone-800'
                            )}
                        >
                            <item.icon className={cn('w-5 h-5', isActive && 'text-emerald-500')} />
                            {item.name}
                        </Link>
                    );
                })}
            </nav>

            {/* Portfolio Links */}
            <div className="px-3 py-3 border-t border-stone-800">
                <p className="px-3 mb-2 text-[10px] text-stone-600 uppercase tracking-wider">Portfolio</p>
                {portfolioLinks.map((item) => (
                    <Link
                        key={item.name}
                        href={item.href}
                        className="flex items-center gap-2 px-3 py-2 rounded-lg text-sm text-stone-500 hover:text-emerald-200 hover:bg-stone-800 transition-colors"
                    >
                        <item.icon className="w-4 h-4" />
                        {item.name}
                        <ExternalLink className="w-3 h-3 ml-auto opacity-50" />
                    </Link>
                ))}
            </div>

            {/* User Profile */}
            <div className="px-3 py-4 border-t border-stone-800">
                <div className="flex items-center gap-3 px-3 py-2">
                    <div className="w-8 h-8 bg-gradient-to-br from-emerald-600 to-emerald-500 rounded-full flex items-center justify-center text-sm font-semibold text-stone-900 shadow-lg shadow-emerald-900/20">
                        JD
                    </div>
                    <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium text-stone-200 truncate">John Dispatcher</p>
                        <p className="text-xs text-stone-500 truncate">Demo User</p>
                    </div>
                </div>
            </div>
        </aside>
    );
}

'use client';

import { useState, useEffect } from 'react';
import {
    AlertTriangle,
    AlertCircle,
    Info,
    X,
    Bell,
    Clock,
    Truck,
    MapPin,
    CheckCircle
} from 'lucide-react';

interface Alert {
    id: string;
    type: 'warning' | 'error' | 'info' | 'success';
    title: string;
    message: string;
    timestamp: Date;
    source?: string;
    actionLabel?: string;
    dismissed?: boolean;
}

const iconMap = {
    warning: AlertTriangle,
    error: AlertCircle,
    info: Info,
    success: CheckCircle,
};

const colorMap = {
    warning: {
        bg: 'bg-amber-500/10',
        border: 'border-amber-500/30',
        icon: 'text-amber-400',
        title: 'text-amber-300',
    },
    error: {
        bg: 'bg-red-500/10',
        border: 'border-red-500/30',
        icon: 'text-red-400',
        title: 'text-red-300',
    },
    info: {
        bg: 'bg-blue-500/10',
        border: 'border-blue-500/30',
        icon: 'text-blue-400',
        title: 'text-blue-300',
    },
    success: {
        bg: 'bg-emerald-500/10',
        border: 'border-emerald-500/30',
        icon: 'text-emerald-400',
        title: 'text-emerald-300',
    },
};

// Mock alerts - in production, these would come from WebSocket
const generateMockAlerts = (): Alert[] => [
    {
        id: '1',
        type: 'warning',
        title: 'Driver Running Late',
        message: 'Marcus J. is 15 minutes behind schedule for stop #5',
        timestamp: new Date(Date.now() - 2 * 60 * 1000),
        source: 'ETA Monitor',
    },
    {
        id: '2',
        type: 'error',
        title: 'Delivery Failed',
        message: 'ORD-2851 failed: Customer not available',
        timestamp: new Date(Date.now() - 5 * 60 * 1000),
        source: 'Driver App',
        actionLabel: 'Reschedule',
    },
    {
        id: '3',
        type: 'info',
        title: 'High Demand Zone',
        message: 'Unusual order volume detected in Brooklyn area',
        timestamp: new Date(Date.now() - 10 * 60 * 1000),
        source: 'Hotspot Detection',
    },
    {
        id: '4',
        type: 'success',
        title: 'Route Optimized',
        message: 'Route R-2847 optimized, saving 12 minutes',
        timestamp: new Date(Date.now() - 15 * 60 * 1000),
        source: 'Optimization Engine',
    },
    {
        id: '5',
        type: 'warning',
        title: 'Traffic Alert',
        message: 'Heavy congestion on I-278, affecting 3 routes',
        timestamp: new Date(Date.now() - 20 * 60 * 1000),
        source: 'Traffic Monitor',
    },
];

function formatTimeAgo(date: Date): string {
    const seconds = Math.floor((Date.now() - date.getTime()) / 1000);

    if (seconds < 60) return 'Just now';
    if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
    if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ago`;
    return `${Math.floor(seconds / 86400)}d ago`;
}

function AlertItem({
    alert,
    onDismiss
}: {
    alert: Alert;
    onDismiss: () => void;
}) {
    const Icon = iconMap[alert.type];
    const colors = colorMap[alert.type];

    return (
        <div className={`p-3 rounded-lg border ${colors.bg} ${colors.border} transition-all hover:scale-[1.01]`}>
            <div className="flex items-start gap-3">
                <Icon className={`w-5 h-5 mt-0.5 flex-shrink-0 ${colors.icon}`} />

                <div className="flex-1 min-w-0">
                    <div className="flex items-start justify-between gap-2">
                        <p className={`font-medium text-sm ${colors.title}`}>{alert.title}</p>
                        <button
                            onClick={(e) => { e.stopPropagation(); onDismiss(); }}
                            className="p-0.5 hover:bg-zinc-700 rounded"
                        >
                            <X className="w-3.5 h-3.5 text-zinc-500" />
                        </button>
                    </div>

                    <p className="text-xs text-zinc-400 mt-1">{alert.message}</p>

                    <div className="flex items-center justify-between mt-2">
                        <div className="flex items-center gap-2 text-[10px] text-zinc-500">
                            <span>{alert.source}</span>
                            <span>•</span>
                            <span>{formatTimeAgo(alert.timestamp)}</span>
                        </div>

                        {alert.actionLabel && (
                            <button className="text-xs text-emerald-400 hover:text-emerald-300 font-medium">
                                {alert.actionLabel}
                            </button>
                        )}
                    </div>
                </div>
            </div>
        </div>
    );
}

export default function AlertsSidebar() {
    const [alerts, setAlerts] = useState<Alert[]>([]);
    const [filter, setFilter] = useState<string>('all');

    useEffect(() => {
        setAlerts(generateMockAlerts());
    }, []);

    const dismissAlert = (id: string) => {
        setAlerts(prev => prev.filter(a => a.id !== id));
    };

    const clearAll = () => {
        setAlerts([]);
    };

    const filteredAlerts = filter === 'all'
        ? alerts
        : alerts.filter(a => a.type === filter);

    const counts = {
        all: alerts.length,
        warning: alerts.filter(a => a.type === 'warning').length,
        error: alerts.filter(a => a.type === 'error').length,
        info: alerts.filter(a => a.type === 'info').length,
    };

    return (
        <div className="h-full flex flex-col bg-zinc-900 border-l border-zinc-800">
            {/* Header */}
            <div className="p-4 border-b border-zinc-800">
                <div className="flex items-center justify-between mb-3">
                    <h2 className="text-lg font-semibold text-zinc-100 flex items-center gap-2">
                        <Bell className="w-5 h-5 text-emerald-400" />
                        Alerts
                        {alerts.length > 0 && (
                            <span className="px-1.5 py-0.5 bg-red-500 text-white text-xs rounded-full">
                                {alerts.length}
                            </span>
                        )}
                    </h2>

                    {alerts.length > 0 && (
                        <button
                            onClick={clearAll}
                            className="text-xs text-zinc-500 hover:text-zinc-300"
                        >
                            Clear all
                        </button>
                    )}
                </div>

                {/* Filter tabs */}
                <div className="flex gap-1">
                    {[
                        { key: 'all', label: 'All', count: counts.all },
                        { key: 'error', label: 'Errors', count: counts.error },
                        { key: 'warning', label: 'Warnings', count: counts.warning },
                    ].map(({ key, label, count }) => (
                        <button
                            key={key}
                            onClick={() => setFilter(key)}
                            className={`px-2 py-1 text-xs rounded transition-colors ${filter === key
                                    ? 'bg-zinc-700 text-zinc-100'
                                    : 'text-zinc-500 hover:text-zinc-300'
                                }`}
                        >
                            {label} {count > 0 && `(${count})`}
                        </button>
                    ))}
                </div>
            </div>

            {/* Alerts list */}
            <div className="flex-1 overflow-auto p-4 space-y-2">
                {filteredAlerts.length === 0 ? (
                    <div className="flex flex-col items-center justify-center h-full text-zinc-500">
                        <CheckCircle className="w-12 h-12 mb-3 opacity-30" />
                        <p className="text-sm">No alerts</p>
                        <p className="text-xs">All systems operational</p>
                    </div>
                ) : (
                    filteredAlerts.map((alert) => (
                        <AlertItem
                            key={alert.id}
                            alert={alert}
                            onDismiss={() => dismissAlert(alert.id)}
                        />
                    ))
                )}
            </div>

            {/* Quick stats */}
            <div className="p-4 border-t border-zinc-800">
                <div className="grid grid-cols-3 gap-2 text-center">
                    <div className="bg-zinc-800 rounded p-2">
                        <div className="flex items-center justify-center gap-1">
                            <Truck className="w-3 h-3 text-emerald-400" />
                            <span className="text-sm font-medium text-zinc-100">8</span>
                        </div>
                        <p className="text-[10px] text-zinc-500">Active</p>
                    </div>
                    <div className="bg-zinc-800 rounded p-2">
                        <div className="flex items-center justify-center gap-1">
                            <Clock className="w-3 h-3 text-amber-400" />
                            <span className="text-sm font-medium text-zinc-100">2</span>
                        </div>
                        <p className="text-[10px] text-zinc-500">Late</p>
                    </div>
                    <div className="bg-zinc-800 rounded p-2">
                        <div className="flex items-center justify-center gap-1">
                            <MapPin className="w-3 h-3 text-cyan-400" />
                            <span className="text-sm font-medium text-zinc-100">23</span>
                        </div>
                        <p className="text-[10px] text-zinc-500">Pending</p>
                    </div>
                </div>
            </div>
        </div>
    );
}

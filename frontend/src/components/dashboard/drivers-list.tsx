'use client';

import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { MapPin, Star, ChevronRight } from 'lucide-react';
import { cn } from '@/lib/utils';
import { useDriverUpdates } from '@/hooks/use-websocket';
import { trpc } from '@/lib/trpc';

const statusConfig = {
    available: { label: 'Available', color: 'bg-teal-500', textColor: 'text-teal-400' },
    on_route: { label: 'On Route', color: 'bg-emerald-500', textColor: 'text-emerald-400' },
    on_break: { label: 'On Break', color: 'bg-stone-500', textColor: 'text-stone-400' },
    offline: { label: 'Offline', color: 'bg-stone-700', textColor: 'text-stone-500' },
} as const;

export function DriversList() {
    const [selectedStatus, setSelectedStatus] = useState<string | null>(null);

    // Fetch drivers from tRPC (real PostgreSQL data)
    const { data: driversData, isLoading } = trpc.drivers.getAll.useQuery({
        limit: 20
    });

    // Listen for real-time driver status updates
    const { drivers: liveUpdates } = useDriverUpdates();

    // Use real data
    const drivers = driversData || [];

    // Apply filter
    const filteredDrivers = selectedStatus
        ? drivers.filter((d: any) => d.status === selectedStatus)
        : drivers;

    if (isLoading) {
        return (
            <div className="h-full bg-stone-900 border border-stone-800 rounded-xl flex items-center justify-center">
                <div className="text-stone-500">Loading drivers...</div>
            </div>
        );
    }

    return (
        <div className="h-full bg-stone-900 border border-stone-800 rounded-xl flex flex-col">
            {/* Header */}
            <div className="p-4 border-b border-stone-800">
                <div className="flex items-center justify-between mb-3">
                    <h2 className="text-lg font-semibold text-stone-100">Active Drivers</h2>
                    <span className="text-xs text-stone-500">{drivers.length} total</span>
                </div>

                {/* Status Filters */}
                <div className="flex gap-2 flex-wrap">
                    {Object.entries(statusConfig).map(([key, config]) => (
                        <button
                            key={key}
                            onClick={() => setSelectedStatus(selectedStatus === key ? null : key)}
                            className={cn(
                                'px-2 py-1 text-xs rounded-md transition-colors',
                                selectedStatus === key
                                    ? `${config.color} text-stone-900 font-medium`
                                    : 'bg-stone-800 text-stone-400 hover:bg-stone-700'
                            )}
                        >
                            {config.label}
                        </button>
                    ))}
                </div>
            </div>

            {/* Drivers List */}
            <div className="flex-1 overflow-y-auto p-2 space-y-2">
                <AnimatePresence>
                    {filteredDrivers.length === 0 ? (
                        <div className="flex items-center justify-center h-full text-stone-500">
                            No drivers found
                        </div>
                    ) : (
                        filteredDrivers.map((driver: any, index: number) => {
                            const initials = driver.name
                                ? driver.name.split(' ').map((n: string) => n[0]).join('')
                                : 'DR';

                            return (
                                <motion.div
                                    key={driver.id}
                                    initial={{ opacity: 0, x: 20 }}
                                    animate={{ opacity: 1, x: 0 }}
                                    exit={{ opacity: 0, x: -20 }}
                                    transition={{ delay: index * 0.05 }}
                                    className="p-3 bg-stone-800/40 hover:bg-stone-800 rounded-lg cursor-pointer transition-colors group border border-transparent hover:border-emerald-500/20"
                                >
                                    <div className="flex items-start gap-3">
                                        {/* Avatar */}
                                        <div className="relative">
                                            <div className="w-10 h-10 bg-gradient-to-br from-emerald-600 to-emerald-500 rounded-full flex items-center justify-center text-sm font-semibold text-stone-900 shadow-md">
                                                {initials}
                                            </div>
                                            <div
                                                className={cn(
                                                    'absolute -bottom-0.5 -right-0.5 w-3 h-3 rounded-full border-2 border-stone-900',
                                                    statusConfig[driver.status as keyof typeof statusConfig]?.color || 'bg-stone-500'
                                                )}
                                            />
                                        </div>

                                        {/* Info */}
                                        <div className="flex-1 min-w-0">
                                            <div className="flex items-center justify-between">
                                                <p className="text-sm font-medium text-stone-100 truncate group-hover:text-emerald-400 transition-colors">
                                                    {driver.name || `Driver #${driver.employee_id}`}
                                                </p>
                                                <div className="flex items-center gap-1">
                                                    <Star className="w-3 h-3 text-emerald-500 fill-emerald-500" />
                                                    <span className="text-xs text-stone-400">
                                                        {driver.rating == null ? 'Unrated' : Number(driver.rating).toFixed(1)}
                                                    </span>
                                                </div>
                                            </div>

                                            <p className="text-xs text-stone-500 mt-0.5">
                                                {driver.vehicle?.vehicle_number || 'No vehicle assigned'}
                                            </p>

                                            <div className="flex items-center gap-3 mt-2">
                                                <div className="flex items-center gap-1 text-xs text-stone-400">
                                                    <MapPin className="w-3 h-3" />
                                                    <span className="truncate">
                                                        {driver.depot?.name || 'No depot'}
                                                    </span>
                                                </div>
                                                <span className={cn(
                                                    'text-xs px-2 py-0.5 rounded-full',
                                                    statusConfig[driver.status as keyof typeof statusConfig]?.textColor || 'text-stone-400'
                                                )}>
                                                    {statusConfig[driver.status as keyof typeof statusConfig]?.label || driver.status}
                                                </span>
                                            </div>
                                        </div>

                                        {/* Arrow */}
                                        <ChevronRight className="w-4 h-4 text-stone-600 group-hover:text-emerald-400 transition-colors" />
                                    </div>
                                </motion.div>
                            );
                        })
                    )}
                </AnimatePresence>
            </div>
        </div>
    );
}

'use client';

import { Package, Truck, Route, Clock, TrendingUp, TrendingDown } from 'lucide-react';
import { motion } from 'framer-motion';
import { trpc } from '@/lib/trpc';

const iconColorMap = {
    orders: { color: 'from-amber-500 to-amber-400', icon: Package },
    drivers: { color: 'from-orange-600 to-orange-500', icon: Truck },
    routes: { color: 'from-yellow-600 to-yellow-500', icon: Route },
    avgDelivery: { color: 'from-stone-600 to-stone-500', icon: Clock },
};

export function StatsCards() {
    // Fetch real stats from tRPC
    const { data: orderStats } = trpc.orders.getStats.useQuery();
    const { data: driverStats } = trpc.drivers.getStats.useQuery();
    const { data: routeStats } = trpc.routes.getStats.useQuery();
    const { data: vehicleStats } = trpc.vehicles.getStats.useQuery();

    const stats = [
        {
            name: 'Active Orders',
            value: orderStats?.total_active || 0,
            change: '+12%',
            trend: 'up' as const,
            ...iconColorMap.orders,
        },
        {
            name: 'Active Drivers',
            value: driverStats?.active_count || 0,
            change: driverStats?.availability_percentage
                ? `${Math.round(driverStats.availability_percentage)}%`
                : '0%',
            trend: 'neutral' as const,
            ...iconColorMap.drivers,
        },
        {
            name: 'Routes Today',
            value: routeStats?.routes_in_progress || 0,
            change: '+5%',
            trend: 'up' as const,
            ...iconColorMap.routes,
        },
        {
            name: 'Avg. Delivery',
            value: routeStats?.avg_stop_time_minutes
                ? `${Math.round(routeStats.avg_stop_time_minutes)}m`
                : 'N/A',
            change: '-8%',
            trend: 'down' as const,
            ...iconColorMap.avgDelivery,
        },
    ];

    return (
        <div className="grid grid-cols-2 gap-4">
            {stats.map((stat, index) => (
                <motion.div
                    key={stat.name}
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: index * 0.1 }}
                    className="bg-stone-900 border border-stone-800 rounded-xl p-4 hover:border-amber-500/20 transition-all shadow-sm hover:shadow-md"
                >
                    <div className="flex items-start justify-between">
                        <div className={`p-2 rounded-lg bg-gradient-to-br ${stat.color} shadow-lg shadow-black/20`}>
                            <stat.icon className="w-4 h-4 text-stone-900" />
                        </div>
                        <div className="flex items-center gap-1 text-xs">
                            {stat.trend === 'up' && <TrendingUp className="w-3 h-3 text-amber-500" />}
                            {stat.trend === 'down' && <TrendingDown className="w-3 h-3 text-amber-500" />}
                            <span className={stat.trend === 'up' ? 'text-amber-500' : stat.trend === 'down' ? 'text-amber-500' : 'text-stone-500'}>
                                {stat.change}
                            </span>
                        </div>
                    </div>
                    <div className="mt-3">
                        <p className="text-2xl font-bold text-stone-100">{stat.value}</p>
                        <p className="text-xs text-stone-500 mt-1">{stat.name}</p>
                    </div>
                </motion.div>
            ))}
        </div>
    );
}

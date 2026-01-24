'use client';

import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Package, Clock, MapPin, AlertTriangle, Filter } from 'lucide-react';
import { cn } from '@/lib/utils';
import { useOrderUpdates } from '@/hooks/use-websocket';
import { trpc } from '@/lib/trpc';

const statusConfig = {
    pending: { label: 'Pending', color: 'bg-stone-500', borderColor: 'border-stone-500' },
    assigned: { label: 'Assigned', color: 'bg-orange-600', borderColor: 'border-orange-600' },
    in_transit: { label: 'In Transit', color: 'bg-amber-600', borderColor: 'border-amber-600' },
    delayed: { label: 'Delayed', color: 'bg-red-800', borderColor: 'border-red-800' },
    delivered: { label: 'Delivered', color: 'bg-yellow-600', borderColor: 'border-yellow-600' },
} as const;

export function OrdersPanel() {
    const [filter, setFilter] = useState<string | null>(null);

    // Fetch orders from tRPC (real PostgreSQL data)
    const { data: ordersData, isLoading, refetch } = trpc.orders.getAll.useQuery({
        limit: 50
    });

    // Listen for real-time order updates
    const { orders: liveUpdates } = useOrderUpdates();

    // Merge static data with live updates
    const orders = ordersData || [];

    // Apply filter
    const filteredOrders = filter
        ? orders.filter((o: any) => o.status === filter)
        : orders;

    // Calculate stats dynamically from real data
    const stats = {
        pending: orders.filter((o: any) => o.status === 'pending').length,
        in_transit: orders.filter((o: any) => o.status === 'in_transit').length,
        delayed: orders.filter((o: any) => o.status === 'delayed').length,
        delivered: orders.filter((o: any) => o.status === 'delivered').length,
    };

    if (isLoading) {
        return (
            <div className="flex-1 bg-stone-900 border border-stone-800 rounded-xl flex items-center justify-center">
                <div className="text-stone-500">Loading orders...</div>
            </div>
        );
    }

    return (
        <div className="flex-1 bg-stone-900 border border-stone-800 rounded-xl flex flex-col overflow-hidden">
            {/* Header */}
            <div className="p-4 border-b border-stone-800">
                <div className="flex items-center justify-between mb-3">
                    <h2 className="text-lg font-semibold text-stone-100">Today's Orders</h2>
                    <button
                        onClick={() => refetch()}
                        className="p-1.5 hover:bg-stone-800 rounded-md transition-colors"
                        title="Refresh orders"
                    >
                        <Filter className="w-4 h-4 text-stone-400" />
                    </button>
                </div>

                {/* Quick Stats */}
                <div className="grid grid-cols-4 gap-2">
                    {[
                        { label: 'Pending', count: stats.pending, color: 'text-stone-400' },
                        { label: 'In Transit', count: stats.in_transit, color: 'text-amber-500' },
                        { label: 'Delayed', count: stats.delayed, color: 'text-orange-600' },
                        { label: 'Delivered', count: stats.delivered, color: 'text-yellow-600' },
                    ].map((stat) => (
                        <button
                            key={stat.label}
                            onClick={() => setFilter(filter === stat.label.toLowerCase().replace(' ', '_') ? null : stat.label.toLowerCase().replace(' ', '_'))}
                            className={cn(
                                "text-center p-2 bg-stone-800/50 hover:bg-stone-800 rounded-lg transition-colors border border-transparent hover:border-stone-700",
                                filter === stat.label.toLowerCase().replace(' ', '_') && "bg-stone-800 border-stone-600"
                            )}
                        >
                            <p className={cn('text-lg font-bold', stat.color)}>{stat.count}</p>
                            <p className="text-[10px] text-stone-500 uppercase">{stat.label}</p>
                        </button>
                    ))}
                </div>
            </div>

            {/* Orders List */}
            <div className="flex-1 overflow-y-auto p-2 space-y-2">
                <AnimatePresence>
                    {filteredOrders.length === 0 ? (
                        <div className="flex items-center justify-center h-full text-stone-500">
                            No orders found
                        </div>
                    ) : (
                        filteredOrders.map((order: any, index: number) => (
                            <motion.div
                                key={order.id}
                                initial={{ opacity: 0, y: 10 }}
                                animate={{ opacity: 1, y: 0 }}
                                exit={{ opacity: 0, y: -10 }}
                                transition={{ delay: index * 0.03 }}
                                className={cn(
                                    'p-3 bg-stone-800/40 hover:bg-stone-800 rounded-lg cursor-pointer transition-colors group border-l-2 border-transparent hover:border-l-amber-500',
                                    statusConfig[order.status as keyof typeof statusConfig]?.borderColor
                                )}
                            >
                                <div className="flex items-start justify-between">
                                    <div className="flex-1 min-w-0">
                                        <div className="flex items-center gap-2">
                                            <span className="text-sm font-mono font-medium text-stone-100 group-hover:text-amber-400 transition-colors">
                                                {order.order_number || `ORD-${order.id.slice(0, 8)}`}
                                            </span>
                                            {order.priority > 2 && (
                                                <span className={cn(
                                                    'text-[10px] px-1.5 py-0.5 rounded uppercase font-semibold',
                                                    order.priority >= 4 ? 'bg-orange-500/10 text-orange-500' : 'bg-amber-500/10 text-amber-500'
                                                )}>
                                                    {order.priority >= 4 ? 'URGENT' : 'HIGH'}
                                                </span>
                                            )}
                                        </div>
                                        <p className="text-xs text-stone-400 mt-1 truncate">
                                            {order.customer?.name || 'Unknown Customer'}
                                        </p>
                                    </div>
                                    <span className={cn(
                                        'text-[10px] px-2 py-0.5 rounded-full uppercase font-medium',
                                        order.status === 'delayed' ? 'bg-red-900/20 text-red-500' :
                                            order.status === 'in_transit' ? 'bg-amber-900/20 text-amber-500' :
                                                order.status === 'assigned' ? 'bg-orange-900/20 text-orange-500' :
                                                    'bg-stone-700 text-stone-400'
                                    )}>
                                        {statusConfig[order.status as keyof typeof statusConfig]?.label || order.status}
                                    </span>
                                </div>

                                <div className="flex items-center gap-4 mt-2 text-xs text-stone-500">
                                    <div className="flex items-center gap-1">
                                        <MapPin className="w-3 h-3" />
                                        <span className="truncate max-w-[120px]">
                                            {order.delivery_address || 'N/A'}
                                        </span>
                                    </div>
                                    <div className="flex items-center gap-1">
                                        <Clock className="w-3 h-3" />
                                        <span>
                                            {order.time_window_start ? new Date(order.time_window_start).toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' }) : 'N/A'}
                                        </span>
                                    </div>
                                </div>

                                {order.status === 'delayed' && (
                                    <div className="flex items-center gap-1 mt-2 text-xs text-orange-500">
                                        <AlertTriangle className="w-3 h-3" />
                                        <span>Behind schedule</span>
                                    </div>
                                )}
                            </motion.div>
                        ))
                    )}
                </AnimatePresence>
            </div>
        </div>
    );
}

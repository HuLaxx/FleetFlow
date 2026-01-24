'use client';

import { useState } from 'react';
import {
    User,
    Truck,
    Clock,
    MapPin,
    Phone,
    Star,
    CheckCircle,
    Circle,
    ArrowRight,
    Zap
} from 'lucide-react';

interface Driver {
    id: string;
    name: string;
    status: 'available' | 'on_route' | 'on_break' | 'offline';
    vehicleId: string;
    vehicleType: string;
    currentLocation: string;
    rating: number;
    completedToday: number;
    remainingStops: number;
    phone: string;
}

interface PendingOrder {
    id: string;
    orderNumber: string;
    address: string;
    timeWindow: string;
    priority: 'normal' | 'high' | 'urgent';
    weight: number;
}

const mockDrivers: Driver[] = [
    {
        id: 'd1',
        name: 'Marcus Johnson',
        status: 'available',
        vehicleId: 'V-102',
        vehicleType: 'Van',
        currentLocation: 'Midtown Hub',
        rating: 4.9,
        completedToday: 12,
        remainingStops: 0,
        phone: '+1 (555) 123-4567',
    },
    {
        id: 'd2',
        name: 'Sarah Chen',
        status: 'on_route',
        vehicleId: 'V-108',
        vehicleType: 'Truck',
        currentLocation: 'En route to Brooklyn',
        rating: 4.7,
        completedToday: 8,
        remainingStops: 5,
        phone: '+1 (555) 234-5678',
    },
    {
        id: 'd3',
        name: 'James Williams',
        status: 'on_break',
        vehicleId: 'V-115',
        vehicleType: 'Van',
        currentLocation: 'Queens Depot',
        rating: 4.8,
        completedToday: 15,
        remainingStops: 0,
        phone: '+1 (555) 345-6789',
    },
];

const mockPendingOrders: PendingOrder[] = [
    { id: 'o1', orderNumber: 'ORD-3001', address: '123 Broadway, Manhattan', timeWindow: '2:00 PM - 4:00 PM', priority: 'urgent', weight: 8.5 },
    { id: 'o2', orderNumber: 'ORD-3002', address: '456 Park Ave, Manhattan', timeWindow: '3:00 PM - 5:00 PM', priority: 'high', weight: 12.0 },
    { id: 'o3', orderNumber: 'ORD-3003', address: '789 5th Ave, Manhattan', timeWindow: '4:00 PM - 6:00 PM', priority: 'normal', weight: 5.2 },
];

const statusConfig = {
    available: { label: 'Available', color: 'bg-emerald-500', textColor: 'text-emerald-400' },
    on_route: { label: 'On Route', color: 'bg-blue-500', textColor: 'text-blue-400' },
    on_break: { label: 'On Break', color: 'bg-amber-500', textColor: 'text-amber-400' },
    offline: { label: 'Offline', color: 'bg-zinc-500', textColor: 'text-zinc-400' },
};

const priorityColor = {
    normal: 'border-zinc-600',
    high: 'border-amber-500',
    urgent: 'border-red-500',
};

function DriverCard({
    driver,
    isSelected,
    onSelect
}: {
    driver: Driver;
    isSelected: boolean;
    onSelect: () => void;
}) {
    const status = statusConfig[driver.status];

    return (
        <div
            onClick={onSelect}
            className={`p-4 rounded-lg border cursor-pointer transition-all ${isSelected
                    ? 'border-emerald-500 bg-emerald-500/10'
                    : 'border-zinc-700 bg-zinc-800/50 hover:border-zinc-600'
                }`}
        >
            <div className="flex items-start justify-between mb-3">
                <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-full bg-zinc-700 flex items-center justify-center">
                        <User className="w-5 h-5 text-zinc-400" />
                    </div>
                    <div>
                        <p className="font-medium text-zinc-100">{driver.name}</p>
                        <div className="flex items-center gap-2 text-xs text-zinc-500">
                            <Truck className="w-3 h-3" />
                            <span>{driver.vehicleId} • {driver.vehicleType}</span>
                        </div>
                    </div>
                </div>
                <div className={`flex items-center gap-1.5 px-2 py-1 rounded text-xs font-medium ${status.textColor} bg-zinc-800`}>
                    <div className={`w-1.5 h-1.5 rounded-full ${status.color}`} />
                    {status.label}
                </div>
            </div>

            <div className="grid grid-cols-3 gap-2 text-center">
                <div className="bg-zinc-800 rounded p-2">
                    <div className="flex items-center justify-center gap-1 text-amber-400">
                        <Star className="w-3 h-3 fill-current" />
                        <span className="text-sm font-medium">{driver.rating}</span>
                    </div>
                    <p className="text-[10px] text-zinc-500 mt-0.5">Rating</p>
                </div>
                <div className="bg-zinc-800 rounded p-2">
                    <p className="text-sm font-medium text-emerald-400">{driver.completedToday}</p>
                    <p className="text-[10px] text-zinc-500 mt-0.5">Completed</p>
                </div>
                <div className="bg-zinc-800 rounded p-2">
                    <p className="text-sm font-medium text-cyan-400">{driver.remainingStops}</p>
                    <p className="text-[10px] text-zinc-500 mt-0.5">Remaining</p>
                </div>
            </div>

            <div className="mt-3 flex items-center gap-1.5 text-xs text-zinc-500">
                <MapPin className="w-3 h-3" />
                <span>{driver.currentLocation}</span>
            </div>
        </div>
    );
}

function OrderCard({ order }: { order: PendingOrder }) {
    return (
        <div className={`p-3 rounded-lg border-l-2 bg-zinc-800/50 ${priorityColor[order.priority]}`}>
            <div className="flex items-center justify-between mb-2">
                <p className="font-medium text-zinc-100 text-sm">{order.orderNumber}</p>
                <span className={`text-xs px-1.5 py-0.5 rounded ${order.priority === 'urgent' ? 'bg-red-500/20 text-red-400' :
                        order.priority === 'high' ? 'bg-amber-500/20 text-amber-400' :
                            'bg-zinc-700 text-zinc-400'
                    }`}>
                    {order.priority.toUpperCase()}
                </span>
            </div>
            <p className="text-xs text-zinc-400 mb-1">{order.address}</p>
            <div className="flex items-center justify-between text-xs text-zinc-500">
                <span className="flex items-center gap-1">
                    <Clock className="w-3 h-3" />
                    {order.timeWindow}
                </span>
                <span>{order.weight} kg</span>
            </div>
        </div>
    );
}

export default function DriverAssignment() {
    const [selectedDriver, setSelectedDriver] = useState<string | null>(null);
    const [selectedOrders, setSelectedOrders] = useState<Set<string>>(new Set());

    const toggleOrderSelection = (orderId: string) => {
        setSelectedOrders(prev => {
            const next = new Set(prev);
            if (next.has(orderId)) {
                next.delete(orderId);
            } else {
                next.add(orderId);
            }
            return next;
        });
    };

    const handleAssign = () => {
        if (selectedDriver && selectedOrders.size > 0) {
            // Would call API here
            alert(`Assigned ${selectedOrders.size} orders to driver ${selectedDriver}`);
            setSelectedOrders(new Set());
        }
    };

    const availableDrivers = mockDrivers.filter(d => d.status === 'available');

    return (
        <div className="h-full flex flex-col bg-zinc-900 p-4">
            <div className="flex items-center justify-between mb-4">
                <div>
                    <h2 className="text-lg font-semibold text-zinc-100 flex items-center gap-2">
                        <Zap className="w-5 h-5 text-emerald-400" />
                        Quick Assignment
                    </h2>
                    <p className="text-sm text-zinc-500">Assign pending orders to available drivers</p>
                </div>
            </div>

            <div className="flex-1 grid grid-cols-2 gap-4 overflow-hidden">
                {/* Drivers */}
                <div className="flex flex-col overflow-hidden">
                    <h3 className="text-sm font-medium text-zinc-400 mb-3 flex items-center gap-2">
                        <User className="w-4 h-4" />
                        Available Drivers ({availableDrivers.length})
                    </h3>
                    <div className="flex-1 space-y-3 overflow-auto pr-2">
                        {mockDrivers.map((driver) => (
                            <DriverCard
                                key={driver.id}
                                driver={driver}
                                isSelected={selectedDriver === driver.id}
                                onSelect={() => setSelectedDriver(driver.id)}
                            />
                        ))}
                    </div>
                </div>

                {/* Orders */}
                <div className="flex flex-col overflow-hidden">
                    <h3 className="text-sm font-medium text-zinc-400 mb-3 flex items-center gap-2">
                        <Clock className="w-4 h-4" />
                        Pending Orders ({mockPendingOrders.length})
                    </h3>
                    <div className="flex-1 space-y-2 overflow-auto pr-2">
                        {mockPendingOrders.map((order) => (
                            <div
                                key={order.id}
                                onClick={() => toggleOrderSelection(order.id)}
                                className={`cursor-pointer transition-all ${selectedOrders.has(order.id) ? 'ring-2 ring-emerald-500 rounded-lg' : ''
                                    }`}
                            >
                                <OrderCard order={order} />
                            </div>
                        ))}
                    </div>
                </div>
            </div>

            {/* Action Bar */}
            <div className="mt-4 pt-4 border-t border-zinc-800 flex items-center justify-between">
                <div className="text-sm text-zinc-400">
                    {selectedDriver && selectedOrders.size > 0 ? (
                        <span>
                            Ready to assign <strong className="text-zinc-200">{selectedOrders.size}</strong> orders
                        </span>
                    ) : (
                        <span>Select a driver and orders to assign</span>
                    )}
                </div>
                <button
                    onClick={handleAssign}
                    disabled={!selectedDriver || selectedOrders.size === 0}
                    className="flex items-center gap-2 px-4 py-2 bg-emerald-500 text-zinc-900 rounded-lg font-medium text-sm hover:bg-emerald-400 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                >
                    Assign Orders
                    <ArrowRight className="w-4 h-4" />
                </button>
            </div>
        </div>
    );
}

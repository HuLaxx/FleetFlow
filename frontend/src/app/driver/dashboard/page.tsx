'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import {
    MapPin, Navigation, Package, CheckCircle,
    Coffee, Truck, Menu, Bell, Search
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { useWebSocket } from '@/hooks/use-websocket';

// Mock Route Data (Matches Backend)
const mockRoute = {
    id: 'RT-8842',
    stops: [
        { id: '1', address: '350 5th Ave, New York, NY', status: 'pending', time: '10:30 AM', customer: 'Tech Solutions' },
        { id: '2', address: '200 Park Ave, New York, NY', status: 'pending', time: '11:15 AM', customer: 'Creative Studios' },
        { id: '3', address: '1 WTC, New York, NY', status: 'pending', time: '12:00 PM', customer: 'Global Trading' },
    ]
};

export default function DriverDashboard() {
    const router = useRouter();
    const [status, setStatus] = useState<'on_route' | 'on_break' | 'available'>('available');
    const [currentRoute, setCurrentRoute] = useState(mockRoute);
    const [activeStopIndex, setActiveStopIndex] = useState(0);

    // Connect to WS for GPS updates
    const { isConnected } = useWebSocket('vehicles');

    // This is a seeded demonstration. No GPS coordinates are sent to a real driver backend.

    const handleCompleteStop = () => {
        // Optimistic update
        setCurrentRoute(prev => ({
            ...prev,
            stops: prev.stops.map((stop, index) =>
                index === activeStopIndex ? { ...stop, status: 'completed' } : stop
            ),
        }));

        if (activeStopIndex < currentRoute.stops.length - 1) {
            setActiveStopIndex(prev => prev + 1);
        } else {
            setStatus('available'); // Route complete
        }
    };

    const toggleStatus = () => {
        setStatus(prev => prev === 'on_route' ? 'on_break' : 'on_route');
    };

    const currentStop = currentRoute.stops[activeStopIndex];

    return (
        <div className="min-h-screen bg-stone-950 pb-20">
            {/* Header */}
            <div className="bg-stone-900 border-b border-stone-800 p-4 sticky top-0 z-20">
                <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                        <div className="w-10 h-10 bg-emerald-500 rounded-full flex items-center justify-center text-stone-900 font-bold">
                            MJ
                        </div>
                        <div>
                            <h2 className="text-stone-100 font-semibold text-sm">Sample Driver</h2>
                            <div className="flex items-center gap-1.5">
                                <span className={cn(
                                    "w-2 h-2 rounded-full animate-pulse",
                                    status === 'on_route' ? "bg-emerald-500" :
                                        status === 'on_break' ? "bg-emerald-500" : "bg-stone-500"
                                )} />
                                <span className="text-xs text-stone-400 capitalize">{status.replace('_', ' ')}</span>
                            </div>
                        </div>
                    </div>
                    <button className="p-2 bg-stone-800 rounded-full text-stone-400 relative">
                        <Bell className="w-5 h-5" />
                        <span className="absolute top-0 right-0 w-2.5 h-2.5 bg-red-500 rounded-full border-2 border-stone-800" />
                    </button>
                </div>
            </div>

            {/* Main Content */}
            <div className="p-4 space-y-4">

                {/* Status Card */}
                {status === 'available' && activeStopIndex === currentRoute.stops.length ? (
                    <div className="bg-stone-900 border border-stone-800 rounded-xl p-6 text-center">
                        <div className="w-16 h-16 bg-emerald-500/10 rounded-full flex items-center justify-center mx-auto mb-4">
                            <CheckCircle className="w-8 h-8 text-emerald-500" />
                        </div>
                        <h3 className="text-lg font-bold text-stone-100 mb-2">All Deliveries Complete!</h3>
                        <p className="text-sm text-stone-500 mb-6">Great job. You have no pending stops.</p>
                        <button
                            onClick={() => router.push('/driver')}
                            className="w-full py-3 bg-stone-800 text-stone-300 rounded-lg hover:bg-stone-700 hover:text-stone-100 transition-colors"
                        >
                            End Shift
                        </button>
                    </div>
                ) : (
                    <>
                        {/* Next Stop Card (Hero) */}
                        <div className="bg-gradient-to-br from-emerald-600 to-emerald-700 rounded-2xl p-5 shadow-lg shadow-emerald-900/20 text-stone-950 relative overflow-hidden">
                            <div className="absolute top-0 right-0 p-3 opacity-10">
                                <Truck className="w-24 h-24" />
                            </div>

                            <div className="relative z-10">
                                <div className="flex justify-between items-start mb-4">
                                    <div>
                                        <p className="text-emerald-100 text-xs font-semibold uppercase tracking-wider mb-1">Next Destination</p>
                                        <h3 className="text-xl font-bold leading-tight">{currentStop.customer}</h3>
                                    </div>
                                    <div className="bg-stone-950/20 backdrop-blur-sm px-3 py-1 rounded-full text-xs font-bold font-mono">
                                        {currentStop.time}
                                    </div>
                                </div>

                                <div className="flex items-start gap-2 mb-6">
                                    <MapPin className="w-5 h-5 mt-0.5 shrink-0" />
                                    <p className="font-medium text-lg leading-snug">{currentStop.address}</p>
                                </div>

                                <div className="flex gap-2">
                                    <button className="flex-1 bg-stone-950 text-emerald-500 py-3 rounded-xl font-bold flex items-center justify-center gap-2 shadow-sm active:scale-[0.98] transition-transform">
                                        <Navigation className="w-4 h-4" /> Start GPS
                                    </button>
                                    <button
                                        onClick={handleCompleteStop}
                                        className="flex-1 bg-white/20 hover:bg-white/30 text-stone-950 py-3 rounded-xl font-bold flex items-center justify-center gap-2 backdrop-blur-sm transition-colors"
                                    >
                                        <CheckCircle className="w-4 h-4" /> Delivered
                                    </button>
                                </div>
                            </div>
                        </div>

                        {/* Route Timeline */}
                        <div className="bg-stone-900 border border-stone-800 rounded-xl p-4">
                            <h4 className="text-stone-400 text-xs font-semibold uppercase tracking-wider mb-4">Current Route</h4>
                            <div className="space-y-6 relative pl-4">
                                {/* Line */}
                                <div className="absolute left-[19px] top-2 bottom-2 w-0.5 bg-stone-800" />

                                {currentRoute.stops.map((stop, index) => (
                                    <div key={stop.id} className="relative flex items-center gap-4 z-10">
                                        {/* Dot */}
                                        <div className={cn(
                                            "w-3 h-3 rounded-full border-2 shrink-0",
                                            stop.status === 'completed'
                                                ? "bg-stone-900 border-emerald-500"
                                                : index === activeStopIndex
                                                    ? "bg-emerald-500 border-emerald-500 ring-4 ring-emerald-500/20"
                                                    : "bg-stone-800 border-stone-600"
                                        )} />

                                        <div className={cn(
                                            "flex-1 p-3 rounded-lg border",
                                            index === activeStopIndex
                                                ? "bg-stone-800 border-emerald-500/30"
                                                : "bg-stone-900/50 border-stone-800 opacity-60"
                                        )}>
                                            <div className="flex justify-between items-start">
                                                <p className="text-stone-200 font-medium text-sm">{stop.customer}</p>
                                                <span className="text-xs text-stone-500 font-mono">{stop.time}</span>
                                            </div>
                                            <p className="text-stone-500 text-xs mt-0.5 truncate">{stop.address}</p>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </div>
                    </>
                )}
            </div>

            {/* Mobile Bottom Nav */}
            <div className="fixed bottom-0 left-0 w-full bg-stone-900 border-t border-stone-800 pb-safe z-30">
                <div className="flex justify-around items-center h-16">
                    <button className="flex flex-col items-center gap-1 text-emerald-500">
                        <Navigation className="w-5 h-5" />
                        <span className="text-[10px] font-medium">Route</span>
                    </button>
                    <button className="flex flex-col items-center gap-1 text-stone-500 hover:text-stone-300">
                        <Package className="w-5 h-5" />
                        <span className="text-[10px] font-medium">Manifest</span>
                    </button>

                    {/* Floating Action Button for Status */}
                    <div className="relative -top-6">
                        <button
                            onClick={toggleStatus}
                            className={cn(
                                "w-14 h-14 rounded-full flex items-center justify-center shadow-lg transition-colors border-4 border-stone-950",
                                status === 'on_route' ? "bg-emerald-500 text-stone-900" : "bg-stone-700 text-stone-400"
                            )}
                        >
                            {status === 'on_route' ? <Truck className="w-6 h-6" /> : <Coffee className="w-6 h-6" />}
                        </button>
                    </div>

                    <button className="flex flex-col items-center gap-1 text-stone-500 hover:text-stone-300">
                        <Search className="w-5 h-5" />
                        <span className="text-[10px] font-medium">History</span>
                    </button>
                    <button className="flex flex-col items-center gap-1 text-stone-500 hover:text-stone-300">
                        <Menu className="w-5 h-5" />
                        <span className="text-[10px] font-medium">Menu</span>
                    </button>
                </div>
            </div>
        </div>
    );
}

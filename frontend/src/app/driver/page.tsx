'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { Truck, ArrowRight, MapPin } from 'lucide-react';
import { motion } from 'framer-motion';

export default function DriverLoginPage() {
    const router = useRouter();
    const [driverId, setDriverId] = useState('');
    const [isLoading, setIsLoading] = useState(false);

    const handleLogin = (e: React.FormEvent) => {
        e.preventDefault();
        setIsLoading(true);

        // Simulate login delay
        setTimeout(() => {
            // In a real app, validate ID against backend
            // storing simple mock session in localStorage for now
            localStorage.setItem('fleetflow_driver_id', driverId || 'DRV-1001');
            router.push('/driver/dashboard');
        }, 1000);
    };

    return (
        <div className="min-h-screen bg-stone-950 flex flex-col items-center justify-center p-6 relative overflow-hidden">
            {/* Background Effects */}
            <div className="absolute top-0 left-0 w-full h-96 bg-gradient-to-b from-amber-900/10 to-transparent pointer-events-none" />
            <div className="absolute -top-20 -right-20 w-64 h-64 bg-amber-500/5 rounded-full blur-3xl" />

            <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                className="w-full max-w-sm z-10"
            >
                {/* Logo Area */}
                <div className="text-center mb-10">
                    <div className="w-16 h-16 bg-gradient-to-br from-amber-500 to-amber-600 rounded-2xl flex items-center justify-center mx-auto mb-4 shadow-xl shadow-amber-900/20">
                        <Truck className="w-8 h-8 text-stone-950" />
                    </div>
                    <h1 className="text-2xl font-bold text-stone-100 mb-1">FleetFlow Driver</h1>
                    <p className="text-stone-500 text-sm">Log in to start your delivery route</p>
                </div>

                {/* Login Form */}
                <form onSubmit={handleLogin} className="space-y-4">
                    <div className="space-y-2">
                        <label htmlFor="driver-id" className="text-xs font-semibold text-stone-400 uppercase tracking-wider ml-1">
                            Driver ID
                        </label>
                        <div className="relative">
                            <input
                                id="driver-id"
                                type="text"
                                placeholder="Enter your ID (e.g. DRV-1001)"
                                value={driverId}
                                onChange={(e) => setDriverId(e.target.value)}
                                className="w-full bg-stone-900 border border-stone-800 text-stone-100 rounded-xl px-4 py-3.5 pl-11 focus:ring-2 focus:ring-amber-500/50 focus:border-amber-500 transition-all outline-none placeholder:text-stone-600"
                            />
                            <MapPin className="absolute left-3.5 top-3.5 w-5 h-5 text-stone-600" />
                        </div>
                    </div>

                    <button
                        type="submit"
                        disabled={isLoading}
                        className="w-full bg-gradient-to-r from-amber-500 to-amber-600 hover:from-amber-400 hover:to-amber-500 text-stone-950 font-bold py-3.5 rounded-xl transition-all shadow-lg shadow-amber-900/20 active:scale-[0.98] flex items-center justify-center gap-2 disabled:opacity-70 disabled:cursor-not-allowed"
                    >
                        {isLoading ? (
                            <span className="w-5 h-5 border-2 border-stone-950/30 border-t-stone-950 rounded-full animate-spin" />
                        ) : (
                            <>
                                Start Shift <ArrowRight className="w-4 h-4" />
                            </>
                        )}
                    </button>
                </form>

                {/* Footer Info */}
                <p className="mt-8 text-center text-xs text-stone-600">
                    v4.2.0 • Phase 4 Build
                </p>
            </motion.div>
        </div>
    );
}

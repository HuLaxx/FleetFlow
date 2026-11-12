'use client';

import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Sparkles, MapPin, Calendar, Loader2, CheckCircle, XCircle } from 'lucide-react';
import { trpc } from '@/lib/trpc';

interface OptimizeRoutesDialogProps {
    isOpen: boolean;
    onClose: () => void;
}

export function OptimizeRoutesDialog({ isOpen, onClose }: OptimizeRoutesDialogProps) {
    const [selectedDate, setSelectedDate] = useState(new Date().toISOString().split('T')[0]);
    const [selectedDepot, setSelectedDepot] = useState<string>('');

    // Fetch depots for selection (we'd need to add a depots router, but for now use a default)
    // In a real app: const { data: depots } = trpc.depots.getAll.useQuery();

    const optimizeMutation = trpc.optimization.optimizeRoutes.useMutation({
        onSuccess: (data) => {
            console.log('Optimization complete:', data);
        },
        onError: (error) => {
            console.error('Optimization failed:', error);
        }
    });

    const handleOptimize = async () => {
        if (!selectedDepot) {
            alert('Please select a depot');
            return;
        }

        try {
            await optimizeMutation.mutateAsync({
                date: selectedDate,
                depot_id: selectedDepot,
            });
        } catch (error) {
            console.error('Optimization error:', error);
        }
    };

    // Mock depots (in production, fetch from API)
    const mockDepots = [
        { id: '00000000-0000-0000-0000-000000000001', name: 'Manhattan Depot' },
        { id: '00000000-0000-0000-0000-000000000002', name: 'Brooklyn Depot' },
        { id: '00000000-0000-0000-0000-000000000003', name: 'Queens Depot' },
    ];

    if (!isOpen) return null;

    return (
        <AnimatePresence>
            <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4"
                onClick={onClose}
            >
                <motion.div
                    initial={{ scale: 0.95, opacity: 0 }}
                    animate={{ scale: 1, opacity: 1 }}
                    exit={{ scale: 0.95, opacity: 0 }}
                    className="bg-stone-900 border border-stone-800 rounded-2xl shadow-2xl max-w-md w-full overflow-hidden"
                    onClick={(e) => e.stopPropagation()}
                >
                    {/* Header */}
                    <div className="bg-gradient-to-r from-emerald-600 to-teal-600 p-6">
                        <div className="flex items-center gap-3">
                            <div className="p-2 bg-white/20 rounded-lg">
                                <Sparkles className="w-6 h-6 text-white" />
                            </div>
                            <div>
                                <h2 className="text-xl font-bold text-white">Optimize Routes</h2>
                                <p className="text-sm text-white/80">OR-Tools route proposal · requires matching backend depot data</p>
                            </div>
                        </div>
                    </div>

                    {/* Content */}
                    <div className="p-6 space-y-4">
                        {/* Date Selection */}
                        <div>
                            <label className="block text-sm font-medium text-stone-300 mb-2">
                                <Calendar className="w-4 h-4 inline mr-1" />
                                Delivery Date
                            </label>
                            <input
                                type="date"
                                value={selectedDate}
                                onChange={(e) => setSelectedDate(e.target.value)}
                                className="w-full px-4 py-2 bg-stone-800 border border-stone-700 rounded-lg text-stone-100 focus:outline-none focus:border-emerald-500 transition-colors"
                            />
                        </div>

                        {/* Depot Selection */}
                        <div>
                            <label className="block text-sm font-medium text-stone-300 mb-2">
                                <MapPin className="w-4 h-4 inline mr-1" />
                                Depot
                            </label>
                            <select
                                value={selectedDepot}
                                onChange={(e) => setSelectedDepot(e.target.value)}
                                className="w-full px-4 py-2 bg-stone-800 border border-stone-700 rounded-lg text-stone-100 focus:outline-none focus:border-emerald-500 transition-colors"
                            >
                                <option value="">Select a sample depot...</option>
                                {mockDepots.map(depot => (
                                    <option key={depot.id} value={depot.id}>
                                        {depot.name}
                                    </option>
                                ))}
                            </select>
                            <p className="text-xs text-amber-400 mt-2">Sample depot IDs are placeholders. A matching depot must exist in the backend before an optimisation request can succeed.</p>
                        </div>

                        {/* Results Display */}
                        {optimizeMutation.isSuccess && (
                            <motion.div
                                initial={{ opacity: 0, y: 10 }}
                                animate={{ opacity: 1, y: 0 }}
                                className="p-4 bg-emerald-900/20 border border-emerald-700/30 rounded-lg"
                            >
                                <div className="flex items-start gap-3">
                                    <CheckCircle className="w-5 h-5 text-emerald-500 flex-shrink-0 mt-0.5" />
                                    <div className="flex-1">
                                        <h4 className="font-semibold text-emerald-400 mb-2">Route Proposals Generated</h4>
                                        <div className="space-y-1 text-sm text-stone-300">
                                            <div className="flex justify-between">
                                                <span>Candidate Routes:</span>
                                                <span className="font-mono text-emerald-400">
                                                    {optimizeMutation.data?.routes?.length || 0}
                                                </span>
                                            </div>
                                            <div className="flex justify-between">
                                                <span>Stops in Proposal:</span>
                                                <span className="font-mono text-emerald-400">
                                                    {optimizeMutation.data?.metrics?.total_orders_scheduled || 0}
                                                </span>
                                            </div>
                                            <div className="flex justify-between items-center">
                                                <span>Total Distance:</span>
                                                <span className="font-mono text-emerald-400">
                                                    {optimizeMutation.data?.metrics?.total_distance_km?.toFixed(1) || 0} km
                                                </span>
                                            </div>

                                        </div>
                                    </div>
                                </div>
                            </motion.div>
                        )}

                        {optimizeMutation.isError && (
                            <div className="p-4 bg-red-900/20 border border-red-700/30 rounded-lg">
                                <div className="flex items-start gap-3">
                                    <XCircle className="w-5 h-5 text-red-500 flex-shrink-0 mt-0.5" />
                                    <div>
                                        <h4 className="font-semibold text-red-400 mb-1">Optimization Failed</h4>
                                        <p className="text-sm text-stone-400">
                                            {optimizeMutation.error?.message || 'An error occurred'}
                                        </p>
                                    </div>
                                </div>
                            </div>
                        )}
                    </div>

                    {/* Actions */}
                    <div className="p-6 pt-0 flex gap-3">
                        <button
                            onClick={onClose}
                            className="flex-1 px-4 py-2 bg-stone-800 hover:bg-stone-700 text-stone-300 rounded-lg transition-colors"
                            disabled={optimizeMutation.isPending}
                        >
                            {optimizeMutation.isSuccess ? 'Close' : 'Cancel'}
                        </button>
                        <button
                            onClick={handleOptimize}
                            disabled={optimizeMutation.isPending || !selectedDepot}
                            className="flex-1 px-4 py-2 bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 text-white rounded-lg transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2 font-medium"
                        >
                            {optimizeMutation.isPending ? (
                                <>
                                    <Loader2 className="w-4 h-4 animate-spin" />
                                    Optimizing...
                                </>
                            ) : (
                                <>
                                    <Sparkles className="w-4 h-4" />
                                    Optimize Routes
                                </>
                            )}
                        </button>
                    </div>
                </motion.div>
            </motion.div>
        </AnimatePresence>
    );
}

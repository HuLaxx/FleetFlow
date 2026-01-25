'use client';

import { Cloud, HardDrive, Sparkles } from 'lucide-react';

type DeploymentNoticeProps = {
    variant?: 'hero' | 'compact';
};

export function DeploymentNotice({ variant = 'compact' }: DeploymentNoticeProps) {
    const isHero = variant === 'hero';

    return (
        <div
            className={`w-full rounded-2xl border border-emerald-500/20 bg-gradient-to-br from-stone-900/80 via-stone-900/60 to-stone-950 px-4 ${
                isHero ? 'py-5 md:py-6' : 'py-3'
            } shadow-lg shadow-emerald-900/10 backdrop-blur`}
        >
            <div className={`flex ${isHero ? 'flex-col md:flex-row md:items-center' : 'items-center'} gap-4`}>
                <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-xl bg-emerald-500/15 border border-emerald-500/30 flex items-center justify-center">
                        <Cloud className="w-5 h-5 text-emerald-400" />
                    </div>
                    <div>
                        <p className={`text-sm ${isHero ? 'md:text-base' : ''} text-emerald-200 font-semibold`}>
                            Live demo runs on free-tier infrastructure
                        </p>
                        <p className="text-xs text-stone-400">
                            Supabase + Upstash + Railway (fallback-safe, limited workloads)
                        </p>
                    </div>
                </div>

                <div className={`flex items-start gap-3 ${isHero ? 'md:ml-auto' : ''}`}>
                    <div className="w-9 h-9 rounded-xl bg-stone-800 border border-stone-700 flex items-center justify-center">
                        <HardDrive className="w-4 h-4 text-stone-300" />
                    </div>
                    <div>
                        <p className={`text-xs ${isHero ? 'md:text-sm' : ''} text-stone-200 font-medium`}>
                            Full-power stack is local-first
                        </p>
                        <p className="text-xs text-stone-500">
                            Run locally to unlock Kafka, Flink, Airflow, PostGIS, TimescaleDB, Redis, MongoDB, OSRM.
                        </p>
                    </div>
                </div>

                {isHero && (
                    <div className="flex items-center gap-2 text-xs text-emerald-300/90 bg-emerald-500/10 border border-emerald-500/20 px-3 py-1.5 rounded-full">
                        <Sparkles className="w-3.5 h-3.5" />
                        Portfolio priority: local = full capabilities
                    </div>
                )}
            </div>
        </div>
    );
}
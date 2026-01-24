'use client';

import {
    Database,
    Server,
    Monitor,
    Cpu,
    Cloud,
    Layers,
    ArrowRight,
    ArrowDown,
} from 'lucide-react';
import { SiteHeader } from '@/components/site/site-header';
import { SiteFooter } from '@/components/site/site-footer';
import Link from 'next/link';

// Logo URLs from Simple Icons
const getLogoUrl = (name: string) => {
    const slugMap: Record<string, string> = {
        'Next.js': 'nextdotjs',
        'Deck.gl': 'webgl',
        'tRPC': 'trpc',
        'Tailwind': 'tailwindcss',
        'FastAPI': 'fastapi',
        'WebSocket': 'socket.io',
        'Redis': 'redis',
        'Kafka': 'apachekafka',
        'Airflow': 'apacheairflow',
        'dbt': 'dbt',
        'Prophet': 'meta',
        'OR-Tools': 'google',
        'MLflow': 'mlflow',
        'PostgreSQL': 'postgresql',
        'TimescaleDB': 'timescale',
        'MongoDB': 'mongodb',
        'Docker': 'docker',
        'Nginx': 'nginx',
        'GitHub': 'github',
    };
    const slug = slugMap[name] || name.toLowerCase().replace(/[^a-z0-9]/g, '');
    return `https://cdn.simpleicons.org/${slug}/white`;
};

// Architecture Diagram Layers - Mapped to Warm Tones
const layers = [
    {
        name: 'Presentation Layer',
        icon: Monitor,
        color: 'from-amber-600 to-amber-500', // Gold
        bgColor: 'bg-amber-900/10',
        borderColor: 'border-amber-500/20',
        components: [
            { name: 'Next.js', full: 'Next.js 16 App Router' },
            { name: 'Deck.gl', full: 'WebGL Map Visualization' },
            { name: 'tRPC', full: 'End-to-end typesafe API' },
            { name: 'Tailwind', full: 'Utility-first CSS' },
        ],
    },
    {
        name: 'API Layer',
        icon: Server,
        color: 'from-orange-600 to-orange-500', // Orange-Bronze
        bgColor: 'bg-orange-900/10',
        borderColor: 'border-orange-500/20',
        components: [
            { name: 'FastAPI', full: 'High-performance Python API' },
            { name: 'WebSocket', full: 'Real-time bidirectional' },
            { name: 'Redis', full: 'Response caching layer' },
        ],
    },
    {
        name: 'Processing Layer',
        icon: Cpu,
        color: 'from-stone-500 to-stone-400', // Stone
        bgColor: 'bg-stone-800/30',
        borderColor: 'border-stone-500/20',
        components: [
            { name: 'Kafka', full: 'Event streaming platform' },
            { name: 'Airflow', full: 'Workflow orchestration' },
            { name: 'dbt', full: 'Data transformations' },
        ],
    },
    {
        name: 'ML Layer',
        icon: Layers,
        color: 'from-yellow-600 to-yellow-500', // Deep Yellow/Gold
        bgColor: 'bg-yellow-900/10',
        borderColor: 'border-yellow-500/20',
        components: [
            { name: 'Prophet', full: 'Demand forecasting' },
            { name: 'OR-Tools', full: 'Route optimization VRP' },
            { name: 'MLflow', full: 'Experiment tracking' },
        ],
    },
    {
        name: 'Data Layer',
        icon: Database,
        color: 'from-amber-700 to-amber-600', // Bronze
        bgColor: 'bg-amber-950/30',
        borderColor: 'border-amber-700/20',
        components: [
            { name: 'PostgreSQL', full: 'PostGIS + TimescaleDB' },
            { name: 'MongoDB', full: 'Document store' },
            { name: 'Redis', full: 'Cache & sessions' },
        ],
    },
    {
        name: 'Infrastructure',
        icon: Cloud,
        color: 'from-stone-600 to-stone-500', // Dark Stone
        bgColor: 'bg-stone-900/30',
        borderColor: 'border-stone-600/20',
        components: [
            { name: 'Docker', full: '8 containerized services' },
            { name: 'Nginx', full: 'Reverse proxy' },
            { name: 'GitHub', full: 'CI/CD Actions' },
        ],
    },
];

export default function ArchitecturePage() {
    return (
        <div className="min-h-screen bg-stone-950">
            <SiteHeader />

            {/* Hero */}
            <section className="pt-32 pb-16 relative overflow-hidden">
                <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top,_var(--tw-gradient-stops))] from-stone-900/40 via-stone-950 to-stone-950" />
                <div className="max-w-7xl mx-auto px-6 relative z-10">
                    <div className="text-center max-w-3xl mx-auto">
                        <h1 className="text-4xl md:text-5xl font-bold text-stone-100 mb-4">
                            System Architecture
                        </h1>
                        <p className="text-xl text-stone-400">
                            A modern, scalable architecture designed for real-time delivery optimization
                            with ML-powered decision making.
                        </p>
                    </div>
                </div>
            </section>

            {/* Visual Data Flow */}
            <section className="py-12 relative">
                <div className="absolute inset-0 bg-[linear-gradient(rgba(245,158,11,0.02)_1px,transparent_1px),linear-gradient(90deg,rgba(245,158,11,0.02)_1px,transparent_1px)] bg-[size:40px_40px] [mask-image:radial-gradient(ellipse_at_center,black_40%,transparent_80%)]" />
                <div className="max-w-5xl mx-auto px-6 relative z-10">
                    <h2 className="text-2xl font-bold text-stone-100 mb-8 text-center">Data Flow</h2>

                    <div className="relative bg-stone-900/80 border border-stone-800 rounded-2xl p-8 backdrop-blur-sm shadow-2xl shadow-black/50">
                        {/* Flow visualization */}
                        <div className="space-y-6">
                            {/* Client Layer */}
                            <div className="flex justify-center gap-4 flex-wrap">
                                {['Dashboard', 'Map', 'Orders', 'Alerts'].map((item) => (
                                    <div key={item} className="px-6 py-3 bg-amber-900/20 border border-amber-500/20 rounded-xl text-amber-300 font-medium shadow-lg shadow-amber-900/10">
                                        {item}
                                    </div>
                                ))}
                            </div>

                            <div className="flex justify-center"><ArrowDown className="w-6 h-6 text-stone-600" /></div>

                            {/* API Layer */}
                            <div className="flex justify-center">
                                <div className="px-8 py-4 bg-orange-900/20 border border-orange-500/20 rounded-xl text-center shadow-lg shadow-orange-900/10">
                                    <p className="text-orange-300 font-semibold">API Gateway</p>
                                    <p className="text-orange-400/70 text-sm">FastAPI + WebSocket</p>
                                </div>
                            </div>

                            <div className="flex justify-center gap-8">
                                <ArrowDown className="w-6 h-6 text-stone-600" />
                                <ArrowDown className="w-6 h-6 text-stone-600" />
                            </div>

                            {/* Processing */}
                            <div className="flex justify-center gap-8 flex-wrap">
                                <div className="px-6 py-3 bg-stone-800/50 border border-stone-600/30 rounded-xl text-center shadow-lg">
                                    <p className="text-stone-300 font-medium">Apache Kafka</p>
                                    <p className="text-stone-500 text-xs">Event Streaming</p>
                                </div>
                                <div className="px-6 py-3 bg-yellow-900/20 border border-yellow-500/20 rounded-xl text-center shadow-lg shadow-yellow-900/10">
                                    <p className="text-yellow-300 font-medium">ML Serving</p>
                                    <p className="text-yellow-500/70 text-xs">Forecasting + VRP</p>
                                </div>
                            </div>

                            <div className="flex justify-center"><ArrowDown className="w-6 h-6 text-stone-600" /></div>

                            {/* Data */}
                            <div className="flex justify-center">
                                <div className="px-8 py-4 bg-stone-900 border border-stone-700 rounded-xl text-center shadow-lg">
                                    <p className="text-stone-300 font-semibold">PostgreSQL</p>
                                    <p className="text-stone-500 text-sm">PostGIS + TimescaleDB</p>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </section>

            {/* Architecture Layers */}
            <section className="py-16">
                <div className="max-w-7xl mx-auto px-6">
                    <h2 className="text-2xl font-bold text-stone-100 mb-12 text-center">Architecture Layers</h2>

                    <div className="space-y-6">
                        {layers.map((layer, index) => (
                            <div key={layer.name}>
                                <div className={`${layer.bgColor} border ${layer.borderColor} rounded-2xl p-6 transition-all hover:bg-opacity-30`}>
                                    <div className="flex items-center gap-4 mb-6">
                                        <div className={`w-12 h-12 rounded-xl bg-gradient-to-br ${layer.color} flex items-center justify-center shadow-lg`}>
                                            <layer.icon className="w-6 h-6 text-stone-900" />
                                        </div>
                                        <h3 className="text-xl font-semibold text-stone-100">{layer.name}</h3>
                                    </div>

                                    <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
                                        {layer.components.map((comp) => (
                                            <div key={comp.name} className="bg-stone-900/80 rounded-xl p-4 flex items-center gap-3 border border-transparent hover:border-amber-500/20 transition-all">
                                                <div className="w-10 h-10 rounded-lg bg-stone-800 flex items-center justify-center flex-shrink-0">
                                                    <img
                                                        src={getLogoUrl(comp.name)}
                                                        alt={comp.name}
                                                        className="w-5 h-5 opacity-80"
                                                        onError={(e) => {
                                                            (e.target as HTMLImageElement).style.display = 'none';
                                                        }}
                                                    />
                                                </div>
                                                <div className="min-w-0">
                                                    <p className="font-medium text-stone-200 truncate">{comp.name}</p>
                                                    <p className="text-xs text-stone-500 truncate">{comp.full}</p>
                                                </div>
                                            </div>
                                        ))}
                                    </div>
                                </div>

                                {index < layers.length - 1 && (
                                    <div className="flex justify-center py-2">
                                        <ArrowDown className="w-6 h-6 text-stone-800" />
                                    </div>
                                )}
                            </div>
                        ))}
                    </div>
                </div>
            </section>

            {/* CTA */}
            <section className="py-16">
                <div className="max-w-4xl mx-auto px-6 text-center">
                    <Link
                        href="/tech-stack"
                        className="inline-flex items-center gap-2 px-6 py-3 bg-stone-900 border border-stone-800 text-stone-300 rounded-xl font-medium hover:bg-stone-800 hover:text-amber-400 hover:border-amber-500/30 transition-all"
                    >
                        Explore Tech Stack
                        <ArrowRight className="w-4 h-4" />
                    </Link>
                </div>
            </section>

            <SiteFooter />
        </div>
    );
}

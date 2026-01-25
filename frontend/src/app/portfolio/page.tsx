'use client';

import Link from 'next/link';
import { SiteHeader } from '@/components/site/site-header';
import { SiteFooter } from '@/components/site/site-footer';
import { DeploymentNotice } from '@/components/site/deployment-notice';
import {
    Workflow,
    Database,
    Cpu,
    Brain,
    Layers,
    ShieldCheck,
    Terminal,
    ArrowRight
} from 'lucide-react';

const workflowSteps = [
    {
        title: 'Ingest + Stream',
        icon: Workflow,
        description: 'Producers emit orders, GPS, and route events into Kafka topics for real-time flow.',
        tools: ['Kafka', 'FastAPI', 'Kafka consumers'],
    },
    {
        title: 'Store + Index',
        icon: Database,
        description: 'Operational data is stored in Postgres/PostGIS with time-series in TimescaleDB.',
        tools: ['PostgreSQL', 'PostGIS', 'TimescaleDB'],
    },
    {
        title: 'Batch + Transform',
        icon: Layers,
        description: 'Airflow DAGs orchestrate dbt models and scheduled optimization workloads.',
        tools: ['Airflow', 'dbt', 'SQL models'],
    },
    {
        title: 'Optimize',
        icon: Cpu,
        description: 'OR-Tools and custom heuristics compute multi-objective routes and assignments.',
        tools: ['OR-Tools', 'Optimization API'],
    },
    {
        title: 'Predict',
        icon: Brain,
        description: 'Forecasting ensemble blends Prophet, LSTM, and XGBoost for demand prediction.',
        tools: ['Prophet', 'TensorFlow', 'XGBoost'],
    },
    {
        title: 'Serve + Observe',
        icon: ShieldCheck,
        description: 'FastAPI APIs, WebSockets, and monitoring dashboards expose real-time state.',
        tools: ['FastAPI', 'WebSocket', 'Prometheus/Grafana'],
    },
];

const roleEvidence = [
    {
        role: 'Data Engineering',
        level: 'Senior-grade foundations',
        evidence: [
            'Airflow DAGs for daily optimization + hourly forecasting',
            'dbt staging + marts models for analytics layers',
            'Flink stream processor for real-time event handling',
        ],
    },
    {
        role: 'Data Science',
        level: 'Applied forecasting + EDA',
        evidence: [
            'EDA notebook with exploratory insights',
            'Feature engineering for temporal signals',
            'Evaluation metrics utilities in ML pipeline',
        ],
    },
    {
        role: 'ML Engineering',
        level: 'Experimentation + serving scaffolding',
        evidence: [
            'Training + tuning scripts for forecasting models',
            'MLflow experiment tracking + model registry hooks',
            'Standalone ML inference API for routing + forecasting',
        ],
    },
    {
        role: 'Backend / Software',
        level: 'Production-style API core',
        evidence: [
            'FastAPI REST + GraphQL endpoints with auth middleware',
            'Kafka consumers + event producers for state changes',
            'Pytest suite for API, consumers, and optimization logic',
        ],
    },
    {
        role: 'Full-Stack',
        level: 'Type-safe dashboard + real-time UI',
        evidence: [
            'Next.js App Router dashboard with tRPC data layer',
            'Deck.gl + MapLibre for fleet visualization',
            'Playwright E2E tests for demo flows',
        ],
    },
    {
        role: 'Data Architecture / DevOps',
        level: 'Multi-store + infra blueprints',
        evidence: [
            'Postgres/PostGIS + Timescale + Redis + MongoDB topology',
            'Docker Compose + Kubernetes manifests for services',
            'Prometheus + Grafana dashboards for observability',
        ],
    },
];

const techBadges = [
    'Next.js 16',
    'React 19',
    'TypeScript',
    'FastAPI',
    'Kafka',
    'PostGIS',
    'TimescaleDB',
    'Redis',
    'MongoDB',
    'Airflow',
    'Flink',
    'dbt',
    'OR-Tools',
    'MLflow',
    'Docker',
    'Kubernetes',
    'Prometheus',
    'Grafana',
];

const TechBadge = ({ name }: { name: string }) => (
    <div className="px-3 py-1.5 rounded-full bg-stone-900 border border-stone-800 text-xs font-medium text-stone-400 hover:text-emerald-400 hover:border-emerald-500/20 transition-all cursor-default">
        {name}
    </div>
);

export default function PortfolioPage() {
    return (
        <div className="min-h-screen bg-stone-950">
            <SiteHeader />

            {/* Hero */}
            <section className="pt-32 pb-12 relative overflow-hidden">
                <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top,_var(--tw-gradient-stops))] from-stone-900/60 via-stone-950 to-stone-950" />
                <div className="max-w-6xl mx-auto px-6 relative z-10 text-center">
                    <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-stone-900/60 border border-emerald-500/20 text-xs font-medium text-emerald-200 mb-6">
                        <Terminal className="w-3.5 h-3.5" />
                        Portfolio evidence • multi-role scope
                    </div>
                    <h1 className="text-4xl md:text-5xl font-bold text-stone-100 mb-4">
                        Workflow, Integrations, and Role Evidence
                    </h1>
                    <p className="text-lg text-stone-400 max-w-3xl mx-auto">
                        This page maps real code, data pipelines, and infrastructure to the exact
                        skills and roles demonstrated by FleetFlow.
                    </p>
                </div>
            </section>

            {/* Rank-1 Focus Notice */}
            <section className="pb-10">
                <div className="max-w-6xl mx-auto px-6">
                    <DeploymentNotice variant="hero" />
                </div>
            </section>

            {/* Workflow */}
            <section className="py-12">
                <div className="max-w-6xl mx-auto px-6">
                    <div className="flex items-center justify-between mb-8">
                        <h2 className="text-2xl font-bold text-stone-100">Workflow & Integrations</h2>
                        <span className="text-xs text-stone-500">End-to-end flow from data to decisions</span>
                    </div>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                        {workflowSteps.map((step) => (
                            <div
                                key={step.title}
                                className="rounded-2xl bg-stone-900/60 border border-stone-800 p-6 hover:border-emerald-500/20 transition-all"
                            >
                                <div className="flex items-center gap-3 mb-4">
                                    <div className="w-10 h-10 rounded-xl bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center">
                                        <step.icon className="w-5 h-5 text-emerald-400" />
                                    </div>
                                    <h3 className="text-lg font-semibold text-stone-100">{step.title}</h3>
                                </div>
                                <p className="text-sm text-stone-400 mb-4">
                                    {step.description}
                                </p>
                                <div className="flex flex-wrap gap-2">
                                    {step.tools.map((tool) => (
                                        <span key={tool} className="text-xs text-stone-500 border border-stone-800 bg-stone-950/60 px-2 py-1 rounded-full">
                                            {tool}
                                        </span>
                                    ))}
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            </section>

            {/* Role Evidence */}
            <section className="py-12 bg-stone-900/30 border-y border-stone-900">
                <div className="max-w-6xl mx-auto px-6">
                    <div className="flex items-center justify-between mb-8">
                        <h2 className="text-2xl font-bold text-stone-100">Role Evidence Matrix</h2>
                        <span className="text-xs text-stone-500">Claims backed by shipped code</span>
                    </div>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                        {roleEvidence.map((role) => (
                            <div
                                key={role.role}
                                className="rounded-2xl bg-stone-950/80 border border-stone-800 p-6"
                            >
                                <div className="flex items-center justify-between mb-4">
                                    <div>
                                        <h3 className="text-lg font-semibold text-stone-100">{role.role}</h3>
                                        <p className="text-xs text-emerald-400/80 mt-1">{role.level}</p>
                                    </div>
                                </div>
                                <ul className="space-y-2 text-sm text-stone-400">
                                    {role.evidence.map((item) => (
                                        <li key={item} className="flex items-start gap-2">
                                            <span className="mt-1 w-1.5 h-1.5 rounded-full bg-emerald-400" />
                                            <span>{item}</span>
                                        </li>
                                    ))}
                                </ul>
                            </div>
                        ))}
                    </div>
                </div>
            </section>

            {/* Tech Highlights */}
            <section className="py-12">
                <div className="max-w-6xl mx-auto px-6">
                    <div className="flex items-center justify-between mb-6">
                        <h2 className="text-2xl font-bold text-stone-100">Skills, Tools, and Libraries</h2>
                        <Link
                            href="/tech-stack"
                            className="text-sm text-emerald-400 hover:text-emerald-300 flex items-center gap-1"
                        >
                            Full stack map
                            <ArrowRight className="w-4 h-4" />
                        </Link>
                    </div>
                    <div className="flex flex-wrap gap-3">
                        {techBadges.map((tech) => (
                            <TechBadge key={tech} name={tech} />
                        ))}
                    </div>
                </div>
            </section>

            {/* CTA */}
            <section className="py-16">
                <div className="max-w-4xl mx-auto px-6 text-center">
                    <h2 className="text-3xl font-bold text-stone-100 mb-4">
                        Want the full experience?
                    </h2>
                    <p className="text-stone-400 mb-8">
                        The live demo is optimized for free-tier deployments. Clone the repo and run locally to
                        unlock the full stack and advanced workloads.
                    </p>
                    <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
                        <Link
                            href="/demo"
                            className="inline-flex items-center gap-2 px-8 py-4 bg-gradient-to-r from-emerald-600 to-emerald-500 text-stone-900 rounded-xl font-semibold text-lg hover:scale-[1.02] transition-all shadow-xl shadow-emerald-900/30"
                        >
                            View Live Demo
                        </Link>
                        <Link
                            href="https://github.com"
                            target="_blank"
                            className="inline-flex items-center gap-2 px-8 py-4 bg-stone-900 border border-stone-800 text-stone-300 rounded-xl font-medium hover:bg-stone-800 hover:text-white transition-all"
                        >
                            View Source
                        </Link>
                    </div>
                </div>
            </section>

            <SiteFooter />
        </div>
    );
}
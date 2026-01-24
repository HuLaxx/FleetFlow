'use client';

import { SiteHeader } from '@/components/site/site-header';
import { SiteFooter } from '@/components/site/site-footer';
import Link from 'next/link';
import { ArrowRight, Play, ExternalLink } from 'lucide-react';

// Using Simple Icons CDN for real logos
const getLogoUrl = (name: string) => {
    const slugMap: Record<string, string> = {
        'Next.js 16': 'nextdotjs',
        'React 19': 'react',
        'TypeScript': 'typescript',
        'Deck.gl': 'webgl',
        'MapLibre GL': 'maplibre',
        'Tailwind CSS': 'tailwindcss',
        'Framer Motion': 'framer',
        'tRPC': 'trpc',
        'FastAPI': 'fastapi',
        'Pydantic': 'pydantic',
        'SQLAlchemy': 'sqlalchemy',
        'Uvicorn': 'gunicorn',
        'Structlog': 'python',
        'Apache Kafka': 'apachekafka',
        'Apache Airflow': 'apacheairflow',
        'dbt': 'dbt',
        'Apache Flink': 'apacheflink',
        'Prophet': 'meta',
        'TensorFlow/Keras': 'tensorflow',
        'XGBoost': 'python',
        'OR-Tools': 'google',
        'MLflow': 'mlflow',
        'scikit-learn': 'scikitlearn',
        'PostgreSQL': 'postgresql',
        'PostGIS': 'postgresql',
        'TimescaleDB': 'timescale',
        'Redis': 'redis',
        'MongoDB': 'mongodb',
        'Docker': 'docker',
        'Docker Compose': 'docker',
        'GitHub Actions': 'githubactions',
        'Nginx': 'nginx',
    };
    const slug = slugMap[name] || name.toLowerCase().replace(/[^a-z0-9]/g, '');
    return `https://cdn.simpleicons.org/${slug}/white`;
};

// Tech Stack Categories - Mapped to Warm Tones
// Gradient: Black → Espresso Brown → Bronze → Gold → Champagne
const categories = [
    {
        name: 'Frontend',
        description: 'Modern React with real-time visualization',
        color: 'from-amber-600 to-amber-500', // Gold
        borderColor: 'border-amber-500/20',
        tools: [
            { name: 'Next.js 16', description: 'React framework with App Router', url: 'https://nextjs.org' },
            { name: 'React 19', description: 'Latest React with hooks', url: 'https://react.dev' },
            { name: 'TypeScript', description: 'Static typing for better DX', url: 'https://typescriptlang.org' },
            { name: 'Deck.gl', description: 'WebGL data visualization', url: 'https://deck.gl' },
            { name: 'MapLibre GL', description: 'Open-source map rendering', url: 'https://maplibre.org' },
            { name: 'Tailwind CSS', description: 'Utility-first CSS', url: 'https://tailwindcss.com' },
            { name: 'Framer Motion', description: 'Animation library', url: 'https://framer.com/motion' },
            { name: 'tRPC', description: 'End-to-end typesafe APIs', url: 'https://trpc.io' },
        ],
    },
    {
        name: 'Backend',
        description: 'High-performance Python APIs',
        color: 'from-orange-600 to-orange-500', // Orange-Bronze
        borderColor: 'border-orange-500/20',
        tools: [
            { name: 'FastAPI', description: 'Modern Python web framework', url: 'https://fastapi.tiangolo.com' },
            { name: 'Pydantic', description: 'Data validation using types', url: 'https://pydantic.dev' },
            { name: 'SQLAlchemy', description: 'Python SQL toolkit and ORM', url: 'https://sqlalchemy.org' },
            { name: 'Uvicorn', description: 'Lightning-fast ASGI server', url: 'https://uvicorn.org' },
        ],
    },
    {
        name: 'Data Engineering',
        description: 'Streaming and batch data pipelines',
        color: 'from-stone-500 to-stone-400', // Stone
        borderColor: 'border-stone-500/20',
        tools: [
            { name: 'Apache Kafka', description: 'Event streaming platform', url: 'https://kafka.apache.org' },
            { name: 'Apache Airflow', description: 'Workflow orchestration', url: 'https://airflow.apache.org' },
            { name: 'dbt', description: 'Data transformation with SQL', url: 'https://getdbt.com' },
            { name: 'Apache Flink', description: 'Stream processing', url: 'https://flink.apache.org' },
        ],
    },
    {
        name: 'Machine Learning',
        description: 'Forecasting and optimization models',
        color: 'from-yellow-600 to-yellow-500', // Deep Yellow
        borderColor: 'border-yellow-500/20',
        tools: [
            { name: 'Prophet', description: 'Time series forecasting', url: 'https://facebook.github.io/prophet' },
            { name: 'TensorFlow/Keras', description: 'Deep learning for LSTM', url: 'https://tensorflow.org' },
            { name: 'XGBoost', description: 'Gradient boosting', url: 'https://xgboost.readthedocs.io' },
            { name: 'OR-Tools', description: "Google's optimization suite", url: 'https://developers.google.com/optimization' },
            { name: 'MLflow', description: 'ML lifecycle management', url: 'https://mlflow.org' },
            { name: 'scikit-learn', description: 'ML in Python', url: 'https://scikit-learn.org' },
        ],
    },
    {
        name: 'Databases',
        description: 'Multi-model data storage',
        color: 'from-amber-700 to-amber-600', // Bronze
        borderColor: 'border-amber-700/20',
        tools: [
            { name: 'PostgreSQL', description: 'Advanced relational database', url: 'https://postgresql.org' },
            { name: 'PostGIS', description: 'Spatial database extender', url: 'https://postgis.net' },
            { name: 'TimescaleDB', description: 'Time-series database', url: 'https://timescale.com' },
            { name: 'Redis', description: 'In-memory data store', url: 'https://redis.io' },
            { name: 'MongoDB', description: 'Document database', url: 'https://mongodb.com' },
        ],
    },
    {
        name: 'DevOps',
        description: 'Containerization and deployment',
        color: 'from-stone-600 to-stone-500', // Dark Stone
        borderColor: 'border-stone-600/20',
        tools: [
            { name: 'Docker', description: 'Container platform', url: 'https://docker.com' },
            { name: 'Docker Compose', description: 'Multi-container orchestration', url: 'https://docs.docker.com/compose' },
            { name: 'GitHub Actions', description: 'CI/CD automation', url: 'https://github.com/features/actions' },
            { name: 'Nginx', description: 'Reverse proxy & load balancer', url: 'https://nginx.org' },
        ],
    },
];

export default function TechStackPage() {
    return (
        <div className="min-h-screen bg-stone-950">
            <SiteHeader />

            {/* Hero */}
            <section className="pt-32 pb-16 relative overflow-hidden">
                <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top,_var(--tw-gradient-stops))] from-stone-900/60 via-stone-950 to-stone-950" />
                <div className="max-w-7xl mx-auto px-6 relative z-10">
                    <div className="text-center max-w-3xl mx-auto">
                        <h1 className="text-4xl md:text-5xl font-bold text-stone-100 mb-4">
                            Technology Stack
                        </h1>
                        <p className="text-xl text-stone-400">
                            30+ production-ready technologies chosen for scalability,
                            performance, and developer experience.
                        </p>
                    </div>
                </div>
            </section>

            {/* Tech Categories */}
            <section className="py-12 relative">
                <div className="max-w-7xl mx-auto px-6 space-y-16">
                    {categories.map((category) => (
                        <div key={category.name}>
                            <div className="flex items-center gap-4 mb-8">
                                <div className={`w-12 h-12 rounded-xl bg-gradient-to-br ${category.color} flex items-center justify-center shadow-lg`}>
                                    <span className="text-xl font-bold text-stone-900 shadow-sm">{category.name.charAt(0)}</span>
                                </div>
                                <div>
                                    <h2 className="text-2xl font-bold text-stone-100">{category.name}</h2>
                                    <p className="text-stone-500">{category.description}</p>
                                </div>
                            </div>

                            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
                                {category.tools.map((tool) => (
                                    <a
                                        key={tool.name}
                                        href={tool.url}
                                        target="_blank"
                                        rel="noopener noreferrer"
                                        className={`group relative bg-stone-900/60 border ${category.borderColor} rounded-xl p-5 hover:bg-stone-900 hover:border-opacity-100 hover:scale-[1.02] transition-all flex items-start gap-4 shadow-sm hover:shadow-lg`}
                                    >
                                        {/* Logo */}
                                        <div className="w-10 h-10 rounded-lg bg-stone-800/80 flex items-center justify-center flex-shrink-0 overflow-hidden">
                                            <img
                                                src={getLogoUrl(tool.name)}
                                                alt={tool.name}
                                                className="w-6 h-6 opacity-80 group-hover:opacity-100 transition-opacity"
                                                onError={(e) => {
                                                    (e.target as HTMLImageElement).style.display = 'none';
                                                }}
                                            />
                                        </div>

                                        {/* Content */}
                                        <div className="flex-1 min-w-0">
                                            <div className="flex items-center gap-2">
                                                <h3 className="font-semibold text-stone-100 group-hover:text-amber-400 transition-colors truncate">
                                                    {tool.name}
                                                </h3>
                                                <ExternalLink className="w-3 h-3 text-stone-600 group-hover:text-amber-400 flex-shrink-0 opacity-0 group-hover:opacity-100 transition-opacity" />
                                            </div>
                                            <p className="text-sm text-stone-500 leading-relaxed mt-1">
                                                {tool.description}
                                            </p>
                                        </div>
                                    </a>
                                ))}
                            </div>
                        </div>
                    ))}
                </div>
            </section>

            {/* Stats */}
            <section className="py-16 bg-stone-900/20 border-y border-stone-900">
                <div className="max-w-7xl mx-auto px-6">
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
                        {[
                            { value: '30+', label: 'Technologies' },
                            { value: '8', label: 'Docker Services' },
                            { value: '6', label: 'ML Models' },
                            { value: '5', label: 'Databases' },
                        ].map((stat) => (
                            <div key={stat.label} className="text-center">
                                <p className="text-4xl font-bold bg-gradient-to-r from-amber-500 to-orange-500 bg-clip-text text-transparent">
                                    {stat.value}
                                </p>
                                <p className="text-stone-500">{stat.label}</p>
                            </div>
                        ))}
                    </div>
                </div>
            </section>

            {/* CTA */}
            <section className="py-16">
                <div className="max-w-4xl mx-auto px-6 text-center">
                    <Link
                        href="/demo"
                        className="inline-flex items-center gap-2 px-8 py-4 bg-gradient-to-r from-amber-600 to-amber-500 text-stone-900 rounded-xl font-semibold text-lg hover:scale-[1.02] transition-all shadow-xl shadow-amber-900/30"
                    >
                        <Play className="w-5 h-5 fill-current" />
                        Try the Demo
                    </Link>
                </div>
            </section>

            <SiteFooter />
        </div>
    );
}

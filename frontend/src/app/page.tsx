'use client';

import Link from 'next/link';
import {
  ArrowRight,
  Truck,
  BarChart3,
  Clock,
  Zap,
  Map,
  Database,
  Shield,
  Bot,
  CheckCircle,
  Activity,
  Code
} from 'lucide-react';
import { SiteHeader } from '@/components/site/site-header';
import { SiteFooter } from '@/components/site/site-footer';
import { DeploymentNotice } from '@/components/site/deployment-notice';
import { motion } from 'framer-motion';

// Tech Stack Logos (using placeholders for now, in real app use SVGs)
const TechBadge = ({ name }: { name: string }) => (
  <div className="px-3 py-1.5 rounded-full bg-stone-900 border border-stone-800 text-xs font-medium text-stone-400 hover:text-emerald-400 hover:border-emerald-500/20 transition-all cursor-default">
    {name}
  </div>
);

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-stone-950 flex flex-col font-sans selection:bg-emerald-500/30">
      <SiteHeader />

      {/* Hero Section */}
      <section className="relative pt-32 pb-20 overflow-hidden">
        {/* Background Effects */}
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top,_var(--tw-gradient-stops))] from-stone-900 via-stone-950 to-black" />
        <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[800px] h-[500px] bg-emerald-600/10 blur-[120px] rounded-full opacity-50" />

        <div className="max-w-7xl mx-auto px-6 relative z-10 text-center">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8 }}
          >
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-stone-900/50 border border-emerald-500/20 text-xs font-medium text-emerald-200 mb-8 shadow-[0_0_15px_-3px_rgba(16,185,129,0.15)]">
              <span className="relative flex h-2 w-2">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
              </span>
              Live Demo • Free-tier deploy
            </div>

            <h1 className="text-5xl md:text-7xl font-bold tracking-tight text-white mb-6">
              Next-Gen Delivery <br />
              <span className="bg-gradient-to-r from-emerald-200 via-emerald-400 to-emerald-600 bg-clip-text text-transparent drop-shadow-sm">
                Optimization Platform
              </span>
            </h1>

            <p className="text-xl text-stone-400 max-w-2xl mx-auto mb-10 leading-relaxed">
              Enterprise-grade logistics engine powered by predictive ML and real-time event streaming.
              Reduce delivery times by <span className="text-emerald-400 font-semibold">23%</span>.
            </p>

            <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
              <Link
                href="/demo"
                className="group relative inline-flex items-center gap-2 px-8 py-4 bg-gradient-to-r from-emerald-600 to-emerald-500 text-white rounded-xl font-semibold text-lg hover:brightness-110 hover:scale-[1.02] transition-all shadow-lg shadow-emerald-900/30 overflow-hidden"
              >
                <div className="absolute inset-0 bg-white/20 translate-y-full group-hover:translate-y-0 transition-transform duration-300" />
                Launch Demo
                <ArrowRight className="w-5 h-5 group-hover:translate-x-1 transition-transform" />
              </Link>

              <Link
                href="/architecture"
                className="inline-flex items-center gap-2 px-8 py-4 bg-stone-900 border border-stone-800 text-stone-300 rounded-xl font-medium hover:bg-stone-800 hover:text-emerald-400 hover:border-emerald-500/20 transition-all"
              >
                View Architecture
              </Link>
            </div>
          </motion.div>

          {/* Deployment Notice */}
          <div className="mt-10">
            <DeploymentNotice variant="hero" />
          </div>

          {/* Stats */}
          <motion.div
            initial={{ opacity: 0, y: 40 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8, delay: 0.2 }}
            className="grid grid-cols-2 md:grid-cols-4 gap-8 mt-20 border-t border-stone-900 pt-10"
          >
            {[
              { label: 'Latency', value: '< 800ms', icon: Clock },
              { label: 'Data Points', value: '1M+/day', icon: Database },
              { label: 'Prediction Accuracy', value: '94%', icon: BarChart3 },
              { label: 'Uptime', value: '99.99%', icon: Shield },
            ].map((stat) => (
              <div key={stat.label} className="flex flex-col items-center">
                <div className="w-10 h-10 rounded-full bg-stone-900/50 border border-emerald-900/30 flex items-center justify-center mb-3 text-emerald-500">
                  <stat.icon className="w-5 h-5" />
                </div>
                <div className="text-2xl font-bold text-stone-100">{stat.value}</div>
                <div className="text-sm text-stone-500">{stat.label}</div>
              </div>
            ))}
          </motion.div>
        </div>
      </section>

      {/* Product Modules */}
      <section className="py-20 relative">
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_bottom,_var(--tw-gradient-stops))] from-emerald-900/15 via-transparent to-transparent" />
        <div className="max-w-7xl mx-auto px-6 relative">
          <div className="text-center mb-14">
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-stone-900/60 border border-emerald-500/20 text-xs font-medium text-emerald-200 mb-4">
              Product Surface
            </div>
            <h2 className="text-3xl md:text-4xl font-bold text-white mb-4">
              Dispatch-ready modules, stitched end-to-end.
            </h2>
            <p className="text-stone-400 max-w-2xl mx-auto">
              Built for ops teams: fast reroutes, live visibility, and optimization that feels immediate.
            </p>
          </div>

          <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-6">
            {[
              {
                title: 'Dispatch Console',
                desc: 'Assign, reroute, and manage exceptions in seconds.',
                icon: Truck,
                color: 'text-emerald-400',
                border: 'group-hover:border-emerald-500/30'
              },
              {
                title: 'Route Intelligence',
                desc: 'Constraint-based VRP solver with live recalculation.',
                icon: Map,
                color: 'text-teal-400',
                border: 'group-hover:border-teal-500/30'
              },
              {
                title: 'Predictive Demand',
                desc: 'Forecast load spikes and rebalance capacity early.',
                icon: BarChart3,
                color: 'text-green-400',
                border: 'group-hover:border-green-500/30'
              },
              {
                title: 'Streaming Telemetry',
                desc: 'Real-time events power the dashboard and alerts.',
                icon: Zap,
                color: 'text-emerald-300',
                border: 'group-hover:border-emerald-400/30'
              },
            ].map((module) => (
              <div
                key={module.title}
                className={`group p-7 rounded-2xl bg-stone-900 border border-stone-800 transition-all hover:bg-stone-800/80 ${module.border} hover:shadow-lg hover:shadow-emerald-900/10`}
              >
                <div className="w-12 h-12 rounded-xl bg-stone-950 flex items-center justify-center mb-5">
                  <module.icon className={`w-6 h-6 ${module.color}`} />
                </div>
                <h3 className="text-lg font-bold text-stone-100 mb-2 group-hover:text-emerald-100 transition-colors">
                  {module.title}
                </h3>
                <p className="text-stone-500 text-sm leading-relaxed">
                  {module.desc}
                </p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Features Grid */}
      <section id="features" className="py-24 relative">
        <div className="max-w-7xl mx-auto px-6">
          <div className="text-center mb-16">
            <h2 className="text-3xl font-bold text-white mb-4">Production-Grade Architecture</h2>
            <p className="text-stone-400 max-w-2xl mx-auto">
              Built with a modern stack designed for high-throughput data processing and real-time inference.
            </p>
          </div>

          <div className="grid md:grid-cols-3 gap-6">
            {[
              {
                title: 'Predictive Forecasting',
                desc: 'Prophet + LSTM models triggered via Airflow to predict demand hotspots.',
                icon: Bot,
                color: 'text-emerald-400',
                border: 'group-hover:border-emerald-500/30'
              },
              {
                title: 'Real-Time Optimization',
                desc: 'OR-Tools VRP engine re-calculates routes in milliseconds upon new events.',
                icon: Map,
                color: 'text-teal-400',
                border: 'group-hover:border-teal-500/30'
              },
              {
                title: 'Event-Driven Core',
                desc: 'Apache Kafka & Flink handle high-volume telemetry ingestion.',
                icon: Zap,
                color: 'text-green-400',
                border: 'group-hover:border-green-500/30'
              },
            ].map((feature) => (
              <div
                key={feature.title}
                className={`group p-8 rounded-2xl bg-stone-900 border border-stone-800 transition-all hover:bg-stone-800/80 ${feature.border} hover:shadow-lg hover:shadow-emerald-900/10`}
              >
                <div className={`w-12 h-12 rounded-xl bg-stone-950 flex items-center justify-center mb-6`}>
                  <feature.icon className={`w-6 h-6 ${feature.color}`} />
                </div>
                <h3 className="text-xl font-bold text-stone-100 mb-3 group-hover:text-emerald-100 transition-colors">
                  {feature.title}
                </h3>
                <p className="text-stone-500 leading-relaxed">
                  {feature.desc}
                </p>
              </div>
            ))}
          </div>

          {/* Tech Ticker */}
          <div className="mt-16 flex flex-wrap justify-center gap-3 opacity-70">
            {['Next.js 16', 'TypeScript', 'FastAPI', 'Kafka', 'PostGIS', 'Docker', 'tRPC', 'Tailwind', 'OR-Tools'].map(tech => (
              <TechBadge key={tech} name={tech} />
            ))}
          </div>
        </div>
      </section>

      {/* Operational Snapshot */}
      <section className="py-16 px-6">
        <div className="max-w-5xl mx-auto">
          <div className="p-8 rounded-2xl border border-stone-800 bg-stone-900/50">
            <div className="flex items-center gap-3 mb-6">
              <Activity className="w-6 h-6 text-emerald-200" />
              <h3 className="text-xl font-semibold text-stone-100">Operational Snapshot</h3>
              <span className="ml-auto px-3 py-1 rounded-full bg-stone-800/80 text-emerald-100/80 text-xs font-medium">
                Local Capabilities
              </span>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {[
                'Kafka streams ingest GPS + order events in real time',
                'OR-Tools solver reroutes on new exceptions',
                'ETA prediction service scores every active stop',
                'Dispatch actions logged with audit-ready history',
                'WebSocket feeds keep the map live and reactive',
                'PostGIS indexing powers geo-queries and heatmaps',
              ].map((item) => (
                <div
                  key={item}
                  className="flex items-center gap-3 p-3 rounded-lg hover:bg-stone-800/50 transition-colors"
                >
                  <CheckCircle className="w-4 h-4 text-emerald-200 flex-shrink-0" />
                  <span className="text-sm text-stone-400">{item}</span>
                </div>
              ))}
            </div>

            <p className="text-xs text-stone-500 mt-4">
              Each capability maps to code in this repo. Local runs show the full stack; the hosted demo stays lightweight.
            </p>
          </div>
        </div>
      </section>

      {/* Developer API */}
      <section className="py-20 relative overflow-hidden">
        <div className="relative max-w-6xl mx-auto px-6">
          <div className="grid lg:grid-cols-2 gap-12 items-center">
            <div className="space-y-6">
              <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-stone-900/70 border border-stone-800 text-emerald-100 text-sm">
                <Code className="w-4 h-4" />
                Dispatch API
              </div>
              <h2 className="text-3xl md:text-5xl font-bold leading-tight text-stone-100">
                Optimization endpoints built for ops tooling.
              </h2>
              <p className="text-lg text-stone-400 leading-relaxed">
                Integrate with your OMS or TMS using a FastAPI layer that exposes routing,
                status, and exception handling.
              </p>
              <ul className="space-y-3 text-stone-400 text-sm">
                {[
                  'Optimize routes with capacity and time-window constraints',
                  'Pull live fleet status with per-stop ETAs',
                  'Post dispatch actions with full audit trails',
                ].map((item) => (
                  <li key={item} className="flex items-start gap-3">
                    <div className="w-5 h-5 rounded-full bg-stone-800 flex items-center justify-center mt-0.5">
                      <CheckCircle className="w-3 h-3 text-emerald-200" />
                    </div>
                    <span>{item}</span>
                  </li>
                ))}
              </ul>
            </div>

            <div className="relative group">
              <div className="absolute -inset-1 bg-gradient-to-r from-emerald-900/30 to-emerald-400/20 rounded-xl blur opacity-30 group-hover:opacity-40 transition duration-1000" />
              <div className="relative rounded-xl border border-stone-800 bg-[#0D0F10] p-6 shadow-2xl">
                <div className="flex items-center justify-between mb-4 border-b border-stone-800 pb-4">
                  <div className="flex gap-2">
                    <div className="w-3 h-3 rounded-full bg-red-500/20 border border-red-500/50" />
                    <div className="w-3 h-3 rounded-full bg-yellow-500/20 border border-yellow-500/50" />
                    <div className="w-3 h-3 rounded-full bg-green-500/20 border border-green-500/50" />
                  </div>
                  <span className="text-xs text-stone-500 font-mono">POST /routes/optimize</span>
                </div>

                <pre className="font-mono text-xs sm:text-sm leading-relaxed overflow-x-auto text-emerald-100/90">
                  <code>{`curl -X POST http://localhost:8000/routes/optimize \\
  -H "Content-Type: application/json" \\
  -d '{
    "depot_id": "hub_12",
    "stops": 48,
    "constraints": ["capacity", "time_window"]
  }'`}</code>
                </pre>

                <div className="mt-4 pt-4 border-t border-stone-800/50">
                  <div className="text-xs text-stone-500 mb-2">Response (200 OK)</div>
                  <pre className="font-mono text-xs leading-relaxed text-emerald-100/90">
                    <code>{`{
  "optimized_routes": 12,
  "total_miles_saved": 84.5,
  "eta_delta_minutes": -18
}`}</code>
                  </pre>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      <SiteFooter />
    </div>
  );
}

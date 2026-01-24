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
  Bot
} from 'lucide-react';
import { SiteHeader } from '@/components/site/site-header';
import { SiteFooter } from '@/components/site/site-footer';
import { motion } from 'framer-motion';

// Tech Stack Logos (using placeholders for now, in real app use SVGs)
const TechBadge = ({ name }: { name: string }) => (
  <div className="px-3 py-1.5 rounded-full bg-stone-900 border border-stone-800 text-xs font-medium text-stone-400 hover:text-amber-400 hover:border-amber-500/20 transition-all cursor-default">
    {name}
  </div>
);

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-stone-950 flex flex-col font-sans selection:bg-amber-500/30">
      <SiteHeader />

      {/* Hero Section */}
      <section className="relative pt-32 pb-20 overflow-hidden">
        {/* Background Effects */}
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top,_var(--tw-gradient-stops))] from-stone-900 via-stone-950 to-black" />
        <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[800px] h-[500px] bg-amber-600/10 blur-[120px] rounded-full opacity-50" />

        <div className="max-w-7xl mx-auto px-6 relative z-10 text-center">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8 }}
          >
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-stone-900/50 border border-amber-500/20 text-xs font-medium text-amber-200 mb-8 shadow-[0_0_15px_-3px_rgba(245,158,11,0.15)]">
              <span className="relative flex h-2 w-2">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-amber-400 opacity-75"></span>
                <span className="relative inline-flex rounded-full h-2 w-2 bg-amber-500"></span>
              </span>
              Live Production v1.2
            </div>

            <h1 className="text-5xl md:text-7xl font-bold tracking-tight text-white mb-6">
              Next-Gen Delivery <br />
              <span className="bg-gradient-to-r from-amber-200 via-amber-400 to-amber-600 bg-clip-text text-transparent drop-shadow-sm">
                Optimization Platform
              </span>
            </h1>

            <p className="text-xl text-stone-400 max-w-2xl mx-auto mb-10 leading-relaxed">
              Enterprise-grade logistics engine powered by predictive ML and real-time event streaming.
              Reduce delivery times by <span className="text-amber-400 font-semibold">23%</span>.
            </p>

            <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
              <Link
                href="/demo"
                className="group relative inline-flex items-center gap-2 px-8 py-4 bg-gradient-to-r from-amber-600 to-amber-500 text-white rounded-xl font-semibold text-lg hover:brightness-110 hover:scale-[1.02] transition-all shadow-lg shadow-amber-900/30 overflow-hidden"
              >
                <div className="absolute inset-0 bg-white/20 translate-y-full group-hover:translate-y-0 transition-transform duration-300" />
                Launch Demo
                <ArrowRight className="w-5 h-5 group-hover:translate-x-1 transition-transform" />
              </Link>

              <Link
                href="/architecture"
                className="inline-flex items-center gap-2 px-8 py-4 bg-stone-900 border border-stone-800 text-stone-300 rounded-xl font-medium hover:bg-stone-800 hover:text-amber-400 hover:border-amber-500/20 transition-all"
              >
                View Architecture
              </Link>
            </div>
          </motion.div>

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
                <div className="w-10 h-10 rounded-full bg-stone-900/50 border border-amber-900/30 flex items-center justify-center mb-3 text-amber-500">
                  <stat.icon className="w-5 h-5" />
                </div>
                <div className="text-2xl font-bold text-stone-100">{stat.value}</div>
                <div className="text-sm text-stone-500">{stat.label}</div>
              </div>
            ))}
          </motion.div>
        </div>
      </section>

      {/* Demo Preview */}
      <section className="py-24 relative">
        <div className="max-w-7xl mx-auto px-6">
          <div className="relative rounded-2xl border border-stone-800 bg-stone-900/50 p-2 shadow-2xl shadow-black/50 overflow-hidden group">
            <div className="absolute top-0 left-0 w-full h-full bg-gradient-to-br from-amber-500/5 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-1000" />
            <div className="rounded-xl overflow-hidden bg-stone-950 aspect-[16/9] relative">
              {/* Mock Dashboard UI - Visual representation */}
              <div className="absolute inset-0 flex items-center justify-center">
                <div className="text-center">
                  <div className="w-20 h-20 rounded-2xl bg-gradient-to-br from-stone-800 to-stone-900 border border-stone-700 flex items-center justify-center mx-auto mb-4 shadow-lg">
                    <Truck className="w-10 h-10 text-amber-500" />
                  </div>
                  <h3 className="text-2xl font-bold text-stone-200">Interactive Dispatcher</h3>
                  <p className="text-stone-500 mt-2">Live tracking & route optimization</p>
                  <div className="mt-6 flex justify-center gap-2">
                    <div className="w-2 h-2 rounded-full bg-amber-500 animate-pulse" />
                    <span className="text-xs text-amber-500 font-mono tracking-wider">SYSTEM ONLINE</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Features Grid */}
      <section className="py-24 bg-stone-900/30 relative">
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
                color: 'text-amber-400',
                border: 'group-hover:border-amber-500/30'
              },
              {
                title: 'Real-Time Optimization',
                desc: 'OR-Tools VRP engine re-calculates routes in milliseconds upon new events.',
                icon: Map,
                color: 'text-orange-400',
                border: 'group-hover:border-orange-500/30'
              },
              {
                title: 'Event-Driven Core',
                desc: 'Apache Kafka & Flink handle high-volume telemetry ingestion.',
                icon: Zap,
                color: 'text-yellow-400',
                border: 'group-hover:border-yellow-500/30'
              },
            ].map((feature) => (
              <div
                key={feature.title}
                className={`group p-8 rounded-2xl bg-stone-900 border border-stone-800 transition-all hover:bg-stone-800/80 ${feature.border} hover:shadow-lg hover:shadow-amber-900/10`}
              >
                <div className={`w-12 h-12 rounded-xl bg-stone-950 flex items-center justify-center mb-6`}>
                  <feature.icon className={`w-6 h-6 ${feature.color}`} />
                </div>
                <h3 className="text-xl font-bold text-stone-100 mb-3 group-hover:text-amber-100 transition-colors">
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

      {/* CTA */}
      <section className="py-24 relative overflow-hidden">
        <div className="absolute inset-0 bg-stone-950" />
        <div className="absolute inset-0 bg-[linear-gradient(rgba(245,158,11,0.03)_1px,transparent_1px),linear-gradient(90deg,rgba(245,158,11,0.03)_1px,transparent_1px)] bg-[size:64px_64px] [mask-image:radial-gradient(ellipse_at_center,black_50%,transparent_90%)]" />

        <div className="max-w-4xl mx-auto px-6 relative z-10 text-center">
          <h2 className="text-4xl font-bold text-white mb-6">
            Ready to optimize your fleet?
          </h2>
          <p className="text-stone-400 mb-10 text-lg">
            Explore the interactive demo to see the real-time decision engine in action,
            or dive into the system architecture.
          </p>
          <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
            <Link
              href="/demo"
              className="inline-flex items-center gap-2 px-8 py-4 bg-amber-500 text-stone-950 rounded-xl font-bold text-lg hover:bg-amber-400 transition-colors shadow-xl shadow-amber-500/20"
            >
              <Truck className="w-5 h-5" />
              Launch Demo
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

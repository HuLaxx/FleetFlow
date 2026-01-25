"use client";

import Link from 'next/link';
import { Truck, Github, Linkedin, Mail } from 'lucide-react';

const pageLinks = [
    { label: 'Home', href: '/' },
    { label: 'Portfolio', href: '/portfolio' },
    { label: 'Architecture', href: '/architecture' },
    { label: 'Tech Stack', href: '/tech-stack' },
    { label: 'Demo', href: '/demo' },
];

const connectLinks = [
    { icon: Github, label: 'GitHub', href: 'https://github.com/HuLaxx/FleetFlow' },
    { icon: Linkedin, label: 'LinkedIn', href: 'https://www.linkedin.com/in/rahul-khanke-853717218/' },
    { icon: Mail, label: 'Email', href: 'mailto:rahulkhane786@gmail.com' },
];

export function SiteFooter() {
    const currentYear = new Date().getFullYear();

    return (
        <footer className="relative z-10 m-4 md:m-8 mt-auto rounded-3xl overflow-hidden border border-white/5 bg-stone-950/70 backdrop-blur-3xl shadow-2xl">
            <div className="px-8 lg:px-12 py-16 md:py-24">
                <div className="max-w-7xl mx-auto">
                    {/* Main Grid */}
                    <div className="grid md:grid-cols-4 gap-12 lg:gap-24">
                        {/* Brand Column */}
                        <div className="md:col-span-2 space-y-6">
                            <Link href="/" className="flex items-center gap-3 group">
                                <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-emerald-500 to-emerald-400 flex items-center justify-center shadow-lg shadow-emerald-500/15 group-hover:shadow-emerald-500/30 transition-all duration-300 group-hover:scale-105">
                                    <Truck className="w-6 h-6 text-stone-900" />
                                </div>
                                <span className="text-2xl font-bold bg-gradient-to-r from-emerald-100 to-emerald-400 bg-clip-text text-transparent">
                                    FleetFlow
                                </span>
                            </Link>
                            <p className="text-stone-400 max-w-sm leading-relaxed text-sm">
                                Enterprise-grade real-time delivery optimization platform.
                                ML-powered route optimization, demand forecasting, and fleet tracking.
                            </p>
                        </div>

                        {/* Pages Column */}
                        <div>
                            <h3 className="font-bold text-sm uppercase tracking-wider text-emerald-100 mb-6">
                                Pages
                            </h3>
                            <ul className="space-y-4 text-sm text-stone-400">
                                {pageLinks.map((link) => (
                                    <li key={link.href}>
                                        <Link
                                            href={link.href}
                                            className="hover:text-emerald-200 transition-colors"
                                        >
                                            {link.label}
                                        </Link>
                                    </li>
                                ))}
                            </ul>
                        </div>

                        {/* Connect Column */}
                        <div>
                            <h3 className="font-bold text-sm uppercase tracking-wider text-emerald-100 mb-6">
                                Connect
                            </h3>
                            <ul className="space-y-4 text-sm text-stone-400">
                                {connectLinks.map((link) => (
                                    <li key={link.label}>
                                        <a
                                            href={link.href}
                                            target="_blank"
                                            rel="noopener noreferrer"
                                            className="hover:text-emerald-200 transition-colors flex items-center gap-2 group"
                                        >
                                            <link.icon className="w-4 h-4 group-hover:scale-110 transition-transform" />
                                            {link.label}
                                        </a>
                                    </li>
                                ))}
                            </ul>
                        </div>
                    </div>
                </div>

                {/* Bottom Bar */}
                <div className="max-w-7xl mx-auto pt-12 mt-12 border-t border-white/5 flex flex-col md:flex-row items-center justify-between gap-6 text-sm text-stone-500">
                    <p>© {currentYear} FleetFlow. All rights reserved.</p>
                    <button
                        type="button"
                        onClick={() => window.scrollTo({ top: 0, behavior: 'smooth' })}
                        className="text-emerald-100/60 hover:text-emerald-100 transition-colors"
                    >
                        Back to top
                    </button>
                    <a
                        href="https://hulax.vercel.app"
                        target="_blank"
                        rel="noreferrer"
                        className="group inline-flex items-baseline gap-1.5 md:mr-6"
                    >
                        <span className="hulax-credit-label text-sm text-emerald-100/60 transition-all duration-300 group-hover:text-emerald-100 group-hover:drop-shadow-[0_0_8px_rgba(16,185,129,0.35)]">
                            A Project By
                        </span>
                        <span className="hulax-credit hulax-credit-gradient text-base sm:text-lg transition-all duration-300 origin-left group-hover:font-semibold">
                            HuLaX
                        </span>
                    </a>
                </div>
            </div>
        </footer>
    );
}

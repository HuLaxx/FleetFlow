'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useState, useEffect } from 'react';
import { Menu, X, Github, Truck, ExternalLink } from 'lucide-react';

const navLinks = [
    { href: '/#features', label: 'Features' },
    { href: '/architecture', label: 'Architecture' },
    { href: '/tech-stack', label: 'Tech Stack' },
    { href: '/demo', label: 'Live Demo', highlight: true },
];

export function SiteHeader() {
    const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
    const [scrolled, setScrolled] = useState(false);
    const pathname = usePathname();

    // Critical: Hide header on demo page to prevent overlap with dashboard
    if (pathname === '/demo') return null;

    // Scroll listener to toggle glassmorphism effect
    useEffect(() => {
        const handleScroll = () => {
            setScrolled(window.scrollY > 20);
        };
        window.addEventListener('scroll', handleScroll);
        return () => window.removeEventListener('scroll', handleScroll);
    }, []);

    return (
        <header
            className={`fixed top-4 left-0 right-0 z-50 transition-all duration-300 px-4 flex justify-center`}
        >
            <div
                className={`w-full max-w-6xl transition-all duration-300 rounded-2xl border ${scrolled
                    ? 'bg-stone-950/90 backdrop-blur-xl border-stone-800 shadow-xl shadow-black/20 py-1'
                    : 'bg-transparent border-transparent py-2'
                    }`}
            >
                <div className="px-6 flex items-center justify-between h-14">
                    {/* Logo Section */}
                    <Link href="/" className="flex items-center gap-3 group">
                        <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-stone-800 to-stone-900 flex items-center justify-center shadow-lg shadow-black/20 group-hover:shadow-amber-900/20 group-hover:scale-105 transition-all border border-white/5">
                            <Truck className="w-5 h-5 text-amber-500" />
                        </div>
                        <div className="flex flex-col">
                            <span className="text-lg font-bold bg-gradient-to-r from-amber-200 to-amber-500 bg-clip-text text-transparent">
                                FleetFlow
                            </span>
                        </div>
                    </Link>

                    {/* Desktop Navigation */}
                    <nav className="hidden md:flex items-center gap-1">
                        {navLinks.map((link) => {
                            const isActive = pathname === link.href;

                            // Highlighted 'Call to Action' button style
                            if (link.highlight) {
                                return (
                                    <Link
                                        key={link.href}
                                        href={link.href}
                                        className="ml-2 flex items-center gap-2 px-5 py-2 text-sm font-medium bg-gradient-to-r from-amber-600 to-amber-500 text-stone-900 rounded-full hover:from-amber-500 hover:to-amber-400 transition-all shadow-lg shadow-amber-500/20 hover:shadow-amber-500/40"
                                    >
                                        {link.label}
                                        <ExternalLink className="w-3 h-3 text-stone-900/70" />
                                    </Link>
                                );
                            }

                            // Standard Nav Link style
                            return (
                                <Link
                                    key={link.href}
                                    href={link.href}
                                    className={`px-4 py-2 text-sm transition-all rounded-full hover:bg-stone-800/50 ${isActive
                                        ? 'text-amber-500 font-medium'
                                        : 'text-stone-400 hover:text-amber-200'
                                        }`}
                                >
                                    {link.label}
                                </Link>
                            );
                        })}
                    </nav>

                    {/* Desktop Actions (Socials) */}
                    <div className="hidden md:flex items-center gap-3">
                        <a
                            href="https://github.com"
                            target="_blank"
                            rel="noopener noreferrer"
                            className="flex items-center gap-2 px-3 py-2 text-sm text-stone-400 hover:text-stone-100 transition-colors rounded-full hover:bg-stone-800/50"
                        >
                            <Github className="w-4 h-4" />
                            <span>GitHub</span>
                        </a>
                    </div>

                    {/* Mobile Menu Toggle */}
                    <button
                        onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
                        className="md:hidden p-2 text-stone-400 hover:text-stone-100 hover:bg-stone-800 rounded-lg transition-colors"
                    >
                        {mobileMenuOpen ? <X className="w-6 h-6" /> : <Menu className="w-6 h-6" />}
                    </button>
                </div>

                {/* Mobile Dropdown Menu */}
                {mobileMenuOpen && (
                    <div className="md:hidden px-4 pb-4 pt-2 border-t border-stone-800">
                        <nav className="flex flex-col gap-1">
                            {navLinks.map((link) => (
                                <Link
                                    key={link.href}
                                    href={link.href}
                                    onClick={() => setMobileMenuOpen(false)}
                                    className={`px-4 py-3 text-sm rounded-lg transition-colors ${pathname === link.href
                                        ? 'text-amber-400 bg-amber-900/10'
                                        : 'text-stone-400 hover:text-stone-100 hover:bg-stone-800/50'
                                        }`}
                                >
                                    {link.label}
                                </Link>
                            ))}
                            <a
                                href="https://github.com"
                                target="_blank"
                                rel="noopener noreferrer"
                                className="flex items-center gap-2 px-4 py-3 text-sm text-stone-400 hover:text-stone-100"
                            >
                                <Github className="w-4 h-4" />
                                GitHub
                            </a>
                        </nav>
                    </div>
                )}
            </div>
        </header>
    );
}

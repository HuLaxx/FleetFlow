import Link from 'next/link';
import { Truck, Github, Linkedin, Twitter } from 'lucide-react';

const footerLinks = {
    product: [
        { label: 'Features', href: '/#features' },
        { label: 'Architecture', href: '/architecture' },
        { label: 'Tech Stack', href: '/tech-stack' },
        { label: 'Live Demo', href: '/demo' },
    ],
    resources: [
        { label: 'Documentation', href: '#' },
        { label: 'API Reference', href: '#' },
        { label: 'Case Studies', href: '#' },
    ],
    company: [
        { label: 'About', href: '#' },
        { label: 'Blog', href: '#' },
        { label: 'Contact', href: '#' },
    ],
};

const socialLinks = [
    { icon: Github, href: 'https://github.com', label: 'GitHub' },
    { icon: Linkedin, href: 'https://linkedin.com', label: 'LinkedIn' },
    { icon: Twitter, href: 'https://twitter.com', label: 'Twitter' },
];

export function SiteFooter() {
    return (
        <footer className="bg-stone-950 border-t border-stone-900 border-t-emerald-900/10">
            <div className="max-w-7xl mx-auto px-6 py-20 pb-24">
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-12">
                    {/* Brand */}
                    <div className="lg:col-span-2">
                        <Link href="/" className="flex items-center gap-3 mb-4 group">
                            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-emerald-600 to-emerald-500 flex items-center justify-center shadow-lg shadow-emerald-900/20 border border-emerald-500/20 group-hover:scale-105 transition-all">
                                <Truck className="w-5 h-5 text-stone-900" />
                            </div>
                            <span className="text-xl font-bold text-stone-100 group-hover:text-emerald-400 transition-colors">
                                FleetFlow
                            </span>
                        </Link>
                        <p className="text-stone-500 text-sm max-w-sm mb-6">
                            Enterprise-grade real-time delivery optimization platform.
                            ML-powered route optimization, demand forecasting, and fleet tracking.
                        </p>
                        <div className="flex gap-4">
                            {socialLinks.map((social) => (
                                <a
                                    key={social.label}
                                    href={social.href}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    className="w-10 h-10 rounded-lg bg-stone-900 border border-stone-800 flex items-center justify-center text-stone-500 hover:text-emerald-400 hover:border-emerald-500/50 hover:bg-stone-800 transition-all shadow-md hover:shadow-emerald-900/10"
                                    aria-label={social.label}
                                >
                                    <social.icon className="w-5 h-5" />
                                </a>
                            ))}
                        </div>
                    </div>

                    {/* Links */}
                    <div>
                        <h3 className="text-sm font-semibold text-stone-100 mb-4">Product</h3>
                        <ul className="space-y-3">
                            {footerLinks.product.map((link) => (
                                <li key={link.label}>
                                    <Link
                                        href={link.href}
                                        className="text-sm text-stone-500 hover:text-emerald-200 transition-colors"
                                    >
                                        {link.label}
                                    </Link>
                                </li>
                            ))}
                        </ul>
                    </div>

                    <div>
                        <h3 className="text-sm font-semibold text-stone-100 mb-4">Resources</h3>
                        <ul className="space-y-3">
                            {footerLinks.resources.map((link) => (
                                <li key={link.label}>
                                    <Link
                                        href={link.href}
                                        className="text-sm text-stone-500 hover:text-emerald-200 transition-colors"
                                    >
                                        {link.label}
                                    </Link>
                                </li>
                            ))}
                        </ul>
                    </div>

                    <div>
                        <h3 className="text-sm font-semibold text-stone-100 mb-4">Company</h3>
                        <ul className="space-y-3">
                            {footerLinks.company.map((link) => (
                                <li key={link.label}>
                                    <Link
                                        href={link.href}
                                        className="text-sm text-stone-500 hover:text-emerald-200 transition-colors"
                                    >
                                        {link.label}
                                    </Link>
                                </li>
                            ))}
                        </ul>
                    </div>
                </div>

                {/* Bottom */}
                <div className="mt-16 pt-8 border-t border-stone-900 flex flex-col md:flex-row items-center justify-between gap-4">
                    <p className="text-sm text-stone-600">
                        © {new Date().getFullYear()} FleetFlow. Portfolio Project.
                    </p>
                    <div className="flex items-center gap-6 text-sm text-stone-600">
                        <Link href="#" className="hover:text-stone-400 transition-colors">Privacy</Link>
                        <Link href="#" className="hover:text-stone-400 transition-colors">Terms</Link>
                    </div>
                </div>
            </div>
        </footer>
    );
}

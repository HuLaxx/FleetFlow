import type { Metadata } from 'next';
import { Inter, Merienda } from 'next/font/google';
import './globals.css';
import { TRPCProvider } from '@/lib/trpc';

const inter = Inter({ variable: '--font-inter', subsets: ['latin'], display: 'swap' });
const script = Merienda({
  subsets: ['latin'],
  weight: ['400', '600', '900'],
  variable: '--font-script',
  display: 'swap',
});

export const metadata: Metadata = {
  title: 'FleetFlow | Dispatch planning and fleet operations',
  description: 'Explore a capacity-aware dispatch scenario, route proposals and delivery workflows. Demo values are illustrative; live services require a configured backend.',
  keywords: ['delivery dispatch', 'fleet operations', 'route planning', 'logistics', 'last-mile delivery'],
  authors: [{ name: 'HuLaX' }],
  icons: {
    icon: '/favicon.svg',
    shortcut: '/favicon.svg',
    apple: '/favicon.svg',
  },
  openGraph: {
    title: 'FleetFlow | A better way to move everything',
    description: 'Dispatch planning, route allocation and transparent delivery operations.',
    type: 'website',
  },
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en" className={`dark ${script.variable}`} suppressHydrationWarning>
      <body className={`${inter.variable} font-sans antialiased bg-[#0c1418] text-zinc-100`} suppressHydrationWarning>
        <TRPCProvider>{children}</TRPCProvider>
      </body>
    </html>
  );
}

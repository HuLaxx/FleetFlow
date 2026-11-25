import type { Metadata } from 'next';
import './globals.css';
import { TRPCProvider } from '@/lib/trpc';
import { LoadingScreen } from '@/components/effects/loading-screen';
import { ProjectGuide } from '@/components/project-guide/project-guide';

export const metadata: Metadata = {
  title: 'FleetFlow | Dispatch planning and fleet operations',
  description: 'Capacity-aware dispatch planning and fleet data engineering: OR-Tools route proposals, Kafka GPS streaming and a PySpark and dbt lakehouse. Demo values are illustrative; benchmarks are synthetic CI runs.',
  keywords: ['delivery dispatch', 'fleet operations', 'route planning', 'data engineering', 'last-mile delivery'],
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
    <html lang="en" className="dark" suppressHydrationWarning>
      <body className="font-sans antialiased bg-[#0c1418] text-zinc-100" suppressHydrationWarning>
        <LoadingScreen />
        <TRPCProvider>{children}</TRPCProvider>
        <ProjectGuide />
      </body>
    </html>
  );
}

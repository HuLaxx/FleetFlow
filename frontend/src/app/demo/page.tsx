'use client';

import dynamic from 'next/dynamic';
import { SiteHeader } from '@/components/site/site-header';
import { SiteFooter } from '@/components/site/site-footer';
import { Sidebar } from '@/components/dashboard/sidebar';
import { Header } from '@/components/dashboard/header';
import { StatsCards } from '@/components/dashboard/stats-cards';
import { DriversList } from '@/components/dashboard/drivers-list';
import { OrdersPanel } from '@/components/dashboard/orders-panel';
import { DeploymentNotice } from '@/components/site/deployment-notice';

// Dynamic import for map (no SSR - uses WebGL)
const FleetMap = dynamic(() => import('@/components/map/fleet-map'), {
    ssr: false,
    loading: () => (
        <div className="w-full h-full bg-stone-900 animate-pulse flex items-center justify-center">
            <div className="text-stone-500">Loading map...</div>
        </div>
    ),
});

export default function DemoPage() {
    return (
        <div className="min-h-screen bg-stone-950 flex flex-col">
            {/* Site Header */}
            <SiteHeader />

            {/* Demo Content */}
            <main className="flex-1 pt-16 flex flex-col">
                {/* Dashboard Container - Full viewport height minus header */}
                <div className="flex-1 flex min-h-[calc(100vh-64px)]">
                    {/* Sidebar */}
                    <Sidebar />

                    {/* Main Content */}
                    <div className="flex-1 flex flex-col overflow-hidden">
                        <div className="px-6 pt-6">
                            <DeploymentNotice variant="compact" />
                        </div>

                        {/* Dashboard Header */}
                        <Header />

                        {/* Dashboard Content */}
                        <div className="flex-1 overflow-hidden p-6">
                            <div className="h-full grid grid-cols-12 gap-6">
                                {/* Left Panel - Stats & Orders */}
                                <div className="col-span-3 flex flex-col gap-6 overflow-hidden">
                                    <StatsCards />
                                    <OrdersPanel />
                                </div>

                                {/* Center - Map */}
                                <div className="col-span-6 bg-stone-900 rounded-xl overflow-hidden border border-stone-800">
                                    <FleetMap />
                                </div>

                                {/* Right Panel - Drivers */}
                                <div className="col-span-3 overflow-hidden">
                                    <DriversList />
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </main>
        </div>
    );
}

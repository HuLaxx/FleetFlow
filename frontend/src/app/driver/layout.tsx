import { Metadata, Viewport } from 'next';

export const metadata: Metadata = {
    title: 'FleetFlow Driver',
    description: 'Driver Companion App for FleetFlow',
    manifest: '/manifest.json',
    icons: {
        icon: '/favicon.ico',
        apple: '/icon-192x192.png',
    },
};

export const viewport: Viewport = {
    themeColor: '#0c0a09', // Stone-950
    width: 'device-width',
    initialScale: 1,
    maximumScale: 1,
    userScalable: false, // Prevent zooming like a native app
};

export default function DriverLayout({
    children,
}: {
    children: React.ReactNode;
}) {
    return (
        <div className="flex flex-col min-h-screen bg-stone-950 text-stone-50">
            {children}
        </div>
    );
}

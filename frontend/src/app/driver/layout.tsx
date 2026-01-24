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

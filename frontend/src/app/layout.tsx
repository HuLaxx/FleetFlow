import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import { TRPCProvider } from "@/lib/trpc";

const inter = Inter({
  variable: "--font-inter",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "FleetFlow | Real-Time Delivery Optimization",
  description: "Predictive & reactive delivery route optimization with real-time fleet management. Reduce delivery time by 23%, cut fuel costs by 18%.",
  keywords: ["delivery optimization", "fleet management", "route optimization", "logistics", "last-mile delivery"],
  authors: [{ name: "FleetFlow Team" }],
  icons: {
    icon: "/favicon.svg",
    shortcut: "/favicon.svg",
    apple: "/favicon.svg",
  },
  openGraph: {
    title: "FleetFlow | Real-Time Delivery Optimization",
    description: "Predictive & reactive delivery route optimization platform",
    type: "website",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="dark" suppressHydrationWarning>
      <body className={`${inter.variable} font-sans antialiased bg-zinc-950 text-zinc-100`} suppressHydrationWarning>
        <TRPCProvider>
          {children}
        </TRPCProvider>
      </body>
    </html>
  );
}

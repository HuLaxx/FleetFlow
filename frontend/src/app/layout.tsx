import type { Metadata } from "next";
import { Inter, Merienda } from "next/font/google";
import "./globals.css";
import { TRPCProvider } from "@/lib/trpc";
import { LoadingScreen } from "@/components/effects/loading-screen";
import { StardustBackground } from "@/components/effects/stardust-background";

const inter = Inter({
  variable: "--font-inter",
  subsets: ["latin"],
});

const script = Merienda({
  subsets: ["latin"],
  weight: ["400", "600", "900"],
  variable: "--font-script",
  display: "swap",
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
    <html lang="en" className={`dark ${script.variable}`} suppressHydrationWarning>
      <body className={`${inter.variable} font-sans antialiased bg-zinc-950 text-zinc-100`} suppressHydrationWarning>
        {/* Global animated gradient background */}
        <div className="fixed inset-0 pointer-events-none overflow-hidden z-0">
          <div className="absolute top-0 left-1/4 w-[700px] h-[700px] bg-gradient-to-r from-emerald-500/12 via-teal-500/12 to-emerald-400/10 rounded-full blur-[150px] animate-pulse" style={{ animationDuration: "7s" }} />
          <div className="absolute bottom-0 right-1/4 w-[600px] h-[600px] bg-gradient-to-r from-teal-500/10 via-emerald-500/10 to-green-500/10 rounded-full blur-[150px] animate-pulse" style={{ animationDuration: "9s" }} />
          <div className="absolute top-1/3 right-1/3 w-[520px] h-[520px] bg-gradient-to-br from-emerald-400/10 via-transparent to-teal-500/12 rounded-full blur-[120px] animate-pulse" style={{ animationDuration: "11s" }} />
        </div>
        <StardustBackground />
        <LoadingScreen />
        <div className="noise" />
        <TRPCProvider>
          {children}
        </TRPCProvider>
      </body>
    </html>
  );
}

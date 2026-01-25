"use client";

import { useEffect, useState } from "react";

export function LoadingScreen() {
  const [isVisible, setIsVisible] = useState(false);

  useEffect(() => {
    try {
      const alreadyShown = sessionStorage.getItem("fleetflow_loaded");
      if (alreadyShown) return;
      sessionStorage.setItem("fleetflow_loaded", "1");
    } catch {
      // If sessionStorage is blocked, still show once per mount.
    }

    setIsVisible(true);
    const hideTimer = setTimeout(() => setIsVisible(false), 2200);
    return () => clearTimeout(hideTimer);
  }, []);

  if (!isVisible) return null;

  return (
    <div className="loading-screen fixed inset-0 z-[100] flex flex-col items-center justify-center bg-stone-950">
      {/* Background glow */}
      <div className="absolute inset-0 overflow-hidden">
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] bg-gradient-to-r from-emerald-400/10 via-emerald-500/10 to-emerald-200/10 rounded-full blur-[150px] animate-pulse" />
        <div
          className="absolute top-1/4 left-1/4 w-[300px] h-[300px] bg-gradient-to-r from-emerald-300/10 to-emerald-500/10 rounded-full blur-[100px] animate-pulse"
          style={{ animationDelay: "0.3s" }}
        />
        <div
          className="absolute bottom-1/4 right-1/4 w-[250px] h-[250px] bg-gradient-to-r from-emerald-200/10 to-emerald-400/10 rounded-full blur-[100px] animate-pulse"
          style={{ animationDelay: "0.6s" }}
        />
      </div>

      <div className="relative z-10 flex flex-col items-center">
        {/* Logo */}
        <div className="relative mb-8">
          <div className="w-20 h-20 rounded-2xl overflow-hidden shadow-2xl shadow-emerald-500/20 animate-pulse bg-stone-900/70 border border-emerald-500/30 flex items-center justify-center">
            <img src="/favicon.svg" alt="FleetFlow" className="w-10 h-10" />
          </div>
          <div className="absolute -inset-2 rounded-3xl bg-gradient-to-r from-emerald-200 via-emerald-400 to-emerald-300 opacity-15 blur-xl animate-pulse" />
        </div>

        <h1 className="text-3xl md:text-4xl font-bold mb-4 bg-gradient-to-r from-emerald-100 via-emerald-300 to-emerald-400 bg-clip-text text-transparent">
          FleetFlow
        </h1>
        <p className="text-stone-500 text-sm mb-8 tracking-wide">
          Real-Time Delivery Optimization
        </p>

        <div className="relative">
          <div className="w-48 h-1 bg-stone-800 rounded-full overflow-hidden">
            <div className="progress-bar h-full bg-gradient-to-r from-emerald-200 via-emerald-400 to-emerald-600 rounded-full" />
          </div>
        </div>

        <div className="flex gap-2 mt-6">
          {[0, 1, 2].map((i) => (
            <div
              key={i}
              className="w-2 h-2 rounded-full bg-emerald-300/60 animate-pulse"
              style={{ animationDelay: `${i * 0.2}s` }}
            />
          ))}
        </div>
      </div>

      <div className="absolute bottom-0 left-0 right-0 h-px bg-gradient-to-r from-transparent via-emerald-300/50 to-transparent" />

      <style jsx>{`
        .loading-screen {
          animation: screenExit 2.1s cubic-bezier(0.76, 0, 0.24, 1) forwards;
        }

        .progress-bar {
          width: 0%;
          animation: loadProgress 1.4s ease-out forwards;
        }

        @keyframes screenExit {
          0% {
            transform: translateY(0);
            opacity: 1;
            visibility: visible;
          }
          66% {
            transform: translateY(0);
            opacity: 1;
            visibility: visible;
          }
          100% {
            transform: translateY(-100%);
            opacity: 0;
            visibility: hidden;
          }
        }

        @keyframes loadProgress {
          0% {
            width: 0%;
          }
          50% {
            width: 70%;
          }
          100% {
            width: 100%;
          }
        }
      `}</style>
    </div>
  );
}

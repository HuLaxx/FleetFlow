'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import { usePathname, useRouter } from 'next/navigation';
import { ArrowUpRight, Truck } from 'lucide-react';

// This is a branded opening animation, NOT a fake backend progress indicator.
// It remains skippable; an explicit showcase URL keeps it visible indefinitely.
const INTRO_DURATION_MS = 4000;

/**
 * On full page loads show FleetFlow's introduction long enough to be seen.
 * Pause the countdown in background tabs (a common reason users miss it when
 * opening a preview from another app). /intro is a persistent preview.
 */
export function LoadingScreen() {
  const pathname = usePathname();
  const router = useRouter();
  const showcase = pathname === '/intro';
  const [visible, setVisible] = useState(true);
  const timerRef = useRef<number | null>(null);
  const skipAfterShowcaseRef = useRef(false);

  const clearCountdown = useCallback(() => {
    if (timerRef.current !== null) {
      window.clearTimeout(timerRef.current);
      timerRef.current = null;
    }
  }, []);

  const dismiss = useCallback(() => {
    clearCountdown();
    setVisible(false);
  }, [clearCountdown]);

  const continueToSite = useCallback(() => {
    dismiss();
    skipAfterShowcaseRef.current = true;
    router.replace('/');
  }, [dismiss, router]);

  // The root layout persists between Next.js client-side navigations.
  // Reopen only for the explicit preview route, not on every navigation.
  useEffect(() => {
    if (showcase) {
      clearCountdown();
      setVisible(true);
    } else if (skipAfterShowcaseRef.current) {
      skipAfterShowcaseRef.current = false;
      setVisible(false);
    }
  }, [showcase, clearCountdown]);

  useEffect(() => {
    if (!visible || showcase) {
      clearCountdown();
      return;
    }

    // Do not let the intro expire while the tab is in the background.
    const scheduleWhileVisible = () => {
      clearCountdown();
      if (document.visibilityState === 'visible') {
        timerRef.current = window.setTimeout(dismiss, INTRO_DURATION_MS);
      }
    };
    scheduleWhileVisible();
    document.addEventListener('visibilitychange', scheduleWhileVisible);
    window.addEventListener('focus', scheduleWhileVisible);
    return () => {
      clearCountdown();
      document.removeEventListener('visibilitychange', scheduleWhileVisible);
      window.removeEventListener('focus', scheduleWhileVisible);
    };
  }, [visible, showcase, dismiss, clearCountdown]);

  useEffect(() => {
    const replay = () => setVisible(true);
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape' && !showcase) dismiss();
    };
    window.addEventListener('fleetflow:replay-intro', replay);
    document.addEventListener('keydown', onKeyDown);
    return () => {
      window.removeEventListener('fleetflow:replay-intro', replay);
      document.removeEventListener('keydown', onKeyDown);
    };
  }, [dismiss, showcase]);

  if (!visible) return null;

  return (
    <div
      className="ff-loader fixed inset-0 z-[100] flex min-h-svh flex-col overflow-y-auto bg-[#071511] text-[#eefbf3]"
      role="dialog"
      aria-modal="true"
      aria-label="FleetFlow opening screen"
      data-testid="fleetflow-intro"
    >
      {/* Entire screen is the loader, with no top navigation or faux header. */}
      <div className="pointer-events-none absolute inset-0 overflow-hidden" aria-hidden="true">
        <div className="ff-loader-glow absolute left-1/2 top-1/2 h-[min(110vw,760px)] w-[min(110vw,760px)] -translate-x-1/2 -translate-y-1/2 rounded-full bg-[#285b46]/20 blur-[100px]" />
        <div
          className="absolute inset-0 opacity-[.13]"
          style={{
            backgroundImage:
              'linear-gradient(rgba(158,240,192,.10) 1px, transparent 1px), linear-gradient(90deg, rgba(158,240,192,.10) 1px, transparent 1px)',
            backgroundSize: '52px 52px',
            maskImage: 'radial-gradient(ellipse at center, black 7%, transparent 72%)',
            WebkitMaskImage: 'radial-gradient(ellipse at center, black 7%, transparent 72%)',
          }}
        />
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_center,transparent_20%,#071511_85%)]" />
      </div>

      <div className="relative flex min-h-svh w-full flex-1 flex-col items-center justify-center px-5 py-12 text-center">
        <div className="mb-8 flex items-center gap-2.5 text-[10px] font-semibold uppercase tracking-[.35em] text-[#85bc9e] sm:text-xs">
          <span className="ff-loader-live h-2 w-2 rounded-full bg-[#abf3cb]" aria-hidden="true" />
          FleetFlow / Dispatch systems
        </div>

        {/* Route animation and rotating indicator are the visual focal point. */}
        <div
          data-testid="fleetflow-loading-animation"
          className="relative mb-8 h-44 w-44 shrink-0 sm:mb-10 sm:h-52 sm:w-52"
          aria-hidden="true"
        >
          <div className="absolute inset-[10px] rounded-full border border-[#9ce8b9]/15" />
          <div className="absolute inset-7 rounded-full border border-dashed border-[#a7e7bf]/15" />
          <div className="ff-loader-spinner absolute inset-0 rounded-full border-[2px] border-transparent border-t-[#b4f5d0] border-r-[#b4f5d0]/20" />
          <div className="ff-loader-halo absolute inset-3 rounded-full border border-[#b4f5d0]/10" />
          <svg viewBox="0 0 208 208" className="absolute inset-0 h-full w-full">
            <defs>
              <linearGradient id="ff-loading-route" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop stopColor="#d7ffe4" />
                <stop offset=".56" stopColor="#87dbad" />
                <stop offset="1" stopColor="#3f997d" />
              </linearGradient>
            </defs>
            <circle cx="104" cy="104" r="85" stroke="#92c9ad" strokeOpacity=".08" strokeWidth="20" fill="none"/>
            <path d="M39 146 C44 104 65 107 75 112 C97 125 105 63 132 64 C158 65 157 103 171 78" stroke="#a4f1c5" strokeOpacity=".16" strokeWidth="11" fill="none" strokeLinecap="round"/>
            <path className="ff-loader-path" d="M39 146 C44 104 65 107 75 112 C97 125 105 63 132 64 C158 65 157 103 171 78" stroke="url(#ff-loading-route)" strokeWidth="3.5" strokeLinecap="round" strokeLinejoin="round" fill="none" pathLength="100" />
            <circle cx="39" cy="146" r="6" fill="#a0e9be" stroke="#071511" strokeWidth="3" />
            <circle className="ff-loader-destination" cx="171" cy="78" r="6" fill="#d4ffe1" stroke="#071511" strokeWidth="3" />
            <circle cx="104" cy="104" r="25" fill="#081b15" stroke="#477e63" strokeOpacity=".75" />
          </svg>
          <span className="absolute inset-0 flex items-center justify-center">
            <span className="flex h-12 w-12 items-center justify-center rounded-xl border border-[#9feaaf]/30 bg-[#10271d] text-[#b4f2c8] shadow-[0_0_40px_rgba(113,234,164,.18)]">
              <Truck size={24} strokeWidth={1.75} />
            </span>
          </span>
        </div>

        <h1 className="text-[clamp(3.1rem,10vw,5.5rem)] font-semibold leading-none tracking-[-.075em] text-[#f0fcf3]">
          Fleet<span className="text-[#a4edc1]">Flow</span>
        </h1>
        <p className="mt-3 text-[10px] font-semibold uppercase tracking-[.4em] text-[#76a58a] sm:text-xs">
          Every stop matters
        </p>

        <div className="mt-9 flex items-center justify-center gap-2 text-sm font-medium text-[#c3e0d0] sm:mt-11">
          <span>Loading your workspace</span>
          <span className="flex items-end gap-1" aria-hidden="true">
            <span className="ff-loader-dot h-1.5 w-1.5 rounded-full bg-[#a8edc3]" />
            <span className="ff-loader-dot h-1.5 w-1.5 rounded-full bg-[#a8edc3]" />
            <span className="ff-loader-dot h-1.5 w-1.5 rounded-full bg-[#a8edc3]" />
          </span>
        </div>

        {/* Indeterminate: this is a brand intro, never a fabricated percentage. */}
        <div
          data-testid="fleetflow-progress-track"
          className="relative mt-5 h-1 w-[min(72vw,270px)] overflow-hidden rounded-full bg-[#315747]/50"
          role="progressbar"
          aria-label="FleetFlow loading animation"
          aria-valuetext="Preparing workspace"
        >
          <div className="ff-loader-progress absolute left-0 top-0 h-full w-[38%] rounded-full bg-gradient-to-r from-[#4f9971] via-[#b4f5cc] to-[#d4ffe3] shadow-[0_0_20px_rgba(166,248,194,.65)]" />
        </div>

        <div className="mt-9 flex items-center gap-3 text-[10px] uppercase tracking-[.23em] text-[#608c73]">
          <span>Plan</span><span className="h-px w-5 bg-[#416c50]" />
          <span>Dispatch</span><span className="h-px w-5 bg-[#416c50]" />
          <span>Deliver</span>
        </div>

        <div className="mt-10 min-h-10 sm:mt-12">
          <button
            type="button"
            onClick={showcase ? continueToSite : dismiss}
            className="inline-flex items-center justify-center gap-2 rounded-full border border-[#416b54] bg-[#133024]/70 px-6 py-3 text-xs font-semibold text-[#c4ebd4] transition-colors hover:border-[#a7efc5] hover:bg-[#1f4833] focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-[#b4f5cc]"
          >
            {showcase ? 'Enter FleetFlow' : 'Skip intro'}
            <ArrowUpRight size={15} />
          </button>
        </div>
        {showcase && (
          <p className="mt-4 text-[11px] text-[#6d957e]">
            Preview mode — the loading animation stays on screen.
          </p>
        )}
      </div>

      <style jsx global>{`
        .ff-loader-path {
          stroke-dasharray: 100;
          stroke-dashoffset: 100;
          animation: ff-route-draw 2.6s ease-in-out infinite;
        }
        .ff-loader-spinner {
          animation: ff-spin 2.7s linear infinite;
        }
        .ff-loader-destination {
          transform-origin: 171px 78px;
          animation: ff-pulse 1.7s ease-in-out infinite;
        }
        .ff-loader-halo {
          animation: ff-halo 2.8s ease-in-out infinite;
        }
        .ff-loader-progress {
          animation: ff-progress 1.85s ease-in-out infinite;
        }
        .ff-loader-dot {
          animation: ff-dot 1.1s ease-in-out infinite;
        }
        .ff-loader-dot:nth-child(2) { animation-delay: 0.16s; }
        .ff-loader-dot:nth-child(3) { animation-delay: 0.32s; }
        .ff-loader-live {
          animation: ff-live 2s ease-in-out infinite;
        }
        @keyframes ff-route-draw {
          0% { stroke-dashoffset: 100; opacity: .55; }
          62%, 84% { stroke-dashoffset: 0; opacity: 1; }
          100% { stroke-dashoffset: -100; opacity: .35; }
        }
        @keyframes ff-spin { to { transform: rotate(360deg); } }
        @keyframes ff-progress {
          0% { transform: translateX(-115%); }
          100% { transform: translateX(370%); }
        }
        @keyframes ff-dot {
          0%, 70%, 100% { opacity: .28; transform: translateY(0); }
          36% { opacity: 1; transform: translateY(-4px); }
        }
        @keyframes ff-pulse {
          0%, 100% { transform: scale(1); opacity: .5; }
          50% { transform: scale(1.6); opacity: 1; }
        }
        @keyframes ff-halo {
          0%, 100% { opacity: .2; transform: scale(.97); }
          50% { opacity: .8; transform: scale(1.05); }
        }
        @keyframes ff-live { 0%, 100% { opacity: .35; } 50% { opacity: 1; } }
        @media (prefers-reduced-motion: reduce) {
          .ff-loader .ff-loader-path,
          .ff-loader .ff-loader-spinner,
          .ff-loader .ff-loader-progress,
          .ff-loader .ff-loader-dot,
          .ff-loader .ff-loader-halo,
          .ff-loader .ff-loader-destination,
          .ff-loader .ff-loader-live { animation: none !important; }
          .ff-loader .ff-loader-path { stroke-dashoffset: 0; }
          .ff-loader .ff-loader-progress { transform: translateX(90%); }
          .ff-loader .ff-loader-dot { opacity: 1; }
        }
      `}</style>
    </div>
  );
}

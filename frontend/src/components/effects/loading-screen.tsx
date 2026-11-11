'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import { usePathname, useRouter } from 'next/navigation';
import { ArrowUpRight, Truck } from 'lucide-react';

// Brand animation only. Never represent network/model progress with fabricated values.
// The normal first paint is a brief, nonblocking 1.3-second transition.
const INTRO_DURATION_MS = 1300;

/**
 * Normal page loads auto-dismiss in 1.3 seconds, with a CSS first-paint
 * fallback when hydration is delayed. /intro remains a persistent preview
 * for reviewing the artwork, not the normal site-loading experience.
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
      className={`ff-loader ${showcase ? "ff-loader-preview" : "ff-loader-auto"} fixed inset-0 z-[100] flex min-h-svh flex-col overflow-y-auto bg-[#0c1418] text-[#eefbf3]`}
      role="dialog"
      aria-modal="true"
      aria-label="FleetFlow opening screen"
      data-testid="fleetflow-intro"
    >
      {/* Same design language as V2 homepage's route illustration:
          charcoal canvas, map grid, street strokes, and three dispatch paths.
          This replaces the older brand's blurred emerald-glow background. */}
      <div
        data-testid="fleetflow-v2-backdrop"
        className="pointer-events-none absolute inset-0 overflow-hidden bg-[#0c1418]"
        aria-hidden="true"
      >
        <svg
          viewBox="0 0 1200 900"
          preserveAspectRatio="xMidYMid slice"
          className="absolute inset-0 h-full w-full"
        >
          <defs>
            <pattern id="ff-v2-loading-grid" width="48" height="48" patternUnits="userSpaceOnUse">
              <path d="M 48 0 L 0 0 0 48" fill="none" stroke="#50605d" strokeWidth="1" opacity=".39" />
            </pattern>
            <radialGradient id="ff-v2-loading-vignette" cx="50%" cy="50%" r="65%">
              <stop offset="0" stopColor="#0c1418" stopOpacity=".76" />
              <stop offset=".42" stopColor="#0c1418" stopOpacity=".48" />
              <stop offset="1" stopColor="#0c1418" stopOpacity=".08" />
            </radialGradient>
          </defs>
          <rect width="1200" height="900" fill="#0c1418" />
          <rect width="1200" height="900" fill="url(#ff-v2-loading-grid)" />
          <g fill="#143a43" opacity=".58">
            <path d="M0 0 H95 Q26 250 106 510 T90 900 H0Z" />
            <path d="M1138 0 H1200 V900 H1153 Q1080 450 1138 0Z" />
          </g>
          <g fill="none" stroke="#3c5e59" opacity=".54">
            <path d="M155 0 L110 900 M290 0 L275 900 M430 0 L420 900 M770 0 L755 900 M910 0 L900 900 M1065 0 L1050 900" strokeWidth="5" />
            <path d="M90 155 L1120 128 M90 315 L1120 300 M90 585 L1120 565 M90 745 L1120 730" strokeWidth="4" />
          </g>
          <g className="ff-v2-loading-routes" fill="none" strokeLinecap="round" strokeLinejoin="round" strokeWidth="3.5">
            <path d="M600 455 L420 265 L248 338 L165 628" stroke="#95e6bc" pathLength="100" />
            <path d="M600 455 L775 265 L974 326 L1042 610" stroke="#ffc28b" pathLength="100" />
            <path d="M600 455 L790 665 L1030 740" stroke="#93baff" pathLength="100" />
          </g>
          <g fill="#112024" strokeWidth="3">
            <circle cx="248" cy="338" r="8" stroke="#95e6bc" />
            <circle cx="165" cy="628" r="8" stroke="#95e6bc" />
            <circle cx="974" cy="326" r="8" stroke="#ffc28b" />
            <circle cx="1042" cy="610" r="8" stroke="#ffc28b" />
            <circle cx="790" cy="665" r="8" stroke="#93baff" />
            <circle cx="1030" cy="740" r="8" stroke="#93baff" />
          </g>
          <circle cx="600" cy="455" r="16" fill="#95e6bc" opacity=".18" />
          <rect x="595" y="450" width="10" height="10" rx="2" fill="#b3f0d2" />
          <rect width="1200" height="900" fill="url(#ff-v2-loading-vignette)" />
          <g fill="#70948d" fontFamily="monospace" fontSize="12" letterSpacing="2" opacity=".6">
            <text x="165" y="122">DISPATCH / SECTOR 01</text>
            <text x="850" y="830">FLEETFLOW / ROUTE NETWORK</text>
          </g>
        </svg>
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_center,rgba(12,20,24,.40)_5%,transparent_75%)]" />
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
          className="mt-5"
          aria-hidden="true"
          style={{
            display: 'block',
            position: 'relative',
            width: '270px',
            maxWidth: '72vw',
            height: '12px',
            minHeight: '12px',
            maxHeight: '12px',
            flexShrink: 0,
            boxSizing: 'content-box',
            backgroundColor: '#31534a',
            border: '1px solid rgba(162, 238, 186, .35)',
            borderRadius: '9999px',
            overflow: 'hidden',
            boxShadow: '0 0 22px rgba(138, 232, 166, .08)',
          }}
        >
          <div
            className="ff-loader-progress"
            style={{
              display: 'block',
              position: 'absolute',
              left: 0,
              top: 0,
              height: '100%',
              width: '42%',
              borderRadius: '9999px',
              background: 'linear-gradient(90deg, #53a477, #b4f5cc, #e2ffe9)',
              boxShadow: '0 0 14px rgba(178, 249, 200, .7)',
            }}
            aria-hidden="true"
          />
        </div>

        <div className="mt-9 flex items-center gap-3 text-[10px] uppercase tracking-[.23em] text-[#608c73]">
          <span>Plan</span><span className="h-px w-5 bg-[#416c50]" />
          <span>Dispatch</span><span className="h-px w-5 bg-[#416c50]" />
          <span>Deliver</span>
        </div>

        {/* Only the manual showcase needs a button. Real visits auto-close. */}
        {showcase && (
          <div className="mt-10 flex flex-col items-center gap-4 sm:mt-12">
            <button
              type="button"
              onClick={continueToSite}
              className="inline-flex items-center justify-center gap-2 rounded-full border border-[#416b54] bg-[#133024]/70 px-6 py-3 text-xs font-semibold text-[#c4ebd4] transition-colors hover:border-[#a7efc5] hover:bg-[#1f4833] focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-[#b4f5cc]"
            >
              Enter FleetFlow
              <ArrowUpRight size={15} />
            </button>
            <p className="text-[11px] text-[#88b49d]">
              Design preview — stays open until you enter the site.
            </p>
          </div>
        )}
      </div>

      <style jsx global>{`
        /* CSS-first paint dismiss keeps the real site responsive even if JS is slow. */
        .ff-loader-auto {
          animation: ff-loader-out 1.3s ease-in-out both;
        }
        @keyframes ff-loader-out {
          0%, 76% { opacity: 1; visibility: visible; }
          99% { opacity: 0.01; visibility: visible; }
          100% { opacity: 0; visibility: hidden; pointer-events: none; }
        }
        .ff-v2-loading-routes path {
          stroke-dasharray: 12 7;
          animation: ff-v2-route-flow 5s linear infinite;
        }
        @keyframes ff-v2-route-flow {
          to { stroke-dashoffset: -76; }
        }
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
          .ff-loader-auto { animation-timing-function: steps(1, end); }
          .ff-loader .ff-v2-loading-routes path,
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

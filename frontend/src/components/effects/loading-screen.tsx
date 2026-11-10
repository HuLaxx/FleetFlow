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
      className="fixed inset-0 z-[100] flex min-h-svh flex-col overflow-y-auto bg-[#0a1417] text-[#edf5ef]"
      role="dialog"
      aria-modal="true"
      aria-label="FleetFlow opening screen"
      data-testid="fleetflow-intro"
    >
      <div
        className="pointer-events-none absolute inset-0 opacity-50"
        style={{
          backgroundImage:
            'linear-gradient(rgba(145,206,169,.07) 1px, transparent 1px), linear-gradient(90deg, rgba(145,206,169,.07) 1px, transparent 1px)',
          backgroundSize: '76px 76px',
        }}
        aria-hidden="true"
      />
      <div className="relative mx-auto flex min-h-svh w-full max-w-[1440px] flex-1 flex-col px-6 py-8 md:px-12 md:py-12">
        <div className="flex items-center justify-between gap-4 border-b border-white/10 pb-5">
          <div className="flex items-center gap-3">
            <span className="flex h-9 w-9 items-center justify-center border border-[#82b99b] bg-[#173028] text-[#a9ebc2]">
              <Truck size={18} strokeWidth={1.8}/>
            </span>
            <span className="text-[20px] font-semibold tracking-[-.055em]">FleetFlow</span>
            <span className="ml-2 hidden border-l border-white/20 pl-4 text-[10px] font-medium uppercase tracking-[.22em] text-[#91b7a4] sm:inline">
              Dispatch systems
            </span>
          </div>
          <button
            type="button"
            onClick={showcase ? continueToSite : dismiss}
            className="group inline-flex items-center gap-2 border border-white/20 px-3 py-2 text-xs text-[#cadbd2] transition hover:border-[#b9e6cb] hover:text-white focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#b9e6cb]"
          >
            {showcase ? 'Continue to FleetFlow' : 'Skip intro'} <ArrowUpRight size={13} className="transition group-hover:translate-x-0.5 group-hover:-translate-y-0.5" />
          </button>
        </div>

        <div className="grid flex-1 grid-cols-1 items-center gap-10 py-8 lg:grid-cols-[1fr_1.08fr]">
          <div className="relative z-10">
            <p className="mb-7 flex items-center gap-3 text-[10px] font-semibold uppercase tracking-[.3em] text-[#9fd7b8]">
              <span className="h-px w-9 bg-[#9fd7b8]"/> Shift briefing / 001
            </p>
            <h2 className="max-w-xl text-[clamp(3rem,5.4vw,6.1rem)] font-semibold leading-[.97] tracking-[-.07em]">
              Every journey<br/>starts with<br/>
              <span className="font-normal italic text-[#a5e7bd]">a plan.</span>
            </h2>
            <p className="mt-7 max-w-md text-sm leading-[1.8] text-[#94aba7]">
              Making complex operations feel effortless.
            </p>
          </div>

          <div className="relative mx-auto w-full max-w-[660px] overflow-hidden border border-[#31524a] bg-[#112329]">
            <div className="absolute left-5 top-5 z-10 text-[10px] font-semibold uppercase tracking-[.2em] text-[#b5d9c6]">
              Route systems / initializing view
            </div>
            <svg viewBox="0 0 600 410" role="img" aria-label="Illustrated delivery routes linking the depot to multiple stops" className="h-auto w-full">
              <defs>
                <pattern id="loader-map" width="42" height="42" patternUnits="userSpaceOnUse">
                  <path d="M 42 0 L 0 0 0 42" fill="none" stroke="#3b5e55" strokeWidth="1" opacity=".45"/>
                </pattern>
              </defs>
              <rect width="600" height="410" fill="#112329"/>
              <rect width="600" height="410" fill="url(#loader-map)"/>
              <path d="M 0 0 L 65 0 Q 28 180 77 305 L 51 410 L 0 410Z" fill="#163a41"/>
              <g stroke="#3f6358" strokeWidth="5" fill="none" opacity=".65">
                <path d="M 130 0 L 100 410 M 228 0 L 205 410 M 348 0 L 338 410 M 465 0 L 444 410"/>
                <path d="M 70 112 L 550 97 M 67 206 L 540 196 M 73 312 L 530 300"/>
              </g>
              <g fill="none" strokeWidth="4" strokeLinecap="round" strokeLinejoin="round" className="fleetflow-loader-routes">
                <path d="M 300 212 L 182 108 L 153 297 L 300 212" stroke="#a3eac2" pathLength="100"/>
                <path d="M 300 212 L 453 106 L 490 277 L 300 212" stroke="#f4bd89" pathLength="100"/>
                <path d="M 300 212 L 375 340 L 300 212" stroke="#9fbff4" pathLength="100"/>
              </g>
              <g fill="#12272a" strokeWidth="4">
                <circle cx="182" cy="108" r="9" stroke="#a3eac2"/><circle cx="153" cy="297" r="9" stroke="#a3eac2"/>
                <circle cx="453" cy="106" r="9" stroke="#f4bd89"/><circle cx="490" cy="277" r="9" stroke="#f4bd89"/>
                <circle cx="375" cy="340" r="9" stroke="#9fbff4"/>
              </g>
              <circle cx="300" cy="212" r="23" fill="#b9eed1" opacity=".12"/>
              <rect x="286" y="198" width="28" height="28" rx="3" fill="#b9eed1" stroke="#132c2b" strokeWidth="4"/>
              <g fontFamily="monospace" fontSize="9" fill="#75978c" letterSpacing="2">
                <text x="110" y="65">DEPOT → DELIVERY NETWORK</text>
                <text x="410" y="375">NYC / DEMO</text>
              </g>
            </svg>
            <div className="flex items-center justify-between gap-2 border-t border-white/10 px-5 py-3 font-mono text-[10px] uppercase tracking-[.16em] text-[#87a89b]">
              <span>Plan · Dispatch · Deliver</span>
              <span className="text-[#b5e5ca]">FleetFlow / V2</span>
            </div>
          </div>
        </div>

        <div className="border-t border-white/10 pt-5">
          <div className="mb-3 flex items-center justify-between gap-3 text-[11px] text-[#a6c5b5]">
            <span className="uppercase tracking-[.18em]">{showcase ? 'Loading screen / Full preview' : 'Opening operations desk'}</span>
            <span className="font-mono text-[#8ca69c]">FF / 001</span>
          </div>
          <div className="h-[2px] overflow-hidden bg-white/10" aria-hidden="true">
            <div className="fleetflow-loader-bar h-full origin-left bg-[#b3ebcb]"/>
          </div>
        </div>
      </div>

      <style jsx>{`
        .fleetflow-loader-routes path {
          stroke-dasharray: 100;
          stroke-dashoffset: 100;
          animation: draw-routes 1.15s ease-out forwards;
        }
        .fleetflow-loader-routes path:nth-child(2) { animation-delay: .14s; }
        .fleetflow-loader-routes path:nth-child(3) { animation-delay: .28s; }
        .fleetflow-loader-bar { animation: fill-bar 1.35s ease-out forwards; }
        @keyframes draw-routes { to { stroke-dashoffset: 0; } }
        @keyframes fill-bar { from { transform: scaleX(0); } to { transform: scaleX(1); } }
        @media (prefers-reduced-motion: reduce) {
          .fleetflow-loader-routes path, .fleetflow-loader-bar { animation: none; }
          .fleetflow-loader-routes path { stroke-dashoffset: 0; }
        }
      `}</style>
    </div>
  );
}

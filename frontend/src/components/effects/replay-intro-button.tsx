'use client';

import { Play } from 'lucide-react';

/** Manually previews the branded full-screen introduction without page reload. */
export function ReplayIntroButton({ className = '' }: { className?: string }) {
  return (
    <button
      type="button"
      onClick={() => window.dispatchEvent(new Event('fleetflow:replay-intro'))}
      className={`inline-flex items-center gap-2 text-xs font-medium text-[#a8cfb8] underline underline-offset-4 transition hover:text-white focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-[#9ce6bf] ${className}`}
    >
      <Play size={13} aria-hidden="true" />
      Replay loading intro
    </button>
  );
}

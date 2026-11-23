/**
 * Real App Router loading boundary for route streaming and navigation.
 * The session-once branded introduction is handled separately in layout.tsx.
 */
export default function Loading() {
  return (
    <main role="status" aria-live="polite" aria-label="Loading FleetFlow page"
      className="relative z-10 flex min-h-[70svh] flex-col items-center justify-center gap-6 bg-[#0c1418] px-6 text-center text-[#e9f3ed]">
      <div className="flex items-center gap-3 font-mono text-xs uppercase tracking-[.24em] text-[#a2cbb4]">
        <span className="h-2 w-2 animate-pulse rounded-full bg-[#a2e6c3]" aria-hidden="true" />
        FleetFlow / Preparing view
      </div>
      <div className="h-px w-44 overflow-hidden bg-white/10" aria-hidden="true">
        <div className="h-full w-1/2 origin-left animate-pulse bg-[#a2e6c3]" />
      </div>
      <p className="max-w-sm text-xs leading-relaxed text-[#7e9b92]">Loading your workspace…</p>
    </main>
  );
}

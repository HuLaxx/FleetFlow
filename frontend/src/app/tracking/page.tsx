"use client";

import dynamic from "next/dynamic";
import Link from "next/link";
import { Activity, AlertTriangle, Clock3, Truck } from "lucide-react";

import { SiteHeader } from "@/components/site/site-header";
import { SiteFooter } from "@/components/site/site-footer";
import { useLiveTracking, STALE_AFTER_MS } from "@/hooks/use-live-tracking";

const LocalLiveTrackingMap = dynamic(
  () => import("@/components/map/local-live-tracking-map"),
  { ssr: false, loading: () => <div className="h-full bg-stone-900" /> },
);

export default function TrackingPage() {
  const { vehicles, fresh, connection, now } = useLiveTracking();
  const connected = connection === "connected";
  return (
    <div className="flex min-h-screen flex-col bg-stone-950 text-stone-100">
      <SiteHeader />
      <main className="mx-auto w-full max-w-7xl flex-1 space-y-6 px-4 pb-16 pt-28 sm:px-6">
        <header className="flex flex-col justify-between gap-4 sm:flex-row sm:items-center">
          <div>
            <div className="mb-2 inline-flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-emerald-400">
              <Activity size={14} /> P1 · Local integration
            </div>
            <h1 className="text-3xl font-bold tracking-tight">GPS tracking console</h1>
            <p className="mt-2 max-w-2xl text-sm text-stone-400">
              Actual validated GPS events only. Positions originate from Kafka and persisted PostGIS,
              not the seeded map in the public <Link href="/demo" className="text-emerald-400 underline">demo</Link>.
            </p>
          </div>
          <div
            role="status"
            aria-live="polite"
            data-testid="tracking-connection"
            className="w-fit rounded-full border border-stone-700 bg-stone-900 px-4 py-2 text-sm"
          >
            <span className={connected ? "text-emerald-400" : "text-amber-300"}>
              {connection === "unconfigured" ? "Not configured" : connection}
            </span>
          </div>
        </header>
        <div className="grid grid-cols-2 gap-3 md:grid-cols-3">
          <div className="rounded-xl border border-stone-800 bg-stone-900 p-4">
            <Truck className="mb-2 text-emerald-400" size={18} />
            <div data-testid="tracking-vehicle-count" className="text-2xl font-bold">{vehicles.length}</div>
            <p className="text-xs text-stone-400">Observed vehicles</p>
          </div>
          <div className="rounded-xl border border-stone-800 bg-stone-900 p-4">
            <Activity className="mb-2 text-emerald-400" size={18} />
            <div data-testid="tracking-fresh-count" className="text-2xl font-bold">{fresh.length}</div>
            <p className="text-xs text-stone-400">Fresh GPS (last 60 s)</p>
          </div>
          <div className="col-span-2 rounded-xl border border-stone-800 bg-stone-900 p-4 md:col-span-1">
            <Clock3 className="mb-2 text-amber-400" size={18} />
            <div className="text-sm font-semibold">{connected ? "Socket connected" : "Live feed unavailable"}</div>
            <p className="text-xs text-stone-400">Disconnected positions are never labelled live</p>
          </div>
        </div>
        <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_320px]">
          <div className="h-[460px] min-h-0 md:h-[620px]">
            <LocalLiveTrackingMap vehicles={vehicles} now={now} />
          </div>
          <section className="rounded-2xl border border-stone-800 bg-stone-900 p-4">
            <h2 className="mb-4 font-semibold">Verified position stream</h2>
            <div className="max-h-[550px] space-y-3 overflow-auto">
              {vehicles.length === 0 ? (
                <div data-testid="no-live-vehicles" className="rounded-lg border border-dashed border-stone-700 p-4 text-sm text-stone-400">
                  No live or saved GPS events available.
                </div>
              ) : vehicles.map(vehicle => {
                const ageMs = Math.max(0, now - Date.parse(vehicle.observed_at));
                const stale = !connected || ageMs > STALE_AFTER_MS;
                return (
                  <article key={vehicle.vehicle_id} data-testid="tracking-vehicle-row" className="rounded-xl border border-stone-800 bg-stone-950 p-3">
                    <div className="flex items-center justify-between gap-2">
                      <p title={vehicle.vehicle_id} className="truncate font-mono text-xs">{vehicle.vehicle_id.slice(0, 12)}…</p>
                      <span data-testid="tracking-freshness" className={stale ? "text-xs font-semibold text-amber-400" : "text-xs font-semibold text-emerald-400"}>
                        {stale ? "STALE / OFFLINE" : "FRESH"}
                      </span>
                    </div>
                    <p className="mt-2 text-xs text-stone-400">
                      {vehicle.location.latitude.toFixed(5)}, {vehicle.location.longitude.toFixed(5)}
                    </p>
                    <p className="mt-1 text-xs text-stone-500">Observed {new Date(vehicle.observed_at).toLocaleString()}</p>
                    <p className="mt-1 text-xs text-stone-500">
                      {vehicle.source === "postgres" ? "PostGIS snapshot" : "Kafka GPS event"}
                    </p>
                  </article>
                );
              })}
            </div>
          </section>
        </div>
        <p className="flex items-start gap-2 rounded-xl border border-amber-800/40 bg-amber-950/20 p-4 text-xs text-amber-200">
          <AlertTriangle className="shrink-0" size={16} />
          Local-only P1 test surface. Production WebSocket access is deliberately disabled
          until authenticated, permission-scoped streaming is implemented. No simulated live metrics.
        </p>
      </main>
      <SiteFooter />
    </div>
  );
}

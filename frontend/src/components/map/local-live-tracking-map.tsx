"use client";

import { Component, type ReactNode } from "react";
import Map, { Marker, NavigationControl } from "react-map-gl/maplibre";
import "maplibre-gl/dist/maplibre-gl.css";

import type { LiveVehicle } from "@/hooks/use-live-tracking";

const DEFAULT_VIEW = { longitude: -4.2518, latitude: 55.8642, zoom: 11 };

class MapErrorBoundary extends Component<
  { children: ReactNode },
  { failed: boolean }
> {
  state = { failed: false };

  static getDerivedStateFromError() {
    return { failed: true };
  }

  render() {
    return this.state.failed ? (
      <div role="status" data-testid="map-fallback" className="flex h-full items-center justify-center p-6 text-center text-sm text-stone-300">
        Map rendering unavailable. The validated GPS feed and timestamps remain accessible.
      </div>
    ) : this.props.children;
  }
}

function supportsWebGL() {
  if (typeof document === "undefined") return false;
  try {
    const canvas = document.createElement("canvas");
    return Boolean(canvas.getContext("webgl2") || canvas.getContext("webgl"));
  } catch {
    return false;
  }
}

export default function LocalLiveTrackingMap({
  vehicles, now, connected = true,
}: {
  vehicles: LiveVehicle[];
  now: number;
  connected?: boolean;
}) {
  // A camera position should never be undefined during MapLibre construction.
  // Use an uncontrolled map with a grounded initial location, and recenter
  // once when the first actual vehicle becomes available.
  const first = vehicles[0];
  const initialViewState = first
    ? { longitude: first.location.longitude, latitude: first.location.latitude, zoom: 12 }
    : DEFAULT_VIEW;

  return (
    <div data-testid="live-map" className="relative h-full min-h-[320px] overflow-hidden rounded-2xl border border-stone-800 bg-stone-950">
      {supportsWebGL() ? (
        <MapErrorBoundary>
          <Map
            key={first?.vehicle_id ?? "untracked"}
            initialViewState={initialViewState}
            mapStyle="https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json"
            style={{ width: "100%", height: "100%" }}
          >
            <NavigationControl position="bottom-right" />
            {vehicles.map(vehicle => {
              const stale = !connected || now - Date.parse(vehicle.observed_at) > 60_000;
              return (
                <Marker
                  key={vehicle.vehicle_id}
                  longitude={vehicle.location.longitude}
                  latitude={vehicle.location.latitude}
                >
                  <div
                    data-testid="live-vehicle-marker"
                    aria-label={stale ? "Stale vehicle" : "Fresh tracked vehicle"}
                    title={vehicle.vehicle_id}
                    className={`h-4 w-4 rounded-full border-2 border-stone-950 shadow-lg ${
                      stale ? "bg-amber-400" : "bg-emerald-400"
                    }`}
                  />
                </Marker>
              );
            })}
          </Map>
        </MapErrorBoundary>
      ) : (
        <div role="status" data-testid="map-fallback" className="flex h-full items-center justify-center p-6 text-center text-sm text-stone-300">
          WebGL is unavailable. The verified GPS coordinates and freshness remain visible in the position feed.
        </div>
      )}
      {vehicles.length === 0 && (
        <div className="pointer-events-none absolute inset-0 flex items-center justify-center bg-stone-950/75 p-6 text-center text-sm text-stone-300">
          No verified GPS positions yet. Start the local backend, outbox worker and Kafka consumer.
        </div>
      )}
    </div>
  );
}

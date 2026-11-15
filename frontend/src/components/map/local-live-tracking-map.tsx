"use client";

import { useEffect, useRef, useState } from "react";
import Map, { Marker, NavigationControl } from "react-map-gl/maplibre";
import "maplibre-gl/dist/maplibre-gl.css";

import type { LiveVehicle } from "@/hooks/use-live-tracking";

export default function LocalLiveTrackingMap({ vehicles, now }: {
  vehicles: LiveVehicle[];
  now: number;
}) {
  const [view, setView] = useState({
    longitude: -4.2518, latitude: 55.8642, zoom: 11,
  });
  const centered = useRef(false);
  useEffect(() => {
    if (!centered.current && vehicles.length > 0) {
      centered.current = true;
      const first = vehicles[0];
      // Follow the first observed vehicle, not a hard-coded demo city.
      setView(prev => ({
        ...prev,
        longitude: first.location.longitude,
        latitude: first.location.latitude,
        zoom: 12,
      }));
    }
  }, [vehicles]);
  return (
    <div data-testid="live-map" className="relative h-full min-h-[320px] overflow-hidden rounded-2xl border border-stone-800">
      <Map
        {...view}
        onMove={event => setView(event.viewState)}
        mapStyle="https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json"
        style={{ width: "100%", height: "100%" }}
      >
        <NavigationControl position="bottom-right" />
        {vehicles.map(vehicle => {
          const stale = now - Date.parse(vehicle.observed_at) > 60_000;
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
                className={`rounded-full border-2 border-stone-950 shadow-lg ${
                  stale ? "bg-amber-400" : "bg-emerald-400"
                } h-4 w-4`}
              />
            </Marker>
          );
        })}
      </Map>
      {vehicles.length === 0 && (
        <div className="pointer-events-none absolute inset-0 flex items-center justify-center bg-stone-950/70 p-6 text-center text-sm text-stone-300">
          No verified GPS positions yet. Start the local backend, outbox worker and Kafka consumer.
        </div>
      )}
    </div>
  );
}

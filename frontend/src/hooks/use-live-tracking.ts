"use client";

import { useEffect, useState } from "react";
import { z } from "zod";

const vehicleSchema = z.object({
  vehicle_id: z.string().uuid(),
  driver_id: z.string().uuid().nullable().optional(),
  event_id: z.string().uuid().nullable().optional(),
  location: z.object({
    latitude: z.number().finite().min(-90).max(90),
    longitude: z.number().finite().min(-180).max(180),
  }),
  observed_at: z.string().datetime({ offset: true }),
  speed_kmh: z.number().nonnegative().nullable().optional(),
  heading: z.number().min(0).max(360).nullable().optional(),
  source: z.enum(["kafka", "postgres"]),
});

export type LiveVehicle = z.infer<typeof vehicleSchema>;
export type LiveConnection = "signed-out" | "unconfigured" | "connecting" | "connected" | "reconnecting" | "unauthorized";
export const STALE_AFTER_MS = 60_000;

export function mergeLivePosition(
  previous: Record<string, LiveVehicle>,
  candidate: unknown,
): Record<string, LiveVehicle> {
  const parsed = vehicleSchema.safeParse(candidate);
  if (!parsed.success) return previous;
  const next = parsed.data;
  const observed = Date.parse(next.observed_at);
  if (!Number.isFinite(observed) || observed > Date.now() + 5 * 60_000) return previous;

  const existing = previous[next.vehicle_id];
  if (existing && Date.parse(existing.observed_at) >= observed) return previous;
  return { ...previous, [next.vehicle_id]: next };
}

export function useLiveTracking(accessToken: string | null) {
  const [positions, setPositions] = useState<Record<string, LiveVehicle>>({});
  const [connection, setConnection] = useState<LiveConnection>("signed-out");
  const [now, setNow] = useState(() => Date.now());

  useEffect(() => {
    const localhost = ["localhost", "127.0.0.1"].includes(window.location.hostname);
    const url = process.env.NEXT_PUBLIC_WS_URL || (localhost ? "ws://localhost:8000/ws" : "");
    // No unauthenticated socket is opened. The access token lives only in
    // React component memory; it is never sent as a URL, cookie or subprotocol.
    if (!accessToken || !url || (!localhost && url.startsWith("ws://"))) {
      const frame = requestAnimationFrame(() => {
        setConnection(accessToken ? "unconfigured" : "signed-out");
        setPositions({});
      });
      return () => cancelAnimationFrame(frame);
    }
    let stopped = false;
    let retry = 0;
    let socket: WebSocket | null = null;
    let retryTimer: ReturnType<typeof setTimeout> | undefined;
    let pingTimer: ReturnType<typeof setInterval> | undefined;
    const clock = setInterval(() => setNow(Date.now()), 10_000);

    const connect = () => {
      if (stopped) return;
      setConnection(retry ? "reconnecting" : "connecting");
      try {
        socket = new WebSocket(url);
      } catch {
        scheduleRetry();
        return;
      }
      socket.onopen = () => {
        retry = 0;
        socket?.send(JSON.stringify({ action: "authenticate", token: accessToken }));
        if (pingTimer) clearInterval(pingTimer);
        pingTimer = setInterval(() => {
          if (socket?.readyState === WebSocket.OPEN) {
            socket.send(JSON.stringify({ action: "ping" }));
          }
        }, 30_000);
      };
      socket.onmessage = event => {
        try {
          const message = JSON.parse(event.data) as { type?: string; data?: unknown };
          if (message.type === "authenticated") {
            setConnection("connected");
            socket?.send(JSON.stringify({ action: "subscribe", channel: "vehicles" }));
          } else if (message.type === "vehicle_update") {
            setPositions(previous => mergeLivePosition(previous, message.data));
          } else if (message.type === "vehicle_snapshot") {
            const snapshot = z.object({ vehicles: z.array(z.unknown()).max(100) }).safeParse(message.data);
            if (snapshot.success) {
              setPositions(previous =>
                snapshot.data.vehicles.reduce(mergeLivePosition, previous),
              );
            }
          }
        } catch {
          // Invalid socket messages never create map markers.
        }
      };
      socket.onclose = (event) => {
        if (pingTimer) clearInterval(pingTimer);
        if (stopped) return;
        // 1008 signals expired, revoked or insufficiently scoped credentials.
        // Do not reconnect or retain another user's previously visible GPS.
        if (event.code === 1008) {
          setPositions({});
          setConnection("unauthorized");
          return;
        }
        scheduleRetry();
      };
      socket.onerror = () => {
        // Closing triggers bounded reconnect and resubscription.
        socket?.close();
      };
    };
    function scheduleRetry() {
      if (stopped) return;
      setConnection("reconnecting");
      const delay = Math.min(15_000, 1_000 * 2 ** Math.min(retry++, 4));
      retryTimer = setTimeout(connect, delay);
    }

    connect();
    return () => {
      stopped = true;
      clearInterval(clock);
      if (retryTimer) clearTimeout(retryTimer);
      if (pingTimer) clearInterval(pingTimer);
      socket?.close();
    };
  }, [accessToken]);

  const vehicles = Object.values(positions);
  const fresh = vehicles.filter(
    vehicle => connection === "connected" && now - Date.parse(vehicle.observed_at) <= STALE_AFTER_MS,
  );
  return { vehicles, fresh, connection, now };
}

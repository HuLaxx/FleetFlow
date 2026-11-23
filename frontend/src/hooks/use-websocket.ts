'use client';

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { z } from 'zod';
import { wsClient, type WebSocketMessage } from '../lib/websocket';

type EventHandler = (message: WebSocketMessage) => void;

const incomingMessageSchema = z.object({
    type: z.string(),
    data: z.unknown(),
    timestamp: z.string().optional(),
});

const vehicleUpdateSchema = z.object({ vehicle_id: z.string() }).passthrough();
const driverUpdateSchema = z.object({ driver_id: z.string() }).passthrough();
const orderUpdateSchema = z.object({ order_id: z.string() }).passthrough();
const routeUpdateSchema = z.object({ route_id: z.string() }).passthrough();

export function useWebSocket(channels: string | string[] = 'all') {
    const channelKey = JSON.stringify(Array.isArray(channels) ? channels : [channels]);
    const channelArray = useMemo(() => JSON.parse(channelKey) as string[], [channelKey]);
    const handlersRef = useRef(new Map<string, Set<EventHandler>>());

    const [isConnected, setIsConnected] = useState(false);
    const [lastMessage, setLastMessage] = useState<WebSocketMessage | null>(null);

    const on = useCallback((type: string, handler: EventHandler) => {
        let handlers = handlersRef.current.get(type);
        if (!handlers) {
            handlers = new Set();
            handlersRef.current.set(type, handlers);
        }
        handlers.add(handler);
    }, []);

    const off = useCallback((type: string, handler: EventHandler) => {
        handlersRef.current.get(type)?.delete(handler);
    }, []);

    useEffect(() => {
        function handleConnected() {
            setIsConnected(true);
            channelArray.forEach(channel => wsClient.subscribe(channel));
        }

        function handleDisconnected() {
            setIsConnected(false);
        }

        function handleMessage(event?: unknown) {
            const parsed = incomingMessageSchema.safeParse(event);
            if (!parsed.success) return;
            const message = parsed.data;
            setLastMessage(message);
            handlersRef.current.get(message.type)?.forEach(handler => handler(message));
            handlersRef.current.get('*')?.forEach(handler => handler(message));
        }

        wsClient.on('connected', handleConnected);
        wsClient.on('disconnected', handleDisconnected);
        wsClient.on('message', handleMessage);
        wsClient.connect();

        // The socket is a shared singleton. Existing connections do not emit a
        // second 'connected' event for newly mounted consumers.
        const readyFrame = requestAnimationFrame(() => {
            if (wsClient.isOpen()) handleConnected();
        });

        return () => {
            cancelAnimationFrame(readyFrame);
            channelArray.forEach(channel => wsClient.unsubscribe(channel));
            wsClient.off('connected', handleConnected);
            wsClient.off('disconnected', handleDisconnected);
            wsClient.off('message', handleMessage);
        };
    }, [channelArray]);

    return { isConnected, lastMessage, wsClient, on, off };
}

function useEventMap<T extends { [key: string]: unknown }>(
    channel: string, types: string[], schema: z.ZodType<T>, idField: keyof T
) {
    const [records, setRecords] = useState<Map<string, T>>(new Map());
    const { isConnected, on, off } = useWebSocket(channel);
    const typeKey = types.join('|');

    useEffect(() => {
        const handler = (message: WebSocketMessage) => {
            const parsed = schema.safeParse(message.data);
            if (!parsed.success) return;
            const record = parsed.data;
            const id = record[idField];
            if (typeof id !== 'string') return;
            setRecords(prev => new Map(prev).set(id, record));
        };

        const keys = typeKey.split('|');
        keys.forEach(key => on(key, handler));
        return () => keys.forEach(key => off(key, handler));
    }, [on, off, schema, idField, typeKey]);

    return { records: Array.from(records.values()), isConnected };
}

export function useVehicleUpdates() {
    const { records, isConnected } = useEventMap('vehicles', ['vehicle_update'], vehicleUpdateSchema, 'vehicle_id');
    return { vehicles: records, isConnected };
}

export function useDriverUpdates() {
    const { records, isConnected } = useEventMap('drivers', ['driver_status_update'], driverUpdateSchema, 'driver_id');
    return { drivers: records, isConnected };
}

export function useOrderUpdates() {
    const { records, isConnected } = useEventMap('orders', ['order_created', 'order_cancelled'], orderUpdateSchema, 'order_id');
    return { orders: records, isConnected };
}

export function useRouteUpdates() {
    const { records, isConnected } = useEventMap('routes', ['route_started', 'stop_completed'], routeUpdateSchema, 'route_id');
    return { routes: records, isConnected };
}

'use client';

import { useEffect, useState, useCallback } from 'react';
import { wsClient, WebSocketMessage } from '../lib/websocket';

type EventHandler = (message: WebSocketMessage) => void;

export function useWebSocket(channels: string | string[] = ['all']) {
    // Normalize channels to always be an array
    const channelArray = Array.isArray(channels) ? channels : [channels];

    const [isConnected, setIsConnected] = useState(false);
    const [lastMessage, setLastMessage] = useState<WebSocketMessage | null>(null);
    const [eventHandlers, setEventHandlers] = useState<Map<string, EventHandler[]>>(new Map());

    // Subscribe to specific event types
    const on = useCallback((eventType: string, handler: EventHandler) => {
        setEventHandlers(prev => {
            const newMap = new Map(prev);
            const handlers = newMap.get(eventType) || [];
            newMap.set(eventType, [...handlers, handler]);
            return newMap;
        });
    }, []);

    // Unsubscribe from event types
    const off = useCallback((eventType: string, handler: EventHandler) => {
        setEventHandlers(prev => {
            const newMap = new Map(prev);
            const handlers = newMap.get(eventType) || [];
            newMap.set(eventType, handlers.filter(h => h !== handler));
            return newMap;
        });
    }, []);

    useEffect(() => {
        // Connect to WebSocket
        wsClient.connect();

        function handleConnected() {
            setIsConnected(true);

            // Subscribe to all requested channels
            channelArray.forEach((channel: string) => {
                wsClient.subscribe(channel);
            });
        }

        function handleDisconnected() {
            setIsConnected(false);
        }

        function handleMessage(message: WebSocketMessage) {
            setLastMessage(message);

            // Trigger event-specific handlers
            const handlers = eventHandlers.get(message.type) || [];
            handlers.forEach(handler => handler(message));

            // Also trigger 'all' handlers
            const allHandlers = eventHandlers.get('*') || [];
            allHandlers.forEach(handler => handler(message));
        }

        wsClient.on('connected', handleConnected);
        wsClient.on('disconnected', handleDisconnected);
        wsClient.on('message', handleMessage as (event?: unknown) => void);

        // Check if already connected
        // @ts-ignore - accessing private property for state check
        if (wsClient['ws']?.readyState === 1) {
            handleConnected();
        }

        return () => {
            // Unsubscribe from channels
            channelArray.forEach((channel: string) => {
                wsClient.unsubscribe(channel);
            });

            wsClient.off('connected', handleConnected);
            wsClient.off('disconnected', handleDisconnected);
            wsClient.off('message', handleMessage as (event?: unknown) => void);
        };
    }, [channelArray, eventHandlers]);

    return { isConnected, lastMessage, wsClient, on, off };
}

/**
 * Hook for real-time vehicle updates
 */
export function useVehicleUpdates() {
    const [vehicles, setVehicles] = useState<Map<string, any>>(new Map());
    const { isConnected, on, off } = useWebSocket(['vehicles']);

    useEffect(() => {
        const handler = (message: WebSocketMessage) => {
            if (message.type === 'vehicle_update') {
                setVehicles(prev => {
                    const next = new Map(prev);
                    next.set(message.data.vehicle_id, message.data);
                    return next;
                });
            }
        };

        on('vehicle_update', handler);
        return () => off('vehicle_update', handler);
    }, [on, off]);

    return { vehicles: Array.from(vehicles.values()), isConnected };
}

/**
 * Hook for real-time driver status updates
 */
export function useDriverUpdates() {
    const [drivers, setDrivers] = useState<Map<string, any>>(new Map());
    const { isConnected, on, off } = useWebSocket(['drivers']);

    useEffect(() => {
        const handler = (message: WebSocketMessage) => {
            if (message.type === 'driver_status_update') {
                setDrivers(prev => {
                    const next = new Map(prev);
                    next.set(message.data.driver_id, message.data);
                    return next;
                });
            }
        };

        on('driver_status_update', handler);
        return () => off('driver_status_update', handler);
    }, [on, off]);

    return { drivers: Array.from(drivers.values()), isConnected };
}

/**
 * Hook for real-time order updates
 */
export function useOrderUpdates() {
    const [orders, setOrders] = useState<Map<string, any>>(new Map());
    const { isConnected, on, off } = useWebSocket(['orders']);

    useEffect(() => {
        const handler = (message: WebSocketMessage) => {
            if (message.type === 'order_created' || message.type === 'order_cancelled') {
                setOrders(prev => {
                    const next = new Map(prev);
                    next.set(message.data.order_id, message.data);
                    return next;
                });
            }
        };

        on('order_created', handler);
        on('order_cancelled', handler);

        return () => {
            off('order_created', handler);
            off('order_cancelled', handler);
        };
    }, [on, off]);

    return { orders: Array.from(orders.values()), isConnected };
}

/**
 * Hook for real-time route updates
 */
export function useRouteUpdates() {
    const [routes, setRoutes] = useState<Map<string, any>>(new Map());
    const { isConnected, on, off } = useWebSocket(['routes']);

    useEffect(() => {
        const handler = (message: WebSocketMessage) => {
            if (message.type === 'route_started' || message.type === 'stop_completed') {
                setRoutes(prev => {
                    const next = new Map(prev);
                    next.set(message.data.route_id, message.data);
                    return next;
                });
            }
        };

        on('route_started', handler);
        on('stop_completed', handler);

        return () => {
            off('route_started', handler);
            off('stop_completed', handler);
        };
    }, [on, off]);

    return { routes: Array.from(routes.values()), isConnected };
}

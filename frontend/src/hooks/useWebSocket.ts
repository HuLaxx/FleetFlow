'use client';

import { useEffect, useRef, useState, useCallback } from 'react';

export interface WebSocketMessage {
    type: string;
    data: Record<string, unknown>;
    timestamp: string;
}

export interface UseWebSocketOptions {
    url: string;
    reconnectInterval?: number;
    maxReconnectAttempts?: number;
    onMessage?: (message: WebSocketMessage) => void;
    onConnect?: () => void;
    onDisconnect?: () => void;
    onError?: (error: Event) => void;
}

export interface UseWebSocketReturn {
    isConnected: boolean;
    lastMessage: WebSocketMessage | null;
    sendMessage: (action: string, channel?: string) => void;
    subscribe: (channel: string) => void;
    unsubscribe: (channel: string) => void;
    connectionState: 'connecting' | 'connected' | 'disconnected' | 'error';
}

const DEFAULT_WS_URL = process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8002/ws';

export function useWebSocket(options: UseWebSocketOptions): UseWebSocketReturn {
    const {
        url,
        reconnectInterval = 3000,
        maxReconnectAttempts = 5,
        onMessage,
        onConnect,
        onDisconnect,
        onError,
    } = options;

    const wsRef = useRef<WebSocket | null>(null);
    const reconnectAttempts = useRef(0);
    const reconnectTimeout = useRef<NodeJS.Timeout | null>(null);

    const [isConnected, setIsConnected] = useState(false);
    const [lastMessage, setLastMessage] = useState<WebSocketMessage | null>(null);
    const [connectionState, setConnectionState] = useState<'connecting' | 'connected' | 'disconnected' | 'error'>('disconnected');

    const connect = useCallback(function attemptConnect() {
        if (wsRef.current?.readyState === WebSocket.OPEN) {
            return;
        }

        setConnectionState('connecting');

        try {
            wsRef.current = new WebSocket(url);

            wsRef.current.onopen = () => {
                setIsConnected(true);
                setConnectionState('connected');
                reconnectAttempts.current = 0;
                onConnect?.();
            };

            wsRef.current.onclose = () => {
                setIsConnected(false);
                setConnectionState('disconnected');
                onDisconnect?.();

                // Attempt reconnect
                if (reconnectAttempts.current < maxReconnectAttempts) {
                    reconnectTimeout.current = setTimeout(() => {
                        reconnectAttempts.current++;
                        attemptConnect();
                    }, reconnectInterval);
                }
            };

            wsRef.current.onerror = (error) => {
                setConnectionState('error');
                onError?.(error);
            };

            wsRef.current.onmessage = (event) => {
                try {
                    const message: WebSocketMessage = JSON.parse(event.data);
                    setLastMessage(message);
                    onMessage?.(message);
                } catch {
                    console.error('Failed to parse WebSocket message');
                }
            };
        } catch (error) {
            setConnectionState('error');
            console.error('WebSocket connection failed:', error);
        }
    }, [url, reconnectInterval, maxReconnectAttempts, onMessage, onConnect, onDisconnect, onError]);

    const disconnect = useCallback(() => {
        if (reconnectTimeout.current) {
            clearTimeout(reconnectTimeout.current);
        }

        if (wsRef.current) {
            wsRef.current.close();
            wsRef.current = null;
        }
    }, []);

    const sendMessage = useCallback((action: string, channel?: string) => {
        if (wsRef.current?.readyState === WebSocket.OPEN) {
            wsRef.current.send(JSON.stringify({ action, channel }));
        }
    }, []);

    const subscribe = useCallback((channel: string) => {
        sendMessage('subscribe', channel);
    }, [sendMessage]);

    const unsubscribe = useCallback((channel: string) => {
        sendMessage('unsubscribe', channel);
    }, [sendMessage]);

    useEffect(() => {
        connect();
        return () => disconnect();
    }, [connect, disconnect]);

    return {
        isConnected,
        lastMessage,
        sendMessage,
        subscribe,
        unsubscribe,
        connectionState,
    };
}

// Vehicle location hook
export interface VehicleLocation {
    vehicle_id: string;
    driver: string;
    location: {
        latitude: number;
        longitude: number;
    };
    speed_kmh: number;
    heading: number;
}

export function useVehicleTracking(wsUrl: string = DEFAULT_WS_URL) {
    const [vehicles, setVehicles] = useState<Map<string, VehicleLocation>>(new Map());
    const [lastUpdate, setLastUpdate] = useState<Date | null>(null);

    const handleMessage = useCallback((message: WebSocketMessage) => {
        if (message.type === 'vehicle_update') {
            const data = message.data as unknown as VehicleLocation;
            setVehicles(prev => {
                const next = new Map(prev);
                next.set(data.vehicle_id, data);
                return next;
            });
            setLastUpdate(new Date());
        }
    }, []);

    const { isConnected, subscribe, connectionState } = useWebSocket({
        url: wsUrl,
        onMessage: handleMessage,
    });

    useEffect(() => {
        if (isConnected) subscribe('alerts');
    }, [isConnected, subscribe]);

    useEffect(() => {
        if (isConnected) subscribe('orders');
    }, [isConnected, subscribe]);

    useEffect(() => {
        if (isConnected) subscribe('vehicles');
    }, [isConnected, subscribe]);

    return {
        vehicles: Array.from(vehicles.values()),
        vehicleMap: vehicles,
        isConnected,
        connectionState,
        lastUpdate,
    };
}

// Order updates hook
export interface OrderUpdate {
    order_id: string;
    order_number: string;
    status: string;
    eta?: string;
    driver_name?: string;
}

export function useOrderUpdates(wsUrl: string = DEFAULT_WS_URL) {
    const [orders, setOrders] = useState<Map<string, OrderUpdate>>(new Map());

    const handleMessage = useCallback((message: WebSocketMessage) => {
        if (message.type === 'order_update') {
            const data = message.data as unknown as OrderUpdate;
            setOrders(prev => {
                const next = new Map(prev);
                next.set(data.order_id, data);
                return next;
            });
        }
    }, []);

    const { isConnected, subscribe, connectionState } = useWebSocket({
        url: wsUrl,
        onMessage: handleMessage,
    });

    return {
        orders: Array.from(orders.values()),
        isConnected,
        connectionState,
    };
}

// Alerts hook
export interface Alert {
    id: string;
    type: string;
    severity: 'low' | 'medium' | 'high' | 'critical';
    message: string;
    timestamp: string;
}

export function useAlerts(wsUrl: string = DEFAULT_WS_URL) {
    const [alerts, setAlerts] = useState<Alert[]>([]);

    const handleMessage = useCallback((message: WebSocketMessage) => {
        if (message.type === 'alert') {
            const data = message.data as unknown as Alert;
            setAlerts(prev => [data, ...prev].slice(0, 50)); // Keep last 50
        }
    }, []);

    const { isConnected, subscribe, connectionState } = useWebSocket({
        url: wsUrl,
        onMessage: handleMessage,
    });

    const clearAlerts = useCallback(() => {
        setAlerts([]);
    }, []);

    return {
        alerts,
        isConnected,
        connectionState,
        clearAlerts,
    };
}

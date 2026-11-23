import mitt from 'mitt';

export type WebSocketMessage = {
    type: string;
    data: unknown;
    timestamp?: string;
};

export type WebSocketConfig = {
    url: string;
    reconnectInterval?: number;
    maxRetries?: number;
};

type WebSocketEvents = {
    connected: void;
    disconnected: void;
    message: WebSocketMessage;
    [key: string]: unknown;
};

class WebSocketClient {
    private emitter = mitt<WebSocketEvents>();
    private ws: WebSocket | null = null;
    private config: WebSocketConfig;
    private reconnectAttempts = 0;
    private shouldReconnect = true;
    private subscriptions: Set<string> = new Set();
    private pingInterval: NodeJS.Timeout | null = null;

    constructor(config: WebSocketConfig) {
        this.config = {
            reconnectInterval: 3000,
            maxRetries: 5,
            ...config,
        };
    }

    on(type: string, handler: (event?: unknown) => void) {
        this.emitter.on(type, handler);
    }

    off(type: string, handler: (event?: unknown) => void) {
        this.emitter.off(type, handler);
    }

    private emit(type: string, event?: unknown) {
        this.emitter.emit(type as keyof WebSocketEvents, event);
    }

    isOpen(): boolean {
        return this.ws?.readyState === WebSocket.OPEN;
    }

    connect() {
        if (this.ws && (this.ws.readyState === WebSocket.OPEN || this.ws.readyState === WebSocket.CONNECTING)) return;
        this.shouldReconnect = true;
        try {
            this.ws = new WebSocket(this.config.url);

            this.ws.onopen = () => {
                console.log('WebSocket connected');
                this.reconnectAttempts = 0;
                this.emit('connected');
                this.startHeartbeat();

                // Resubscribe to channels
                this.subscriptions.forEach((channel) => {
                    this.subscribe(channel);
                });
            };

            this.ws.onmessage = (event) => {
                try {
                    const message: WebSocketMessage = JSON.parse(event.data);
                    this.emit('message', message);

                    // Emit internal events based on message type
                    if (message.type) {
                        this.emit(message.type, message.data);
                    }
                } catch (error) {
                    console.error('WebSocket message parse error:', error);
                }
            };

            this.ws.onclose = () => {
                this.stopHeartbeat();
                console.log('WebSocket disconnected');
                this.emit('disconnected');

                if (this.shouldReconnect) {
                    this.handleReconnect();
                }
            };

            this.ws.onerror = (error) => {
                console.error('WebSocket error:', error);
                this.emit('error', error);
            };

        } catch (error) {
            console.error('WebSocket connection error:', error);
            this.handleReconnect();
        }
    }

    private handleReconnect() {
        if (this.reconnectAttempts < (this.config.maxRetries || 5)) {
            this.reconnectAttempts++;
            console.log(`Reconnecting in ${this.config.reconnectInterval}ms... (Attempt ${this.reconnectAttempts})`);
            setTimeout(() => this.connect(), this.config.reconnectInterval);
        } else {
            console.error('Max reconnection attempts reached');
        }
    }

    subscribe(channel: string) {
        this.subscriptions.add(channel);
        if (this.ws?.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify({ action: 'subscribe', channel }));
        }
    }

    unsubscribe(channel: string) {
        this.subscriptions.delete(channel);
        if (this.ws?.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify({ action: 'unsubscribe', channel }));
        }
    }

    disconnect() {
        this.shouldReconnect = false;
        this.stopHeartbeat();
        if (this.ws) {
            this.ws.close();
            this.ws = null;
        }
    }

    private startHeartbeat() {
        this.pingInterval = setInterval(() => {
            if (this.ws?.readyState === WebSocket.OPEN) {
                this.ws.send(JSON.stringify({ action: 'ping' }));
            }
        }, 30000);
    }

    private stopHeartbeat() {
        if (this.pingInterval) {
            clearInterval(this.pingInterval);
            this.pingInterval = null;
        }
    }
}

// Singleton instance for the app
// Uses NEXT_PUBLIC_WS_URL when set.
const WS_URL = process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8002/ws';

export const wsClient = new WebSocketClient({
    url: WS_URL,
});

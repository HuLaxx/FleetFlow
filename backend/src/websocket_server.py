"""
FleetFlow WebSocket Server

Real-time communication for:
- Live vehicle tracking
- Order status updates
- Route progress
- System alerts
"""

import asyncio
import json
import os
from dataclasses import asdict, dataclass
from datetime import datetime, UTC
from typing import Any

import structlog
from fastapi import FastAPI, Header, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

logger = structlog.get_logger()

ALLOWED_ORIGINS = [
    origin.strip()
    for origin in os.getenv(
        "WEBSOCKET_ALLOWED_ORIGINS",
        "http://localhost:3000,http://localhost:3001",
    ).split(",")
    if origin.strip()
]
BROADCAST_TOKEN = os.getenv("WEBSOCKET_BROADCAST_TOKEN", "")


@dataclass
class WebSocketMessage:
    """WebSocket message format."""

    type: str  # vehicle_update, order_update, route_update, alert
    data: dict[str, Any]
    timestamp: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now(UTC).isoformat()

    def to_json(self) -> str:
        return json.dumps(asdict(self))


class ConnectionManager:
    """
    WebSocket connection manager.

    Handles:
    - Multiple clients
    - Channel subscriptions
    - Broadcast and targeted messages
    """

    def __init__(self):
        # All active connections
        self.active_connections: set[WebSocket] = set()

        # Subscriptions by channel
        self.channel_subscriptions: dict[str, set[WebSocket]] = {
            "vehicles": set(),
            "orders": set(),
            "routes": set(),
            "alerts": set(),
            "all": set(),
        }

        # Connection metadata
        self.connection_info: dict[WebSocket, dict[str, Any]] = {}

    async def connect(self, websocket: WebSocket, client_id: str = None) -> None:
        """Accept a new WebSocket connection."""
        await websocket.accept()
        self.active_connections.add(websocket)
        self.connection_info[websocket] = {
            "client_id": client_id or str(id(websocket)),
            "connected_at": datetime.now(UTC).isoformat(),
            "subscriptions": [],
        }

        # Subscribe to 'all' by default
        self.channel_subscriptions["all"].add(websocket)

        logger.info("WebSocket connected", client_id=client_id, total=len(self.active_connections))

    def disconnect(self, websocket: WebSocket) -> None:
        """Remove a WebSocket connection."""
        self.active_connections.discard(websocket)

        # Remove from all channels
        for channel in self.channel_subscriptions.values():
            channel.discard(websocket)

        # Remove metadata
        info = self.connection_info.pop(websocket, {})
        logger.info("WebSocket disconnected", client_id=info.get("client_id"))

    def subscribe(self, websocket: WebSocket, channel: str) -> bool:
        """Subscribe a connection to a channel."""
        if channel in self.channel_subscriptions:
            self.channel_subscriptions[channel].add(websocket)

            if websocket in self.connection_info:
                self.connection_info[websocket]["subscriptions"].append(channel)

            return True
        return False

    def unsubscribe(self, websocket: WebSocket, channel: str) -> bool:
        """Unsubscribe from a channel."""
        if channel in self.channel_subscriptions:
            self.channel_subscriptions[channel].discard(websocket)
            return True
        return False

    async def send_personal(self, websocket: WebSocket, message: WebSocketMessage) -> None:
        """Send message to a specific client."""
        try:
            await websocket.send_text(message.to_json())
        except Exception as e:
            logger.error("Failed to send message", error=str(e))

    async def broadcast(self, message: WebSocketMessage, channel: str = "all") -> int:
        """
        Broadcast message to all subscribers of a channel.

        Returns:
            Number of clients sent to
        """
        connections = self.channel_subscriptions.get(channel, set())
        sent = 0

        for connection in list(connections):
            try:
                await connection.send_text(message.to_json())
                sent += 1
            except Exception:
                # Connection might be dead, remove it
                self.disconnect(connection)

        return sent

    async def broadcast_all(self, message: WebSocketMessage) -> int:
        """Broadcast to all connected clients."""
        sent = 0
        for connection in list(self.active_connections):
            try:
                await connection.send_text(message.to_json())
                sent += 1
            except Exception:
                self.disconnect(connection)
        return sent

    @property
    def connection_count(self) -> int:
        return len(self.active_connections)

    def get_stats(self) -> dict[str, Any]:
        """Get connection statistics."""
        return {
            "total_connections": self.connection_count,
            "channels": {
                channel: len(subs) for channel, subs in self.channel_subscriptions.items()
            },
        }


# Global connection manager
manager = ConnectionManager()

# FastAPI app
app = FastAPI(
    title="FleetFlow WebSocket Server",
    description="Real-time updates for fleet tracking",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health():
    """Health check with connection stats."""
    return {
        "status": "healthy",
        **manager.get_stats(),
    }


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, client_id: str = None):
    """
    Main WebSocket endpoint.

    Message format (from client):
    {
        "action": "subscribe" | "unsubscribe" | "ping",
        "channel": "vehicles" | "orders" | "routes" | "alerts"
    }
    """
    origin = websocket.headers.get("origin")
    if origin and origin not in ALLOWED_ORIGINS:
        await websocket.close(code=1008)
        return

    await manager.connect(websocket, client_id)

    try:
        # Send welcome message
        await manager.send_personal(
            websocket,
            WebSocketMessage(
                type="connected",
                data={
                    "message": "Connected to FleetFlow",
                    "channels": list(manager.channel_subscriptions.keys()),
                },
            ),
        )

        while True:
            # Receive and process client messages
            data = await websocket.receive_text()

            try:
                message = json.loads(data)
                action = message.get("action")
                channel = message.get("channel")

                if action == "subscribe" and channel:
                    success = manager.subscribe(websocket, channel)
                    await manager.send_personal(
                        websocket,
                        WebSocketMessage(
                            type="subscribed" if success else "error",
                            data={"channel": channel, "success": success},
                        ),
                    )

                elif action == "unsubscribe" and channel:
                    success = manager.unsubscribe(websocket, channel)
                    await manager.send_personal(
                        websocket, WebSocketMessage(type="unsubscribed", data={"channel": channel})
                    )

                elif action == "ping":
                    await manager.send_personal(websocket, WebSocketMessage(type="pong", data={}))

            except json.JSONDecodeError:
                await manager.send_personal(
                    websocket, WebSocketMessage(type="error", data={"message": "Invalid JSON"})
                )

    except WebSocketDisconnect:
        manager.disconnect(websocket)


@app.post("/broadcast/{channel}")
async def broadcast_to_channel(
    channel: str,
    message: dict[str, Any],
    x_broadcast_token: str = Header(default=""),
):
    """
    Broadcast a message to a channel (internal API).

    Used by other services to push updates.
    """
    if BROADCAST_TOKEN and x_broadcast_token != BROADCAST_TOKEN:
        raise HTTPException(status_code=401, detail="Unauthorized")
    ws_message = WebSocketMessage(
        type=f"{channel}_update",
        data=message,
    )

    sent = await manager.broadcast(ws_message, channel)

    return {
        "status": "sent",
        "channel": channel,
        "recipients": sent,
    }


# ============================================
# Background task for simulated updates
# ============================================


async def simulate_vehicle_updates():
    """Simulate vehicle location updates for demo."""
    import random

    vehicles = [
        {"id": "v1", "driver": "Marcus J.", "lat": 40.7484, "lon": -73.9857},
        {"id": "v2", "driver": "Sarah C.", "lat": 40.7831, "lon": -73.9712},
        {"id": "v3", "driver": "James W.", "lat": 40.7128, "lon": -74.0060},
    ]

    while True:
        for vehicle in vehicles:
            # Simulate movement
            vehicle["lat"] += random.uniform(-0.001, 0.001)
            vehicle["lon"] += random.uniform(-0.001, 0.001)
            vehicle["speed"] = random.uniform(20, 50)
            vehicle["heading"] = random.uniform(0, 360)

            await manager.broadcast(
                WebSocketMessage(
                    type="vehicle_update",
                    data={
                        "vehicle_id": vehicle["id"],
                        "driver": vehicle["driver"],
                        "location": {
                            "latitude": round(vehicle["lat"], 6),
                            "longitude": round(vehicle["lon"], 6),
                        },
                        "speed_kmh": round(vehicle["speed"], 1),
                        "heading": round(vehicle["heading"], 1),
                    },
                ),
                channel="vehicles",
            )

        await asyncio.sleep(2)  # Update every 2 seconds


@app.on_event("startup")
async def startup():
    """Start background tasks."""
    asyncio.create_task(simulate_vehicle_updates())
    logger.info("WebSocket server started")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("websocket_server:app", host="0.0.0.0", port=8002, reload=True, log_level="info")

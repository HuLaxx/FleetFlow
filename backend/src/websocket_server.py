"""
FleetFlow WebSocket Server

Real-time communication for:
- Live vehicle tracking
- Order status updates
- Route progress
- System alerts
"""

import json
import os
import secrets
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from typing import Any

import structlog
from fastapi import FastAPI, Header, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select

from src.config import get_settings
from src.database import AsyncSessionLocal
from src.models import Vehicle

logger = structlog.get_logger()

ALLOWED_ORIGINS = [
    origin.strip()
    for origin in os.getenv(
        "WEBSOCKET_ALLOWED_ORIGINS",
        "http://localhost:3000,http://localhost:3001,http://127.0.0.1:3000",
    ).split(",")
    if origin.strip()
]
BROADCAST_TOKEN = os.getenv("WEBSOCKET_BROADCAST_TOKEN", "")
settings = get_settings()


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

    async def connect(self, websocket: WebSocket, client_id: str | None = None) -> None:
        """Accept a new WebSocket connection."""
        await websocket.accept()
        self.active_connections.add(websocket)
        self.connection_info[websocket] = {
            "client_id": client_id or str(id(websocket)),
            "connected_at": datetime.now(UTC).isoformat(),
            "subscriptions": [],
        }

        # No implicit subscriptions: explicitly request a channel.

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
        except (WebSocketDisconnect, RuntimeError, OSError) as e:
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
            except (WebSocketDisconnect, RuntimeError, OSError):
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
            except (WebSocketDisconnect, RuntimeError, OSError):
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
async def websocket_endpoint(websocket: WebSocket, client_id: str | None = None):
    """
    Main WebSocket endpoint.

    Message format (from client):
    {
        "action": "subscribe" | "unsubscribe" | "ping",
        "channel": "vehicles" | "orders" | "routes" | "alerts"
    }
    """
    origin = websocket.headers.get("origin")
    # Fail closed outside the local development environment until an
    # authenticated remote WebSocket handshake is implemented.
    if settings.environment != "development" or origin not in ALLOWED_ORIGINS:
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
                    if success and channel == "vehicles":
                        # Snapshot-on-subscribe restores missed best-effort updates.
                        async with AsyncSessionLocal() as session:
                            positions = (
                                await session.scalars(
                                    select(Vehicle)
                                    .where(Vehicle.last_gps_at.is_not(None))
                                    .order_by(Vehicle.last_gps_at.desc())
                                    .limit(100)
                                )
                            ).all()
                            await manager.send_personal(
                                websocket,
                                WebSocketMessage(
                                    type="vehicle_snapshot",
                                    data={
                                        "vehicles": [
                                            {
                                                "vehicle_id": str(vehicle.id),
                                                "driver_id": (
                                                    str(vehicle.current_driver_id)
                                                    if vehicle.current_driver_id
                                                    else None
                                                ),
                                                "location": {
                                                    "latitude": float(vehicle.latitude),
                                                    "longitude": float(vehicle.longitude),
                                                },
                                                "observed_at": vehicle.last_gps_at.isoformat()
                                                + "Z",
                                                "event_id": (
                                                    str(vehicle.last_gps_event_id)
                                                    if vehicle.last_gps_event_id
                                                    else None
                                                ),
                                                "source": "postgres",
                                            }
                                            for vehicle in positions
                                            if vehicle.latitude is not None
                                            and vehicle.longitude is not None
                                        ],
                                        "limit": 100,
                                    },
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
        pass
    finally:
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
    if not BROADCAST_TOKEN or not secrets.compare_digest(x_broadcast_token, BROADCAST_TOKEN):
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


# The public Next.js demo uses explicitly seeded map fixtures. This service
# never manufactures simulated GPS broadcasts in the background.


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("src.main:app", host="127.0.0.1", port=8000, reload=False)

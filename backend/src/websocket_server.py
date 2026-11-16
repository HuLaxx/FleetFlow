"""Authenticated, scoped GPS WebSocket for one local FastAPI process.

A browser must authenticate with a short-lived *access* JWT in its first
WebSocket frame. Tokens are never read from URL queries, subprotocols or
cookies. No location, subscription or snapshot is sent before authentication.
GPS delivery is best effort; snapshot recovery is via durable PostGIS.
"""

import asyncio
import json
import os
import secrets
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

import structlog
from fastapi import FastAPI, Header, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from src.auth.jwt import decode_token
from src.config import get_settings
from src.database import AsyncSessionLocal
from src.models import Vehicle
from src.models.user import User, UserRole

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
    """Versioned channel envelope; never embeds credentials."""

    type: str
    data: dict[str, Any]
    timestamp: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now(UTC).isoformat()

    def to_json(self) -> str:
        return json.dumps(asdict(self))


def may_view_vehicle(user: User, vehicle: Vehicle) -> bool:
    """Deny by default; all scopes are from the database, not JWT claims."""
    if not user.is_active:
        return False
    if user.role == UserRole.ADMIN:
        return True
    if user.role == UserRole.DISPATCHER:
        return user.depot_id is not None and user.depot_id == vehicle.depot_id
    if user.role == UserRole.DRIVER:
        return user.driver_id is not None and user.driver_id == vehicle.current_driver_id
    return False


def may_subscribe(user: User) -> bool:
    """Unscoped viewers/dispatchers/drivers cannot subscribe."""
    if not user.is_active:
        return False
    if user.role == UserRole.ADMIN:
        return True
    if user.role == UserRole.DISPATCHER:
        return user.depot_id is not None
    if user.role == UserRole.DRIVER:
        return user.driver_id is not None
    return False


async def authenticate_access_token(token: str) -> tuple[User, datetime] | None:
    """Validate token purpose, signature/expiry, active DB user and role."""
    if not isinstance(token, str) or not 0 < len(token) <= 4096:
        return None
    data = decode_token(token, expected_type="access")
    if data is None or data.email is None or data.exp is None:
        return None
    expires = data.exp.replace(tzinfo=UTC) if data.exp.tzinfo is None else data.exp
    if expires <= datetime.now(UTC):
        return None
    async with AsyncSessionLocal() as session:
        user = await session.scalar(select(User).where(User.email == data.email))
        if user is None or not user.is_active:
            return None
        if data.role != user.role.value or not may_subscribe(user):
            return None
        # Only identity/scope attributes are retained by the registry.
        # No session or raw access token is kept with the connection.
        return user, expires


class ConnectionManager:
    """In-process, authenticated subscriptions; recheck roles on broadcast."""

    def __init__(self):
        self.active_connections: set[WebSocket] = set()
        self.channel_subscriptions: dict[str, set[WebSocket]] = {"vehicles": set()}
        self.connection_info: dict[WebSocket, dict[str, Any]] = {}

    async def connect(
        self,
        websocket: WebSocket,
        client_id: str | None = None,
        *,
        user: User,
        expires: datetime,
        already_accepted: bool = False,
    ) -> None:
        if not already_accepted:
            await websocket.accept()
        self.active_connections.add(websocket)
        self.connection_info[websocket] = {
            "client_id": client_id or str(id(websocket)),
            "user_id": user.id,
            "role": user.role,
            "driver_id": user.driver_id,
            "depot_id": user.depot_id,
            "expires": expires,
        }
        logger.info("GPS WebSocket authenticated", role=user.role.value)

    def disconnect(self, websocket: WebSocket) -> None:
        self.active_connections.discard(websocket)
        for channel in self.channel_subscriptions.values():
            channel.discard(websocket)
        self.connection_info.pop(websocket, None)

    def subscribe(self, websocket: WebSocket, channel: str) -> bool:
        if (
            channel != "vehicles"
            or websocket not in self.connection_info
            or websocket not in self.active_connections
        ):
            return False
        self.channel_subscriptions["vehicles"].add(websocket)
        return True

    def unsubscribe(self, websocket: WebSocket, channel: str) -> bool:
        if channel != "vehicles":
            return False
        self.channel_subscriptions["vehicles"].discard(websocket)
        return True

    async def send_personal(self, websocket: WebSocket, message: WebSocketMessage) -> None:
        try:
            await websocket.send_text(message.to_json())
        except (WebSocketDisconnect, RuntimeError, OSError):
            self.disconnect(websocket)

    async def revoke(self, websocket: WebSocket) -> None:
        self.disconnect(websocket)
        try:
            await websocket.close(code=1008)
        except (WebSocketDisconnect, RuntimeError, OSError):
            pass

    @staticmethod
    def is_current_user(user: User | None, meta: dict[str, Any] | None) -> bool:
        if not user or not meta or not may_subscribe(user):
            return False
        return (
            meta["expires"] > datetime.now(UTC)
            and user.id == meta["user_id"]
            and user.role == meta["role"]
            and user.driver_id == meta["driver_id"]
            and user.depot_id == meta["depot_id"]
        )

    async def broadcast(self, message: WebSocketMessage, channel: str = "all") -> int:
        """Re-authorize per live update; never fan out GPS via a generic channel."""
        if channel != "vehicles" or message.type != "vehicle_update":
            return 0
        subscribed = list(self.channel_subscriptions["vehicles"])
        if not subscribed:
            return 0
        try:
            vehicle_id = UUID(message.data["vehicle_id"])
        except (KeyError, ValueError, TypeError, AttributeError):
            return 0

        sent = 0
        try:
            async with AsyncSessionLocal() as session:
                vehicle = await session.get(Vehicle, vehicle_id)
                if vehicle is None:
                    return 0
                for socket in subscribed:
                    meta = self.connection_info.get(socket)
                    user = await session.get(User, meta["user_id"]) if meta else None
                    if not self.is_current_user(user, meta):
                        await self.revoke(socket)
                        continue
                    if not may_view_vehicle(user, vehicle):
                        continue
                    await self.send_personal(socket, message)
                    if socket in self.active_connections:
                        sent += 1
        except SQLAlchemyError:
            logger.exception("GPS broadcast denied due to database failure")
        return sent

    async def broadcast_all(self, message: WebSocketMessage) -> int:
        """Never bypass vehicle authorization with a global fanout."""
        return await self.broadcast(message, channel="vehicles")

    @property
    def connection_count(self) -> int:
        return len(self.active_connections)

    def get_stats(self) -> dict[str, Any]:
        return {
            "total_connections": self.connection_count,
            "channels": {
                channel: len(subscriptions)
                for channel, subscriptions in self.channel_subscriptions.items()
            },
        }


manager = ConnectionManager()

# Legacy standalone app remains available only for local HTTP diagnostics.
# Real GPS consumers and browsers share the manager in src.main:app.
app = FastAPI(title="FleetFlow WebSocket Server", version="1.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health():
    return {"status": "healthy", **manager.get_stats()}


async def permitted_snapshot(user_id: UUID, role: UserRole) -> list[dict[str, Any]]:
    """Snapshot filters by *current* database scope, never a client-supplied ID."""
    async with AsyncSessionLocal() as session:
        user = await session.get(User, user_id)
        if not user or user.role != role or not may_subscribe(user):
            raise PermissionError("GPS access revoked")
        query = select(Vehicle).where(Vehicle.last_gps_at.is_not(None))
        if user.role == UserRole.DISPATCHER:
            query = query.where(Vehicle.depot_id == user.depot_id)
        elif user.role == UserRole.DRIVER:
            query = query.where(Vehicle.current_driver_id == user.driver_id)
        vehicles = (
            await session.scalars(query.order_by(Vehicle.last_gps_at.desc()).limit(100))
        ).all()
        return [
            {
                "vehicle_id": str(v.id),
                "driver_id": str(v.current_driver_id) if v.current_driver_id else None,
                "location": {"latitude": float(v.latitude), "longitude": float(v.longitude)},
                "observed_at": v.last_gps_at.isoformat() + "Z",
                "event_id": str(v.last_gps_event_id) if v.last_gps_event_id else None,
                "source": "postgres",
            }
            for v in vehicles
            if may_view_vehicle(user, v) and v.latitude is not None and v.longitude is not None
        ]


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, client_id: str | None = None):
    """Access JWT must arrive in the first authenticated frame, within 5 s."""
    origin = websocket.headers.get("origin")
    # P1 integration remains local-only; TLS, rate-limited production
    # termination and multi-worker fanout are separate future gates.
    if settings.environment != "development" or origin not in ALLOWED_ORIGINS:
        await websocket.close(code=1008)
        return

    await websocket.accept()
    try:
        raw = await asyncio.wait_for(websocket.receive_text(), timeout=5)
        if len(raw) > 8192:
            raise ValueError("Oversized authentication frame")
        first = json.loads(raw)
        if not isinstance(first, dict) or first.get("action") != "authenticate":
            raise ValueError("Authentication required")
        authenticated = await authenticate_access_token(first.get("token"))
        if authenticated is None:
            raise ValueError("Invalid credentials or missing GPS scope")
        user, expires = authenticated
    except (TimeoutError, WebSocketDisconnect, ValueError, TypeError, json.JSONDecodeError):
        await websocket.close(code=1008)
        return
    except SQLAlchemyError:
        await websocket.close(code=1011)
        return

    await manager.connect(
        websocket,
        client_id,
        user=user,
        expires=expires,
        already_accepted=True,
    )
    await manager.send_personal(
        websocket,
        WebSocketMessage(type="authenticated", data={"channel": "vehicles"}),
    )
    try:
        while True:
            # JWT expiry and revocation are checked on every message AND
            # every outgoing GPS update. An idle socket can be closed by a
            # bounded receive timeout, so it cannot outlive its access token.
            seconds = (expires - datetime.now(UTC)).total_seconds()
            if seconds <= 0:
                await websocket.close(code=1008)
                break
            try:
                raw = await asyncio.wait_for(websocket.receive_text(), timeout=min(30, seconds))
            except TimeoutError:
                continue
            if len(raw) > 4096:
                await websocket.close(code=1009)
                break
            try:
                request = json.loads(raw)
            except json.JSONDecodeError:
                await manager.send_personal(
                    websocket,
                    WebSocketMessage(type="error", data={"message": "Invalid JSON"}),
                )
                continue
            if not isinstance(request, dict):
                continue
            async with AsyncSessionLocal() as session:
                current = await session.get(User, user.id)
                if not manager.is_current_user(current, manager.connection_info.get(websocket)):
                    await manager.revoke(websocket)
                    break
            action = request.get("action")
            channel = request.get("channel")
            if action == "subscribe":
                success = manager.subscribe(websocket, channel)
                await manager.send_personal(
                    websocket,
                    WebSocketMessage(
                        type="subscribed" if success else "error",
                        data={"channel": channel, "success": success},
                    ),
                )
                if success:
                    try:
                        positions = await permitted_snapshot(user.id, user.role)
                    except (PermissionError, SQLAlchemyError):
                        await manager.revoke(websocket)
                        break
                    await manager.send_personal(
                        websocket,
                        WebSocketMessage(
                            type="vehicle_snapshot",
                            data={"vehicles": positions, "limit": 100},
                        ),
                    )
            elif action == "unsubscribe":
                success = manager.unsubscribe(websocket, channel)
                await manager.send_personal(
                    websocket,
                    WebSocketMessage(
                        type="unsubscribed",
                        data={"channel": channel, "success": success},
                    ),
                )
            elif action == "ping":
                await manager.send_personal(
                    websocket,
                    WebSocketMessage(type="pong", data={}),
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
    """Opt-in authenticated internal endpoint, still subject to scope checks."""
    if not BROADCAST_TOKEN or not secrets.compare_digest(x_broadcast_token, BROADCAST_TOKEN):
        raise HTTPException(status_code=401, detail="Unauthorized")
    if channel != "vehicles":
        raise HTTPException(status_code=403, detail="Unsupported location channel")
    if not isinstance(message, dict) or "vehicle_id" not in message:
        raise HTTPException(status_code=422, detail="Missing vehicle ID")
    sent = await manager.broadcast(
        WebSocketMessage(type="vehicle_update", data=message),
        channel=channel,
    )
    return {"status": "sent", "channel": channel, "recipients": sent}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("src.main:app", host="127.0.0.1", port=8000, reload=False)

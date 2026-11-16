"""PostGIS-backed JWT WebSocket authentication, isolation and revocation."""

import json
from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest
from fastapi import WebSocketDisconnect
from starlette.routing import WebSocketRoute

from src.auth.jwt import create_access_token, create_refresh_token, decode_token
from src.main import app
from src.models.user import User, UserRole
from src.websocket_server import (
    WebSocketMessage,
    manager,
    websocket_endpoint,
)


class LocalSocket:
    def __init__(self, frames=(), *, origin="http://localhost:3000"):
        self.headers = {"origin": origin} if origin else {}
        self.frames = list(frames)
        self.sent = []
        self.accepted = False
        self.close_code = None

    async def accept(self):
        self.accepted = True

    async def close(self, code=1000):
        self.close_code = code

    async def send_text(self, text):
        self.sent.append(json.loads(text))

    async def receive_text(self):
        if self.frames:
            return json.dumps(self.frames.pop(0))
        raise WebSocketDisconnect(code=1000)


def auth_frame(token):
    return {"action": "authenticate", "token": token}


async def make_user(session, role, *, driver_id=None, depot_id=None, active=True):
    email = f"socket-{uuid4().hex[:12]}@example.test"
    user = User(
        email=email, role=role, driver_id=driver_id, depot_id=depot_id,
        is_active=active, hashed_password="not-used-by-token-test",
    )
    session.add(user)
    await session.flush()
    token = create_access_token({"sub": email, "role": role.value})
    return user, token


def mock_session(monkeypatch, db_session):
    @asynccontextmanager
    async def factory():
        yield db_session

    monkeypatch.setattr("src.websocket_server.AsyncSessionLocal", factory)


@pytest.mark.asyncio
async def test_driver_snapshot_never_includes_unassigned_vehicle(
    db_session, monkeypatch, sample_depot, sample_driver, sample_vehicle
):
    depot = await sample_depot()
    driver = await sample_driver(depot_id=depot.id)
    other_driver = await sample_driver(depot_id=depot.id)
    mine = await sample_vehicle(depot_id=depot.id, driver_id=driver.id)
    other = await sample_vehicle(depot_id=depot.id, driver_id=other_driver.id)
    for v, lat in ((mine, "55.8700"), (other, "56.3000")):
        v.latitude = Decimal(lat)
        v.longitude = Decimal("-4.2600")
        v.last_gps_at = datetime.now(UTC).replace(tzinfo=None)
        v.last_gps_event_id = uuid4()
    await db_session.flush()
    _, token = await make_user(db_session, UserRole.DRIVER, driver_id=driver.id)
    mock_session(monkeypatch, db_session)
    socket = LocalSocket(
        [auth_frame(token), {"action": "subscribe", "channel": "vehicles"}]
    )
    await websocket_endpoint(socket)
    assert socket.accepted
    assert socket.close_code is None
    assert [message["type"] for message in socket.sent] == [
        "authenticated", "subscribed", "vehicle_snapshot"
    ]
    snapshot = socket.sent[-1]["data"]["vehicles"]
    assert len(snapshot) == 1
    assert snapshot[0]["vehicle_id"] == str(mine.id)
    assert snapshot[0]["location"] == {"latitude": 55.87, "longitude": -4.26}
    assert manager.connection_count == 0


@pytest.mark.asyncio
async def test_dispatcher_depot_snapshot_and_admin_full_fleet(
    db_session, monkeypatch, sample_depot, sample_driver, sample_vehicle
):
    first = await sample_depot()
    second = await sample_depot()
    a = await sample_vehicle(depot_id=first.id)
    b = await sample_vehicle(depot_id=second.id)
    for v in (a, b):
        v.latitude = Decimal("55.87")
        v.longitude = Decimal("-4.26")
        v.last_gps_at = datetime.now(UTC).replace(tzinfo=None)
    await db_session.flush()
    _, scoped = await make_user(db_session, UserRole.DISPATCHER, depot_id=first.id)
    _, admin = await make_user(db_session, UserRole.ADMIN)
    mock_session(monkeypatch, db_session)
    for token, expected in (
        (scoped, {str(a.id)}),
        (admin, {str(a.id), str(b.id)}),
    ):
        socket = LocalSocket(
            [auth_frame(token), {"action": "subscribe", "channel": "vehicles"}]
        )
        await websocket_endpoint(socket)
        observed = {v["vehicle_id"] for v in socket.sent[-1]["data"]["vehicles"]}
        assert observed == expected


@pytest.mark.asyncio
async def test_invalid_tokens_roles_and_missing_scopes_fail_closed(
    db_session, monkeypatch
):
    mock_session(monkeypatch, db_session)
    viewer, viewer_token = await make_user(db_session, UserRole.VIEWER)
    dispatcher, dispatcher_token = await make_user(db_session, UserRole.DISPATCHER)
    _, unlinked_driver = await make_user(db_session, UserRole.DRIVER)
    _, disabled = await make_user(db_session, UserRole.ADMIN, active=False)
    _, admin_token = await make_user(db_session, UserRole.ADMIN)
    refresh = create_refresh_token({"sub": viewer.email, "role": viewer.role.value})
    assert decode_token(refresh) is None
    assert decode_token(refresh, expected_type="refresh") is not None
    expired = create_access_token(
        {"sub": dispatcher.email, "role": dispatcher.role.value},
        expires_delta=timedelta(seconds=-5),
    )

    for frame in (
        {"action": "subscribe", "channel": "vehicles"},
        auth_frame("bad-token"),
        auth_frame(refresh),
        auth_frame(expired),
        auth_frame(viewer_token),
        auth_frame(dispatcher_token),
        auth_frame(unlinked_driver),
        auth_frame(disabled),
    ):
        socket = LocalSocket([frame, {"action": "subscribe", "channel": "vehicles"}])
        await websocket_endpoint(socket)
        assert socket.accepted
        assert socket.close_code == 1008
        assert not socket.sent
        assert manager.connection_count == 0

    # An authenticated admin still cannot subscribe to broad/other channels.
    socket = LocalSocket(
        [auth_frame(admin_token), {"action": "subscribe", "channel": "all"}]
    )
    await websocket_endpoint(socket)
    assert [v["type"] for v in socket.sent] == ["authenticated", "error"]
    assert not manager.channel_subscriptions["vehicles"]


@pytest.mark.asyncio
async def test_outgoing_gps_is_scoped_and_revoked_accounts_are_closed(
    db_session, monkeypatch, sample_depot, sample_driver, sample_vehicle
):
    d1 = await sample_depot()
    d2 = await sample_depot()
    driver = await sample_driver(depot_id=d1.id)
    vehicle = await sample_vehicle(depot_id=d1.id, driver_id=driver.id)
    another = await sample_vehicle(depot_id=d2.id)
    user_driver, _ = await make_user(db_session, UserRole.DRIVER, driver_id=driver.id)
    user_dispatcher, _ = await make_user(db_session, UserRole.DISPATCHER, depot_id=d2.id)
    user_admin, _ = await make_user(db_session, UserRole.ADMIN)
    mock_session(monkeypatch, db_session)
    expires = datetime.now(UTC) + timedelta(minutes=10)
    sockets = {}
    try:
        for key, user in (
            ("driver", user_driver),
            ("other_depot", user_dispatcher),
            ("admin", user_admin),
        ):
            socket = LocalSocket()
            await manager.connect(socket, user=user, expires=expires)
            assert manager.subscribe(socket, "vehicles")
            sockets[key] = socket

        message = WebSocketMessage(
            type="vehicle_update",
            data={
                "vehicle_id": str(vehicle.id),
                "location": {"latitude": 55.87, "longitude": -4.26},
            },
        )
        assert await manager.broadcast(message, channel="vehicles") == 2
        assert len(sockets["driver"].sent) == 1
        assert len(sockets["admin"].sent) == 1
        assert not sockets["other_depot"].sent

        # A revoked live identity is removed before the next GPS packet.
        user_driver.is_active = False
        await db_session.flush()
        assert await manager.broadcast(message, channel="vehicles") == 1
        assert sockets["driver"].close_code == 1008
        assert len(sockets["driver"].sent) == 1

        # Reassignment to an unauthorized depot must not leak either.
        vehicle.depot_id = d2.id
        vehicle.current_driver_id = None
        await db_session.flush()
        assert await manager.broadcast(message, channel="vehicles") == 1
        assert len(sockets["other_depot"].sent) == 0
        assert len(sockets["admin"].sent) == 3
        # The dispatcher was scoped to d2 but cannot see any *previous*
        # location update. A future GPS broadcast will use current vehicle
        # assignment; the depot scope itself has not been revoked.
    finally:
        for socket in sockets.values():
            manager.disconnect(socket)
    assert manager.connection_count == 0


@pytest.mark.asyncio
async def test_origin_rejection_happens_before_authentication():
    socket = LocalSocket(origin="https://untrusted.example")
    await websocket_endpoint(socket)
    assert socket.close_code == 1008
    assert not socket.accepted
    assert socket.sent == []


def test_websocket_route_is_mounted_on_actual_api_process():
    assert any(
        isinstance(route, WebSocketRoute) and route.path == "/ws"
        for route in app.routes
    )

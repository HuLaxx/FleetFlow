"""Live local GPS WebSocket: shared FastAPI route and PostGIS snapshots."""

import json
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

import pytest
from fastapi import WebSocketDisconnect
from starlette.routing import WebSocketRoute

from src.main import app
from src.websocket_server import manager, websocket_endpoint


class LocalSocket:
    def __init__(self, *, origin="http://localhost:3000"):
        self.headers = {"origin": origin} if origin else {}
        self.sent = []
        self.accepted = False
        self.close_code = None
        self.received = 0

    async def accept(self):
        self.accepted = True

    async def close(self, code=1000):
        self.close_code = code

    async def send_text(self, text):
        self.sent.append(json.loads(text))

    async def receive_text(self):
        self.received += 1
        if self.received == 1:
            return json.dumps({"action": "subscribe", "channel": "vehicles"})
        raise WebSocketDisconnect(code=1000)


@pytest.mark.asyncio
async def test_snapshot_contains_only_real_persisted_gps_positions(
    db_session, sample_depot, sample_driver, sample_vehicle, monkeypatch
):
    depot = await sample_depot()
    driver = await sample_driver(depot_id=depot.id)
    vehicle = await sample_vehicle(depot_id=depot.id, driver_id=driver.id)
    vehicle.latitude = Decimal("55.8700")
    vehicle.longitude = Decimal("-4.2600")
    vehicle.last_gps_at = datetime.now(UTC).replace(tzinfo=None)
    vehicle.last_gps_event_id = uuid4()
    await db_session.flush()

    @asynccontextmanager
    async def context():
        yield db_session

    monkeypatch.setattr("src.websocket_server.AsyncSessionLocal", context)
    socket = LocalSocket()
    await websocket_endpoint(socket, client_id="test-local")
    assert socket.accepted
    assert socket.close_code is None
    assert [message["type"] for message in socket.sent] == [
        "connected", "subscribed", "vehicle_snapshot"
    ]
    snapshot = socket.sent[-1]["data"]["vehicles"]
    assert len(snapshot) == 1
    assert snapshot[0]["vehicle_id"] == str(vehicle.id)
    assert snapshot[0]["location"] == {"latitude": 55.87, "longitude": -4.26}
    assert snapshot[0]["source"] == "postgres"
    assert manager.connection_count == 0


@pytest.mark.asyncio
async def test_untrusted_origin_never_connects_to_location_stream():
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

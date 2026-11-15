"""PostGIS-backed GPS intake, freshness and Kafka-to-WS broadcast contract.

This test exercises the production ORM and GPS handler. Kafka delivery is
separately covered by the real-broker workflow; browser socket tests are
separate because a DB commit cannot make external broadcasts exactly-once.
"""

from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from sqlalchemy import func, select

from src.consumers.gps_consumer import GPSLocationConsumer
from src.models import DispatchOutboxEvent, Vehicle
from src.models.user import UserRole
from tests.test_api.test_dispatch_approval import token_for


@pytest.mark.asyncio
async def test_gps_submission_authenticates_driver_and_queues_outbox(
    client, db_session, sample_depot, sample_driver, sample_vehicle
):
    depot = await sample_depot()
    driver = await sample_driver(depot_id=depot.id)
    vehicle = await sample_vehicle(depot_id=depot.id, driver_id=driver.id)
    path = f"/api/v1/drivers/{driver.id}/location"
    payload = {"latitude": 55.87, "longitude": -4.26, "speed_kmh": 22}

    anonymous = await client.post(path, json=payload)
    assert anonymous.status_code == 401

    viewer = await client.post(
        path, json=payload, headers=await token_for(db_session, UserRole.VIEWER)
    )
    assert viewer.status_code == 403

    another_driver = await client.post(
        path,
        json=payload,
        headers=await token_for(db_session, UserRole.DRIVER, driver_id=uuid4()),
    )
    assert another_driver.status_code == 403

    valid = await client.post(
        path,
        json=payload,
        headers=await token_for(db_session, UserRole.DRIVER, driver_id=driver.id),
    )
    assert valid.status_code == 202, valid.text
    assert valid.json()["status"] == "queued"
    assert valid.json()["delivery_status"] == "pending"
    assert vehicle.latitude is None
    assert vehicle.last_gps_at is None
    queued = await db_session.scalar(
        select(DispatchOutboxEvent).where(
            DispatchOutboxEvent.id == valid.json()["event_id"]
        )
    )
    assert queued is not None
    assert queued.topic == "gps.location"
    assert queued.payload["vehicle_id"] == str(vehicle.id)
    assert queued.payload["schema_version"] == 1
    assert queued.payload["event_id"] == str(queued.id)


@pytest.mark.asyncio
async def test_gps_commit_precedes_broadcast_and_old_events_cannot_rollback_position(
    db_session, sample_depot, sample_driver, sample_vehicle, monkeypatch
):
    depot = await sample_depot()
    driver = await sample_driver(depot_id=depot.id)
    vehicle = await sample_vehicle(depot_id=depot.id, driver_id=driver.id)

    @asynccontextmanager
    async def session_factory():
        yield db_session

    monkeypatch.setattr("src.consumers.gps_consumer.AsyncSessionLocal", session_factory)
    websocket = AsyncMock()
    websocket.broadcast.return_value = 1
    consumer = GPSLocationConsumer()
    consumer.set_websocket_manager(websocket)

    now = datetime.now(UTC).replace(microsecond=0)
    event = {
        "event_id": str(uuid4()),
        "schema_version": 1,
        "driver_id": str(driver.id),
        "vehicle_id": str(vehicle.id),
        "location": {"latitude": 55.8752, "longitude": -4.2581},
        "timestamp": now.isoformat(),
        "speed_kmh": 15.5,
    }

    await consumer.handle_message("gps.location", str(vehicle.id), event, 0)
    assert vehicle.latitude == Decimal("55.8752")
    assert vehicle.longitude == Decimal("-4.2581")
    assert vehicle.last_gps_event_id == event["event_id"]
    assert vehicle.last_gps_at == now.replace(tzinfo=None)
    assert websocket.broadcast.await_count == 1
    message = websocket.broadcast.await_args.args[0]
    assert message.type == "vehicle_update"
    assert message.data["location"]["latitude"] == 55.8752
    assert message.data["source"] == "kafka"

    # Neither the same packet nor an older packet may move the marker back.
    await consumer.handle_message("gps.location", str(vehicle.id), event, 0)
    older = {
        **event,
        "event_id": str(uuid4()),
        "timestamp": (now - timedelta(minutes=2)).isoformat(),
        "location": {"latitude": 45.0, "longitude": 12.0},
    }
    await consumer.handle_message("gps.location", str(vehicle.id), older, 0)
    assert vehicle.latitude == Decimal("55.8752")
    assert websocket.broadcast.await_count == 1

    newer = {
        **event,
        "event_id": str(uuid4()),
        "timestamp": (now + timedelta(seconds=1)).isoformat(),
        "location": {"latitude": 55.8759, "longitude": -4.2518},
    }
    await consumer.handle_message("gps.location", str(vehicle.id), newer, 0)
    assert vehicle.latitude == Decimal("55.8759")
    assert websocket.broadcast.await_count == 2

    wrong_driver = {**newer, "event_id": str(uuid4()), "driver_id": str(uuid4())}
    with pytest.raises(ValueError, match="not assigned"):
        await consumer.handle_message("gps.location", None, wrong_driver, 0)
    assert websocket.broadcast.await_count == 2


@pytest.mark.asyncio
async def test_invalid_gps_contract_never_mutates_saved_coordinates(
    db_session, sample_depot, sample_driver, sample_vehicle, monkeypatch
):
    depot = await sample_depot()
    driver = await sample_driver(depot_id=depot.id)
    vehicle = await sample_vehicle(depot_id=depot.id, driver_id=driver.id)

    @asynccontextmanager
    async def session_factory():
        yield db_session

    monkeypatch.setattr("src.consumers.gps_consumer.AsyncSessionLocal", session_factory)
    consumer = GPSLocationConsumer()
    bad = {
        "event_id": str(uuid4()),
        "schema_version": 1,
        "driver_id": str(driver.id),
        "vehicle_id": str(vehicle.id),
        "location": {"latitude": 91.0, "longitude": -4.2581},
        "timestamp": datetime.now(UTC).isoformat(),
    }
    with pytest.raises(ValueError, match="Invalid GPS event"):
        await consumer.handle_message("gps.location", None, bad, 0)
    assert vehicle.latitude is None
    assert vehicle.last_gps_at is None

    unversioned = {**bad, "location": {"latitude": 55.0, "longitude": -4.0}}
    del unversioned["event_id"]
    with pytest.raises(ValueError, match="schema_version"):
        await consumer.handle_message("gps.location", None, unversioned, 0)

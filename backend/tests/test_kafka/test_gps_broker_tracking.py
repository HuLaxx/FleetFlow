"""Real Redpanda -> GPS consumer -> PostGIS -> WebSocket manager acceptance.

Uses a disposable broker and fleetflow_test. Browser acceptance is a
separate Playwright check; no deployed/public WebSocket is claimed here.
"""

import asyncio
import os
from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from aiokafka import AIOKafkaConsumer
from geoalchemy2.elements import WKTElement
from sqlalchemy.ext.asyncio import async_sessionmaker

from src.consumers.gps_consumer import GPSLocationConsumer
from src.events.models import GPSLocationEvent, Location
from src.events.producer import KafkaProducerService
from src.models import Depot, DispatchOutboxEvent, Driver, Vehicle
from src.reliability.dispatch import dispatch_outbox_batch

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        os.getenv("FLEETFLOW_KAFKA_INTEGRATION") != "1",
        reason="Needs a real disposable Kafka-compatible broker",
    ),
]


@pytest.mark.asyncio
async def test_real_gps_outbox_event_updates_db_and_websocket_once(integration_engine):
    sessions = async_sessionmaker(integration_engine, expire_on_commit=False)
    suffix = uuid4().hex
    producer = KafkaProducerService()
    await producer.ensure_topics_exist()

    async with sessions() as session:
        depot = Depot(
            name=f"GPS Depot {suffix}",
            address="Local test depot",
            latitude=Decimal("55.8642"),
            longitude=Decimal("-4.2518"),
            location=WKTElement("POINT(-4.2518 55.8642)", srid=4326),
        )
        session.add(depot)
        await session.flush()
        driver = Driver(
            employee_id=f"GPS-{suffix[:10]}",
            first_name="GPS",
            last_name="Runner",
            email=f"gps-{suffix}@example.test",
            status="available",
        )
        session.add(driver)
        await session.flush()
        vehicle = Vehicle(
            vehicle_number=f"GPS-{suffix[:10]}",
            type="van",
            capacity_kg=Decimal("25"),
            depot_id=depot.id,
            current_driver_id=driver.id,
            status="available",
        )
        session.add(vehicle)
        await session.flush()
        event = GPSLocationEvent(
            driver_id=driver.id,
            vehicle_id=vehicle.id,
            location=Location(latitude=55.8743, longitude=-4.2571),
            speed_kmh=25,
            timestamp=datetime.now(UTC),
        )
        session.add(
            DispatchOutboxEvent(
                id=event.event_id,
                topic="gps.location",
                message_key=str(vehicle.id),
                payload=event.model_dump(mode="json"),
                status="pending",
                next_attempt_at=event.timestamp,
            )
        )
        await session.commit()

    try:
        async with sessions() as session:
            sent = await dispatch_outbox_batch(session, producer.publish_confirmed_async)
            assert sent["published"] == 1
        group = f"fleetflow-gps-test-{suffix}"
        async def new_consumer():
            client = AIOKafkaConsumer(
                "gps.location",
                bootstrap_servers=os.environ["KAFKA_BOOTSTRAP_SERVERS"],
                group_id=group,
                auto_offset_reset="earliest",
                enable_auto_commit=False,
                value_deserializer=None,
            )
            await client.start()
            return client

        handler = GPSLocationConsumer()
        socket_manager = AsyncMock()
        socket_manager.broadcast.return_value = 1
        handler.set_websocket_manager(socket_manager)

        consumer_client = await new_consumer()
        try:
            first = await asyncio.wait_for(consumer_client.getone(), timeout=25)
            await handler._process_message(first)
            # Do not commit the Kafka offset; restart must redeliver.
        finally:
            await consumer_client.stop()

        consumer_client = await new_consumer()
        try:
            duplicate = await asyncio.wait_for(consumer_client.getone(), timeout=25)
            assert duplicate.value == first.value
            await handler._process_message(duplicate)
            await consumer_client.commit()
        finally:
            await consumer_client.stop()

        async with sessions() as session:
            saved = await session.get(Vehicle, vehicle.id)
            assert saved is not None
            assert saved.latitude == Decimal("55.8743000")
            assert saved.longitude == Decimal("-4.2571000")
            assert saved.last_gps_event_id == event.event_id
            assert saved.last_gps_at is not None
        assert socket_manager.broadcast.await_count == 1
        envelope = socket_manager.broadcast.await_args.args[0]
        assert envelope.type == "vehicle_update"
        assert envelope.data["event_id"] == str(event.event_id)
        assert envelope.data["location"] == {
            "latitude": 55.8743,
            "longitude": -4.2571,
        }
    finally:
        producer.close()

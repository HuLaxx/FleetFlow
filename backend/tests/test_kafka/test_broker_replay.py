"""Real-broker acceptance: outbox ACK, consumer restart, dedup and quarantine.

This test is opt-in and must run on an isolated local PostGIS test database
with a real disposable Kafka-compatible broker. It MUST NOT silently mock Kafka.
"""

import asyncio
import hashlib
import os
from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import uuid4

import pytest
from aiokafka import AIOKafkaConsumer, AIOKafkaProducer
from geoalchemy2.elements import WKTElement
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker

from src.consumers.route_consumer import RouteEventsConsumer
from src.events.producer import KafkaProducerService
from src.models import (
    Depot,
    DispatchConsumerInbox,
    DispatchOutboxEvent,
    DispatchQuarantineEvent,
    Driver,
    Route,
    RouteApprovalAudit,
    Vehicle,
)
from src.reliability.dispatch import dispatch_outbox_batch

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        os.getenv("FLEETFLOW_KAFKA_INTEGRATION") != "1",
        reason="Real broker required: run the dedicated kafka-integration CI job",
    ),
]


@pytest.mark.asyncio
async def test_real_broker_outbox_restart_replay_and_poison_quarantine(integration_engine):
    broker_url = os.environ["KAFKA_BOOTSTRAP_SERVERS"]
    session_factory = async_sessionmaker(integration_engine, expire_on_commit=False)
    unique = uuid4().hex
    event_id, actor_id = uuid4(), uuid4()
    key = f"route-{unique}"
    group = f"fleetflow-acceptance-{unique}"
    route = None
    depot = None
    vehicle = None
    driver = None
    quarantined_offset = None
    quarantined_partition = None

    producer = KafkaProducerService()
    await producer.ensure_topics_exist()
    try:
        # Committed PostgreSQL facts are visible to independent consumer sessions.
        async with session_factory() as session:
            depot = Depot(
                name=f"Accept Depot {unique}",
                address="Local test depot",
                latitude=Decimal("55.8642"),
                longitude=Decimal("-4.2518"),
                location=WKTElement("POINT(-4.2518 55.8642)", srid=4326),
            )
            session.add(depot)
            await session.flush()
            driver = Driver(
                employee_id=f"ACPT-{unique[:10]}",
                first_name="Local",
                last_name="Runner",
                email=f"accept-{unique}@example.test",
                status="available",
            )
            session.add(driver)
            await session.flush()
            vehicle = Vehicle(
                vehicle_number=f"ACPT-{unique[:10]}",
                type="van",
                capacity_kg=Decimal("50"),
                depot_id=depot.id,
                current_driver_id=driver.id,
                status="available",
            )
            session.add(vehicle)
            await session.flush()
            route = Route(
                route_date=date(2030, 1, 15),
                depot_id=depot.id,
                vehicle_id=vehicle.id,
                driver_id=driver.id,
                planned_stops=0,
                status="approved",
            )
            session.add(route)
            await session.flush()
            timestamp = datetime.now(UTC)
            payload = {
                "event_id": str(event_id),
                "schema_version": 1,
                "event_type": "route.approved",
                "route_id": str(route.id),
                "driver_id": str(driver.id),
                "vehicle_id": str(vehicle.id),
                "approved_by_user_id": str(actor_id),
                "timestamp": timestamp.isoformat(),
            }
            session.add(
                RouteApprovalAudit(
                    route_id=route.id,
                    approved_by_user_id=actor_id,
                    event_id=event_id,
                    previous_status="planned",
                    new_status="approved",
                    approved_at=timestamp,
                )
            )
            session.add(
                DispatchOutboxEvent(
                    id=event_id,
                    topic="routes.approved",
                    message_key=key,
                    payload=payload,
                    status="pending",
                    next_attempt_at=timestamp,
                )
            )
            await session.commit()

        async with session_factory() as session:
            result = await dispatch_outbox_batch(session, producer.publish_confirmed_async)
            assert result == {"selected": 1, "published": 1, "failed": 0}

        async def new_consumer():
            client = AIOKafkaConsumer(
                "routes.approved",
                bootstrap_servers=broker_url,
                group_id=group,
                auto_offset_reset="earliest",
                enable_auto_commit=False,
                value_deserializer=None,
            )
            await client.start()
            return client

        handler = RouteEventsConsumer()
        client = await new_consumer()
        try:
            first = await asyncio.wait_for(client.getone(), timeout=25)
            assert first.value is not None
            await handler._process_message(first)
            # Simulate a process dying before broker offset commit.
        finally:
            await client.stop()

        # Simulate worker ACK-before-DB-commit crash window: replay same event_id.
        async with session_factory() as session:
            outbox = await session.get(DispatchOutboxEvent, event_id)
            outbox.status = "pending"
            outbox.next_attempt_at = datetime.now(UTC)
            await session.commit()
        async with session_factory() as session:
            replayed = await dispatch_outbox_batch(
                session, producer.publish_confirmed_async
            )
            assert replayed == {"selected": 1, "published": 1, "failed": 0}

        restarted = await new_consumer()
        try:
            redelivered = await asyncio.wait_for(restarted.getone(), timeout=25)
            assert redelivered.value == first.value
            await handler._process_message(redelivered)
            await restarted.commit()

            duplicate = await asyncio.wait_for(restarted.getone(), timeout=25)
            assert duplicate.value == first.value
            await handler._process_message(duplicate)
            await restarted.commit()

            # A malformed message enters the durable DB quarantine before ACK.
            raw = b"{invalid-kafka-json-with-no-customer-details"
            raw_producer = AIOKafkaProducer(bootstrap_servers=broker_url)
            await raw_producer.start()
            try:
                await raw_producer.send_and_wait("routes.approved", raw, key=key.encode())
            finally:
                await raw_producer.stop()
            poisoned = await asyncio.wait_for(restarted.getone(), timeout=25)
            assert poisoned.value == raw
            await handler._process_message(poisoned)
            await restarted.commit()
            quarantined_offset, quarantined_partition = (
                poisoned.offset,
                poisoned.partition,
            )
            # A repeated delivery of the same Kafka offset must not create another row.
            await handler._process_message(poisoned)
        finally:
            await restarted.stop()

        async with session_factory() as session:
            receipts = await session.scalar(
                select(func.count(DispatchConsumerInbox.event_id)).where(
                    DispatchConsumerInbox.event_id == event_id
                )
            )
            assert receipts == 1
            quarantined = await session.scalar(
                select(DispatchQuarantineEvent).where(
                    DispatchQuarantineEvent.topic == "routes.approved",
                    DispatchQuarantineEvent.partition == quarantined_partition,
                    DispatchQuarantineEvent.offset == quarantined_offset,
                )
            )
            assert quarantined is not None
            assert quarantined.reason == "invalid_json"
            assert quarantined.payload_sha256 == hashlib.sha256(raw).hexdigest()
            assert quarantined.payload_bytes == len(raw)
            quarantine_count = await session.scalar(
                select(func.count(DispatchQuarantineEvent.id)).where(
                    DispatchQuarantineEvent.topic == "routes.approved",
                    DispatchQuarantineEvent.partition == quarantined_partition,
                    DispatchQuarantineEvent.offset == quarantined_offset,
                )
            )
            assert quarantine_count == 1
            outbox = await session.get(DispatchOutboxEvent, event_id)
            assert outbox.status == "published"
            assert outbox.attempts == 2
    finally:
        # This is a disposable PostGIS CI database. Approval audit rows are
        # immutable by SQL trigger, so cleanup must not delete or rewrite them.
        producer.close()

"""Failure semantics for raw Kafka bytes and durable poison-message handling."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.consumers.base import BaseKafkaConsumer, PermanentEventError


class QuarantineConsumer(BaseKafkaConsumer):
    def __init__(self, *, quarantine_fails=False):
        super().__init__(topics=["routes.approved"], group_id="quarantine-test")
        self.quarantined = []
        self.events = []
        self.quarantine_fails = quarantine_fails

    async def handle_message(self, topic, key, value, timestamp):
        self.events.append(value)
        if value.get("schema_version") != 1:
            raise PermanentEventError("unsupported_schema")

    async def quarantine_message(self, message, *, reason):
        if self.quarantine_fails:
            raise OSError("Simulated database transaction failure")
        self.quarantined.append((message.topic, message.offset, reason))


def broker_with_messages(*messages):
    broker = MagicMock()
    broker.start = AsyncMock()
    broker.stop = AsyncMock()
    broker.commit = AsyncMock()

    async def items():
        for message in messages:
            yield message

    broker.__aiter__.side_effect = items
    return broker


def message(payload, offset):
    return SimpleNamespace(
        topic="routes.approved",
        partition=1,
        offset=offset,
        key=b"route",
        value=payload,
        timestamp=1763145000000,
    )


@pytest.mark.asyncio
async def test_malformed_json_is_quarantined_before_offset_commit():
    malformed = message(b"{ definitely not JSON", 20)
    good = message(b'{"schema_version": 1, "event_id": "accepted"}', 21)
    broker = broker_with_messages(malformed, good)
    consumer = QuarantineConsumer()
    consumer._running = True
    with patch("src.consumers.base.AIOKafkaConsumer", return_value=broker) as create:
        await consumer._consume_loop()

    assert create.call_args.kwargs["value_deserializer"] is None
    assert create.call_args.kwargs["enable_auto_commit"] is False
    assert consumer.quarantined == [("routes.approved", 20, "invalid_json")]
    assert consumer.events == [{"schema_version": 1, "event_id": "accepted"}]
    assert broker.commit.await_count == 2


@pytest.mark.asyncio
async def test_permanent_schema_failure_is_quarantined_then_committed():
    invalid = message(b'{"schema_version": 99}', 40)
    broker = broker_with_messages(invalid)
    consumer = QuarantineConsumer()
    consumer._running = True
    with patch("src.consumers.base.AIOKafkaConsumer", return_value=broker):
        await consumer._consume_loop()
    assert consumer.quarantined == [("routes.approved", 40, "unsupported_schema")]
    broker.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_quarantine_failure_prevents_commit_and_restart_can_retry():
    malformed = message(b"{ broken", 9)
    broker = broker_with_messages(malformed)
    consumer = QuarantineConsumer(quarantine_fails=True)
    consumer._running = True
    with patch("src.consumers.base.AIOKafkaConsumer", return_value=broker):
        with pytest.raises(OSError, match="Simulated database"):
            await consumer._consume_loop()
    broker.commit.assert_not_awaited()
    broker.stop.assert_awaited_once()


@pytest.mark.asyncio
async def test_unprotected_consumer_fails_closed_on_invalid_payload():
    class NoQuarantine(BaseKafkaConsumer):
        async def handle_message(self, topic, key, value, timestamp):
            raise AssertionError("Should not invoke handler")

    broker = broker_with_messages(message(b"not json", 1))
    consumer = NoQuarantine(topics=["orders.created"])
    consumer._running = True
    with patch("src.consumers.base.AIOKafkaConsumer", return_value=broker):
        with pytest.raises(RuntimeError, match="no durable quarantine"):
            await consumer._consume_loop()
    broker.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_large_message_is_quarantined_without_parsing():
    payload = b"x" * 131073
    broker = broker_with_messages(message(payload, 88))
    consumer = QuarantineConsumer()
    consumer._running = True
    with patch("src.consumers.base.AIOKafkaConsumer", return_value=broker):
        await consumer._consume_loop()
    assert consumer.quarantined == [("routes.approved", 88, "payload_too_large")]
    broker.commit.assert_awaited_once()

"""Manual Kafka offset semantics, without connecting to an external broker."""
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.consumers.base import BaseKafkaConsumer


class RecordingConsumer(BaseKafkaConsumer):
    def __init__(self, fail=False):
        super().__init__(topics=["test.events"], group_id="test-offsets")
        self.fail = fail
        self.calls = []

    async def handle_message(self, topic, key, value, timestamp):
        self.calls.append((topic, key, value, timestamp))
        if self.fail:
            raise ValueError("simulated invalid message")


def fake_broker(message):
    broker = MagicMock()
    broker.start = AsyncMock()
    broker.stop = AsyncMock()
    broker.commit = AsyncMock()

    async def receive():
        yield message

    broker.__aiter__.side_effect = receive
    return broker


@pytest.mark.asyncio
async def test_successful_handler_commits_offset_after_processing():
    event = SimpleNamespace(
        topic="test.events", partition=0, offset=5,
        key=b"entity-1", value={"event_id": "example", "schema_version": 1},
        timestamp=1730000000000,
    )
    broker = fake_broker(event)
    consumer = RecordingConsumer()
    consumer._running = True
    with patch("src.consumers.base.AIOKafkaConsumer", return_value=broker) as build:
        await consumer._consume_loop()

    assert consumer.calls == [("test.events", "entity-1", event.value, event.timestamp)]
    assert build.call_args.kwargs["enable_auto_commit"] is False
    broker.commit.assert_awaited_once()
    broker.stop.assert_awaited_once()


@pytest.mark.asyncio
async def test_failing_handler_never_commits_and_propagates_error():
    event = SimpleNamespace(
        topic="test.events", partition=0, offset=8,
        key=None, value={"bad": "payload"}, timestamp=1730000000000,
    )
    broker = fake_broker(event)
    consumer = RecordingConsumer(fail=True)
    consumer._running = True
    with patch("src.consumers.base.AIOKafkaConsumer", return_value=broker):
        with pytest.raises(ValueError, match="simulated invalid message"):
            await consumer._consume_loop()

    assert len(consumer.calls) == 1
    broker.commit.assert_not_awaited()
    broker.stop.assert_awaited_once()

"""Producer ACK contract: an enqueue is not a confirmed broker delivery."""

import pytest

from src.events.producer import KafkaProducerService


class StubMessage:
    def topic(self):
        return "routes.approved"

    def partition(self):
        return 0

    def offset(self):
        return 10


class StubProducer:
    def __init__(self, error=None, *, never_ack=False):
        self.error = error
        self.never_ack = never_ack
        self.callback = None
        self.produced = []

    def produce(self, *, topic, key, value, callback):
        self.produced.append((topic, key, value))
        self.callback = callback

    def poll(self, timeout):
        if not self.never_ack and self.callback is not None:
            callback = self.callback
            self.callback = None
            callback(self.error, StubMessage())


def test_confirmed_publish_waits_for_success_callback(monkeypatch):
    publisher = KafkaProducerService()
    broker = StubProducer()
    monkeypatch.setattr(publisher, "_get_producer", lambda: broker)
    publisher.publish_confirmed("routes.approved", {"event_id": "sample"}, "route-a")
    assert len(broker.produced) == 1
    assert broker.produced[0][1] == b"route-a"
    assert publisher.stats["delivered"] == 1


def test_broker_negative_ack_is_an_error(monkeypatch):
    publisher = KafkaProducerService()
    broker = StubProducer(error=RuntimeError("Simulated broker rejection"))
    monkeypatch.setattr(publisher, "_get_producer", lambda: broker)
    with pytest.raises(RuntimeError, match="Broker rejected"):
        publisher.publish_confirmed("routes.approved", {}, "route-a")
    assert publisher.stats["errors"] == 1


def test_unacknowledged_send_times_out_instead_of_marking_delivered(monkeypatch):
    publisher = KafkaProducerService()
    broker = StubProducer(never_ack=True)
    monkeypatch.setattr(publisher, "_get_producer", lambda: broker)
    with pytest.raises(TimeoutError):
        publisher.publish_confirmed("routes.approved", {}, "route-a", timeout=0.01)
    assert publisher.stats["delivered"] == 0

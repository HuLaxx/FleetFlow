"""Kafka producer for publishing events."""

import asyncio
import json
import time
from datetime import datetime
from typing import Any, ClassVar
from uuid import UUID

import structlog
from confluent_kafka import KafkaException, Producer
from confluent_kafka.admin import AdminClient, NewTopic

from src.config import get_settings

logger = structlog.get_logger()


class KafkaEncoder(json.JSONEncoder):
    """Custom JSON encoder for Kafka messages."""

    def default(self, obj: Any) -> Any:
        if isinstance(obj, UUID):
            return str(obj)
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)


class KafkaProducerService:
    """
    Kafka producer service for publishing events to topics.

    Topics:
    - orders.created
    - orders.cancelled
    - orders.assigned
    - orders.delivered
    - gps.location
    - drivers.status
    - routes.created
    - routes.started
    - routes.stops
    - traffic.updates
    """

    TOPICS: ClassVar[list[str]] = [
        "orders.created",
        "orders.cancelled",
        "orders.assigned",
        "orders.delivered",
        "gps.location",
        "drivers.status",
        "routes.created",
        "routes.started",
        "routes.approved",
        "routes.stops",
        "traffic.updates",
        "alerts.driver_late",
        "alerts.hotspot",
    ]

    def __init__(self):
        settings = get_settings()
        self.bootstrap_servers = settings.kafka_bootstrap_servers
        self._producer: Producer | None = None
        self._delivery_count = 0
        self._error_count = 0

    def _get_producer(self) -> Producer:
        """Lazy initialization of producer."""
        if self._producer is None:
            self._producer = Producer(
                {
                    "bootstrap.servers": self.bootstrap_servers,
                    "client.id": "fleetflow-producer",
                    "acks": "all",
                    "enable.idempotence": True,
                    "max.in.flight.requests.per.connection": 5,
                    "retries": 3,
                    "retry.backoff.ms": 100,
                    "compression.type": "snappy",
                }
            )
        return self._producer

    def _delivery_callback(self, err: Any, msg: Any) -> None:
        """Callback for message delivery confirmation."""
        if err:
            self._error_count += 1
            logger.error("Message delivery failed", error=str(err), topic=msg.topic())
        else:
            self._delivery_count += 1
            logger.debug(
                "Message delivered",
                topic=msg.topic(),
                partition=msg.partition(),
                offset=msg.offset(),
            )

    async def ensure_topics_exist(self) -> None:
        """Create topics if they don't exist."""
        try:
            admin = AdminClient({"bootstrap.servers": self.bootstrap_servers})

            # Get existing topics
            metadata = admin.list_topics(timeout=10)
            existing_topics = set(metadata.topics.keys())

            # Create missing topics
            topics_to_create = [
                NewTopic(
                    topic,
                    num_partitions=3,
                    replication_factor=1,
                    config={
                        "retention.ms": str(7 * 24 * 60 * 60 * 1000),  # 7 days
                        "cleanup.policy": "delete",
                    },
                )
                for topic in self.TOPICS
                if topic not in existing_topics
            ]

            if topics_to_create:
                futures = admin.create_topics(topics_to_create)
                for topic, future in futures.items():
                    try:
                        future.result()
                        logger.info("Created Kafka topic", topic=topic)
                    except (KafkaException, TimeoutError, RuntimeError, OSError) as e:
                        if "TOPIC_ALREADY_EXISTS" not in str(e):
                            logger.warning("Failed to create topic", topic=topic, error=str(e))
        except (KafkaException, TimeoutError, RuntimeError, OSError) as e:
            logger.error("Failed to ensure topics exist", error=str(e))

    def publish(
        self, topic: str, event: Any, key: str | None = None, headers: dict | None = None
    ) -> None:
        """
        Publish an event to a Kafka topic.

        Args:
            topic: Kafka topic name
            event: Pydantic model to serialize
            key: Optional partition key
            headers: Optional message headers
        """
        producer = self._get_producer()

        # Serialize event
        if hasattr(event, "model_dump"):
            value = json.dumps(event.model_dump(), cls=KafkaEncoder).encode("utf-8")
        else:
            value = json.dumps(event, cls=KafkaEncoder).encode("utf-8")

        # Prepare headers
        kafka_headers = None
        if headers:
            kafka_headers = [
                (k, v.encode("utf-8") if isinstance(v, str) else v) for k, v in headers.items()
            ]

        try:
            producer.produce(
                topic=topic,
                key=key.encode("utf-8") if key else None,
                value=value,
                headers=kafka_headers,
                callback=self._delivery_callback,
            )
            producer.poll(0)  # Trigger callbacks
        except (KafkaException, TimeoutError, RuntimeError, OSError) as e:
            logger.error("Failed to publish event", topic=topic, error=str(e))
            raise

    async def publish_async(
        self, topic: str, event: Any, key: str | None = None, headers: dict | None = None
    ) -> None:
        """Async wrapper for publish."""
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self.publish, topic, event, key, headers)

    def publish_confirmed(
        self,
        topic: str,
        event: dict,
        key: str,
        timeout: float = 10.0,
    ) -> None:
        """Return only after Kafka's delivery callback confirms broker ACK.

        Unconfirmed sends must never mark durable outbox rows as published.
        Timeout raises; a late ACK can still happen, causing a safe replay.
        """
        producer = self._get_producer()
        completed: list[object] = []

        def on_delivery(error: object, message: Any) -> None:
            self._delivery_callback(error, message)
            completed.append(error)

        producer.produce(
            topic=topic,
            key=key.encode("utf-8"),
            value=json.dumps(event, cls=KafkaEncoder).encode("utf-8"),
            callback=on_delivery,
        )
        deadline = time.monotonic() + timeout
        while not completed and time.monotonic() < deadline:
            producer.poll(min(0.2, max(0, deadline - time.monotonic())))
        if not completed:
            raise TimeoutError("Broker delivery acknowledgement not received")
        if completed[0] is not None:
            raise RuntimeError("Broker rejected event delivery")

    async def publish_confirmed_async(
        self,
        topic: str,
        event: dict,
        key: str,
        timeout: float = 10.0,
    ) -> None:
        """Use confirmed publication without blocking the API event loop."""
        await asyncio.to_thread(self.publish_confirmed, topic, event, key, timeout)

    def flush(self, timeout: float = 10.0) -> int:
        """Flush pending messages."""
        if self._producer:
            return self._producer.flush(timeout)
        return 0

    def close(self) -> None:
        """Close the producer."""
        if self._producer:
            self._producer.flush(30)
            self._producer = None
            logger.info(
                "Kafka producer closed", delivered=self._delivery_count, errors=self._error_count
            )

    @property
    def stats(self) -> dict:
        """Get producer statistics."""
        return {
            "delivered": self._delivery_count,
            "errors": self._error_count,
        }


# Singleton instance
_producer: KafkaProducerService | None = None


def get_kafka_producer() -> KafkaProducerService:
    """Get or create Kafka producer singleton."""
    global _producer
    if _producer is None:
        _producer = KafkaProducerService()
    return _producer

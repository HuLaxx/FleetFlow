"""Events module - Kafka producers and event models."""

from src.events.models import (
    Address,
    DriverStatus,
    DriverStatusEvent,
    EventType,
    GPSLocationEvent,
    Location,
    OrderAssignedEvent,
    OrderCancelledEvent,
    OrderCreatedEvent,
    OrderDeliveredEvent,
    OrderItem,
    OrderPriority,
    OrderStatus,
    RouteCreatedEvent,
    RouteStartedEvent,
    RouteStop,
    StopCompletedEvent,
    TimeWindow,
    TrafficUpdateEvent,
)
from src.events.producer import (
    KafkaProducerService,
    get_kafka_producer,
)

__all__ = [
    # Enums
    "EventType",
    "OrderStatus",
    "OrderPriority",
    "DriverStatus",
    # Models
    "Location",
    "Address",
    "TimeWindow",
    "OrderItem",
    # Events
    "OrderCreatedEvent",
    "OrderCancelledEvent",
    "OrderAssignedEvent",
    "OrderDeliveredEvent",
    "GPSLocationEvent",
    "DriverStatusEvent",
    "RouteCreatedEvent",
    "RouteStartedEvent",
    "RouteStop",
    "StopCompletedEvent",
    "TrafficUpdateEvent",
    # Producer
    "KafkaProducerService",
    "get_kafka_producer",
]

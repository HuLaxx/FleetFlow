"""Events module - Kafka producers and event models."""

from src.events.models import (
    EventType,
    OrderStatus,
    OrderPriority,
    DriverStatus,
    Location,
    Address,
    TimeWindow,
    OrderItem,
    OrderCreatedEvent,
    OrderCancelledEvent,
    OrderAssignedEvent,
    OrderDeliveredEvent,
    GPSLocationEvent,
    DriverStatusEvent,
    RouteCreatedEvent,
    RouteStartedEvent,
    RouteStop,
    StopCompletedEvent,
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

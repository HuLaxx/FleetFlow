"""Kafka consumers package."""

from src.consumers.gps_consumer import GPSLocationConsumer
from src.consumers.driver_consumer import DriverStatusConsumer
from src.consumers.order_consumer import OrderEventsConsumer
from src.consumers.route_consumer import RouteEventsConsumer

__all__ = [
    "GPSLocationConsumer",
    "DriverStatusConsumer",
    "OrderEventsConsumer",
    "RouteEventsConsumer",
]

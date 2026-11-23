"""SQLAlchemy ORM models for FleetFlow database."""

from src.models.customer import Customer
from src.models.depot import Depot
from src.models.dispatch_events import (
    DispatchConsumerInbox,
    DispatchOutboxEvent,
    DispatchQuarantineEvent,
    RouteApprovalAudit,
)
from src.models.driver import Driver
from src.models.order import Order
from src.models.route import Route
from src.models.route_stop import RouteStop
from src.models.user import User
from src.models.vehicle import Vehicle

__all__ = [
    "Customer",
    "Depot",
    "DispatchConsumerInbox",
    "DispatchOutboxEvent",
    "DispatchQuarantineEvent",
    "Driver",
    "Order",
    "Route",
    "RouteApprovalAudit",
    "RouteStop",
    "User",
    "Vehicle",
]

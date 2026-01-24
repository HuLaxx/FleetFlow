"""
GraphQL Schema Types for FleetFlow.
"""

from datetime import datetime, date
from typing import Optional, List
from uuid import UUID
import strawberry


@strawberry.type
class Location:
    """Geographic location."""
    latitude: float
    longitude: float
    address: Optional[str] = None


@strawberry.type
class Depot:
    """Depot/Warehouse."""
    id: strawberry.ID
    name: str
    address: str
    city: str
    state: str
    location: Location
    operating_hours_start: Optional[str] = None
    operating_hours_end: Optional[str] = None


@strawberry.type
class Vehicle:
    """Delivery vehicle."""
    id: strawberry.ID
    vehicle_number: str
    type: str
    capacity_kg: float
    status: str
    current_location: Optional[Location] = None


@strawberry.type
class Driver:
    """Delivery driver."""
    id: strawberry.ID
    employee_id: str
    name: str
    email: str
    phone: Optional[str] = None
    status: str
    rating: float
    total_deliveries: int
    current_location: Optional[Location] = None
    current_vehicle: Optional[Vehicle] = None
    preferred_depot: Optional[Depot] = None


@strawberry.type
class Customer:
    """Customer."""
    id: strawberry.ID
    name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    address: str
    location: Location


@strawberry.type
class OrderItem:
    """Item in an order."""
    name: str
    quantity: int
    weight_kg: float


@strawberry.type
class Order:
    """Delivery order."""
    id: strawberry.ID
    order_number: str
    status: str
    priority: int
    delivery_date: str
    time_window_start: str
    time_window_end: str
    total_weight_kg: float
    total_value: Optional[float] = None
    items: List[OrderItem]
    customer: Optional[Customer] = None
    depot: Optional[Depot] = None


@strawberry.type
class RouteStop:
    """Stop on a route."""
    sequence: int
    order: Order
    planned_arrival: str
    actual_arrival: Optional[str] = None
    status: str


@strawberry.type
class Route:
    """Delivery route."""
    id: strawberry.ID
    route_date: str
    status: str
    planned_stops: int
    completed_stops: int
    driver: Optional[Driver] = None
    vehicle: Optional[Vehicle] = None
    depot: Optional[Depot] = None
    stops: List[RouteStop]
    total_distance_km: Optional[float] = None
    total_duration_minutes: Optional[int] = None


@strawberry.type
class DriverStats:
    """Driver fleet statistics."""
    total_drivers: int
    available: int
    on_route: int
    on_break: int
    offline: int
    avg_rating: float


@strawberry.type
class OrderStats:
    """Order statistics."""
    total_orders: int
    pending: int
    in_transit: int
    delivered: int
    failed: int


@strawberry.type
class RouteStats:
    """Route statistics."""
    total_routes: int
    in_progress: int
    completed: int
    total_distance_km: float
    avg_stops_per_route: float


@strawberry.type
class DashboardStats:
    """Combined dashboard statistics."""
    drivers: DriverStats
    orders: OrderStats
    routes: RouteStats


@strawberry.type
class OptimizationResult:
    """Route optimization result."""
    success: bool
    routes_created: int
    total_orders_assigned: int
    estimated_distance_km: float
    estimated_duration_minutes: int
    optimization_time_ms: float


# Input types
@strawberry.input
class LocationInput:
    """Location input."""
    latitude: float
    longitude: float
    address: Optional[str] = None


@strawberry.input
class CreateOrderInput:
    """Create order input."""
    customer_id: strawberry.ID
    depot_id: strawberry.ID
    delivery_date: str
    time_window_start: str
    time_window_end: str
    items: List[str]  # JSON strings
    priority: int = 1


@strawberry.input
class UpdateDriverLocationInput:
    """Update driver location input."""
    driver_id: strawberry.ID
    latitude: float
    longitude: float
    speed_kmh: Optional[float] = None
    heading: Optional[float] = None


@strawberry.input
class OptimizeRoutesInput:
    """Route optimization input."""
    date: str
    depot_id: strawberry.ID

"""
GraphQL Schema Types for FleetFlow.
"""

import strawberry


@strawberry.type
class Location:
    """Geographic location."""

    latitude: float
    longitude: float
    address: str | None = None


@strawberry.type
class Depot:
    """Depot/Warehouse."""

    id: strawberry.ID
    name: str
    address: str
    city: str
    state: str
    location: Location
    operating_hours_start: str | None = None
    operating_hours_end: str | None = None


@strawberry.type
class Vehicle:
    """Delivery vehicle."""

    id: strawberry.ID
    vehicle_number: str
    type: str
    capacity_kg: float
    status: str
    current_location: Location | None = None


@strawberry.type
class Driver:
    """Delivery driver."""

    id: strawberry.ID
    employee_id: str
    name: str
    email: str
    phone: str | None = None
    status: str
    rating: float
    total_deliveries: int
    current_location: Location | None = None
    current_vehicle: Vehicle | None = None
    preferred_depot: Depot | None = None


@strawberry.type
class Customer:
    """Customer."""

    id: strawberry.ID
    name: str
    email: str | None = None
    phone: str | None = None
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
    total_value: float | None = None
    items: list[OrderItem]
    customer: Customer | None = None
    depot: Depot | None = None


@strawberry.type
class RouteStop:
    """Stop on a route."""

    sequence: int
    order: Order
    planned_arrival: str
    actual_arrival: str | None = None
    status: str


@strawberry.type
class Route:
    """Delivery route."""

    id: strawberry.ID
    route_date: str
    status: str
    planned_stops: int
    completed_stops: int
    driver: Driver | None = None
    vehicle: Vehicle | None = None
    depot: Depot | None = None
    stops: list[RouteStop]
    total_distance_km: float | None = None
    total_duration_minutes: int | None = None


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
    address: str | None = None


@strawberry.input
class CreateOrderInput:
    """Create order input."""

    customer_id: strawberry.ID
    depot_id: strawberry.ID
    delivery_date: str
    time_window_start: str
    time_window_end: str
    items: list[str]  # JSON strings
    priority: int = 1


@strawberry.input
class UpdateDriverLocationInput:
    """Update driver location input."""

    driver_id: strawberry.ID
    latitude: float
    longitude: float
    speed_kmh: float | None = None
    heading: float | None = None


@strawberry.input
class OptimizeRoutesInput:
    """Route optimization input."""

    date: str
    depot_id: strawberry.ID

"""Pydantic models for Kafka events."""

from datetime import datetime, timezone
from typing import Literal, Optional
from uuid import UUID, uuid4
from pydantic import BaseModel, Field
from enum import Enum


# ============================================
# Enums
# ============================================

class OrderStatus(str, Enum):
    PENDING = "pending"
    ASSIGNED = "assigned"
    IN_TRANSIT = "in_transit"
    ARRIVED = "arrived"
    DELIVERED = "delivered"
    FAILED = "failed"
    CANCELLED = "cancelled"
    RESCHEDULED = "rescheduled"


class OrderPriority(int, Enum):
    LOW = 1
    NORMAL = 2
    HIGH = 3
    URGENT = 4
    CRITICAL = 5


class DriverStatus(str, Enum):
    AVAILABLE = "available"
    ON_ROUTE = "on_route"
    ON_BREAK = "on_break"
    OFFLINE = "offline"


class EventType(str, Enum):
    # Order events
    ORDER_CREATED = "order.created"
    ORDER_UPDATED = "order.updated"
    ORDER_CANCELLED = "order.cancelled"
    ORDER_ASSIGNED = "order.assigned"
    ORDER_DELIVERED = "order.delivered"
    ORDER_FAILED = "order.failed"
    
    # Driver events
    DRIVER_LOCATION_UPDATED = "driver.location_updated"
    DRIVER_STATUS_CHANGED = "driver.status_changed"
    
    # Route events
    ROUTE_CREATED = "route.created"
    ROUTE_STARTED = "route.started"
    ROUTE_COMPLETED = "route.completed"
    ROUTE_OPTIMIZED = "route.optimized"
    
    # Stop events
    STOP_ARRIVED = "stop.arrived"
    STOP_COMPLETED = "stop.completed"
    STOP_SKIPPED = "stop.skipped"


# ============================================
# Base Models
# ============================================

class Location(BaseModel):
    """Geographic location."""
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    
    def to_tuple(self) -> tuple[float, float]:
        return (self.latitude, self.longitude)


class Address(BaseModel):
    """Physical address."""
    street: str
    city: str
    state: str
    postal_code: str
    country: str = "US"
    location: Location


class TimeWindow(BaseModel):
    """Delivery time window."""
    start: datetime
    end: datetime


# ============================================
# Order Events
# ============================================

class OrderItem(BaseModel):
    """Item in an order."""
    sku: str
    name: str
    quantity: int = Field(..., ge=1)
    weight_kg: float = Field(..., ge=0)
    is_fragile: bool = False


class OrderCreatedEvent(BaseModel):
    """Event published when a new order is created."""
    event_type: EventType = EventType.ORDER_CREATED
    schema_version: Literal[1] = 1
    event_id: UUID = Field(default_factory=uuid4)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    # Order data
    order_id: UUID
    order_number: str
    customer_id: UUID
    depot_id: Optional[UUID] = None
    
    # Delivery details
    delivery_address: Address
    delivery_date: str  # ISO date
    time_window: TimeWindow
    
    # Items
    items: list[OrderItem]
    total_weight_kg: float
    total_value: Optional[float] = None
    
    # Metadata
    priority: OrderPriority = OrderPriority.NORMAL
    source: str = "api"
    external_order_id: Optional[str] = None
    special_instructions: Optional[str] = None


class OrderCancelledEvent(BaseModel):
    """Event published when an order is cancelled."""
    event_type: EventType = EventType.ORDER_CANCELLED
    schema_version: Literal[1] = 1
    event_id: UUID = Field(default_factory=uuid4)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    order_id: UUID
    order_number: str
    reason: str
    cancelled_by: str  # 'customer', 'dispatcher', 'system'


class OrderAssignedEvent(BaseModel):
    """Event published when an order is assigned to a route."""
    event_type: EventType = EventType.ORDER_ASSIGNED
    schema_version: Literal[1] = 1
    event_id: UUID = Field(default_factory=uuid4)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    order_id: UUID
    route_id: UUID
    driver_id: UUID
    stop_sequence: int
    estimated_arrival: datetime


class OrderDeliveredEvent(BaseModel):
    """Event published when an order is delivered."""
    event_type: EventType = EventType.ORDER_DELIVERED
    schema_version: Literal[1] = 1
    event_id: UUID = Field(default_factory=uuid4)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    order_id: UUID
    route_id: UUID
    driver_id: UUID
    delivered_at: datetime
    recipient_name: Optional[str] = None
    signature_url: Optional[str] = None
    photo_url: Optional[str] = None


# ============================================
# GPS Events
# ============================================

class GPSLocationEvent(BaseModel):
    """Real-time GPS location update from driver."""
    event_type: EventType = EventType.DRIVER_LOCATION_UPDATED
    schema_version: Literal[1] = 1
    event_id: UUID = Field(default_factory=uuid4)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    driver_id: UUID
    vehicle_id: UUID
    location: Location
    speed_kmh: Optional[float] = Field(None, ge=0)
    heading: Optional[float] = Field(None, ge=0, le=360)
    accuracy_m: Optional[float] = Field(None, ge=0)
    altitude_m: Optional[float] = None
    battery_level: Optional[int] = Field(None, ge=0, le=100)
    is_moving: bool = True


class DriverStatusEvent(BaseModel):
    """Event published when driver status changes."""
    event_type: EventType = EventType.DRIVER_STATUS_CHANGED
    schema_version: Literal[1] = 1
    event_id: UUID = Field(default_factory=uuid4)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    driver_id: UUID
    previous_status: DriverStatus
    new_status: DriverStatus
    reason: Optional[str] = None


# ============================================
# Route Events
# ============================================

class RouteStop(BaseModel):
    """Stop within a route."""
    stop_sequence: int
    order_id: UUID
    location: Location
    address: str
    planned_arrival: datetime
    service_time_minutes: int = 5


class RouteCreatedEvent(BaseModel):
    """Event published when a route is optimized and created."""
    event_type: EventType = EventType.ROUTE_CREATED
    schema_version: Literal[1] = 1
    event_id: UUID = Field(default_factory=uuid4)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    route_id: UUID
    route_date: str  # ISO date
    driver_id: UUID
    vehicle_id: UUID
    depot_id: UUID
    
    # Route details
    stops: list[RouteStop]
    planned_distance_km: float
    planned_duration_minutes: int
    
    # Optimization metadata
    algorithm_used: str
    optimization_score: float
    computation_time_ms: int


class RouteStartedEvent(BaseModel):
    """Event published when driver starts a route."""
    event_type: EventType = EventType.ROUTE_STARTED
    schema_version: Literal[1] = 1
    event_id: UUID = Field(default_factory=uuid4)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    route_id: UUID
    driver_id: UUID
    started_at: datetime
    first_stop_eta: datetime


class StopCompletedEvent(BaseModel):
    """Event published when a stop is completed."""
    event_type: EventType = EventType.STOP_COMPLETED
    schema_version: Literal[1] = 1
    event_id: UUID = Field(default_factory=uuid4)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    route_id: UUID
    stop_id: UUID
    order_id: UUID
    driver_id: UUID
    completed_at: datetime
    actual_service_time_minutes: int
    next_stop_eta: Optional[datetime] = None


# ============================================
# Traffic Events
# ============================================

class TrafficUpdateEvent(BaseModel):
    """Traffic data from external API."""
    schema_version: Literal[1] = 1
    event_id: UUID = Field(default_factory=uuid4)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    segment_id: str
    location: Location
    current_speed_kmh: float
    free_flow_speed_kmh: float
    congestion_level: float = Field(..., ge=0, le=1)  # 0 = free flow, 1 = standstill
    delay_minutes: float
    confidence: float = Field(default=0.9, ge=0, le=1)
    source: str = "tomtom"

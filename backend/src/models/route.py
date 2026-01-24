"""Route model."""

from datetime import date, datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy import String, Integer, Date, Numeric, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from geoalchemy2 import Geography

from src.database import Base


class Route(Base):
    """
    Optimized Delivery Route.
    
    Represents a planned route for a driver/vehicle.
    """
    __tablename__ = "routes"
    
    # Primary Key
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    
    # Schedule
    route_date: Mapped[date] = mapped_column(Date, nullable=False)
    
    # Assignments
    driver_id: Mapped[Optional[UUID]] = mapped_column(
        ForeignKey("drivers.id", ondelete="SET NULL")
    )
    vehicle_id: Mapped[Optional[UUID]] = mapped_column(
        ForeignKey("vehicles.id", ondelete="SET NULL")
    )
    depot_id: Mapped[Optional[UUID]] = mapped_column(
        ForeignKey("depots.id", ondelete="SET NULL")
    )
    
    # Route Geometry (PostGIS)
    planned_route: Mapped[Optional[str]] = mapped_column(
        Geography(geometry_type="LINESTRING", srid=4326)
    )
    actual_route: Mapped[Optional[str]] = mapped_column(
        Geography(geometry_type="LINESTRING", srid=4326)
    )
    
    # Planned Metrics
    planned_distance_km: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2))
    planned_duration_minutes: Mapped[Optional[int]] = mapped_column(Integer)
    planned_stops: Mapped[Optional[int]] = mapped_column(Integer)
    
    # Actual Metrics
    actual_distance_km: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2))
    actual_duration_minutes: Mapped[Optional[int]] = mapped_column(Integer)
    completed_stops: Mapped[int] = mapped_column(Integer, default=0)
    
    # Optimization Metadata
    algorithm_used: Mapped[Optional[str]] = mapped_column(String(50))
    optimization_score: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 4))
    computation_time_ms: Mapped[Optional[int]] = mapped_column(Integer)
    
    # Status: planned, in_progress, completed, cancelled
    status: Mapped[str] = mapped_column(String(20), default="planned")
    
    # Timing
    started_at: Mapped[Optional[datetime]] = mapped_column()
    completed_at: Mapped[Optional[datetime]] = mapped_column()
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), onupdate=func.now(), nullable=False
    )
    
    # Relationships
    driver: Mapped[Optional["Driver"]] = relationship(
        "Driver", back_populates="routes"
    )
    vehicle: Mapped[Optional["Vehicle"]] = relationship(
        "Vehicle", back_populates="routes"
    )
    depot: Mapped[Optional["Depot"]] = relationship(
        "Depot", back_populates="routes"
    )
    stops: Mapped[list["RouteStop"]] = relationship(
        "RouteStop", back_populates="route", cascade="all, delete-orphan"
    )
    
    def __repr__(self) -> str:
        return f"<Route(id={self.id}, date={self.route_date}, status='{self.status}')>"

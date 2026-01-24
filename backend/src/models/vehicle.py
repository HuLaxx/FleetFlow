"""Vehicle model."""

from datetime import date, datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy import String, Integer, Date, Numeric, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from geoalchemy2 import Geography

from src.database import Base


class Vehicle(Base):
    """
    Vehicle/Fleet Asset.
    
    Represents a delivery vehicle (van, truck, bike, car).
    """
    __tablename__ = "vehicles"
    
    # Primary Key
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    
    # Identification
    vehicle_number: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    type: Mapped[str] = mapped_column(String(50), nullable=False)  # van, truck, bike, car
    make: Mapped[Optional[str]] = mapped_column(String(100))
    model: Mapped[Optional[str]] = mapped_column(String(100))
    year: Mapped[Optional[int]] = mapped_column(Integer)
    
    # Capacity
    capacity_kg: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    capacity_cubic_m: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2))
    
    # Fuel & Emissions
    fuel_type: Mapped[str] = mapped_column(
        String(20), default="diesel"
    )  # diesel, petrol, electric, hybrid
    fuel_efficiency_km_per_l: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2))
    co2_emission_g_per_km: Mapped[Optional[Decimal]] = mapped_column(Numeric(6, 2))
    
    # Assignment
    depot_id: Mapped[Optional[UUID]] = mapped_column(
        ForeignKey("depots.id", ondelete="SET NULL")
    )
    current_driver_id: Mapped[Optional[UUID]] = mapped_column(
        ForeignKey("drivers.id", ondelete="SET NULL")
    )
    
    # Current Location (PostGIS)
    latitude: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 7))
    longitude: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 7))
    current_location: Mapped[Optional[str]] = mapped_column(
        Geography(geometry_type="POINT", srid=4326)
    )
    
    # Status: available, in_use, maintenance, retired
    status: Mapped[str] = mapped_column(String(20), default="available")
    
    # Maintenance
    last_maintenance_date: Mapped[Optional[date]] = mapped_column(Date)
    next_maintenance_date: Mapped[Optional[date]] = mapped_column(Date)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), onupdate=func.now(), nullable=False
    )
    
    # Relationships
    depot: Mapped[Optional["Depot"]] = relationship(
        "Depot", back_populates="vehicles"
    )
    current_driver: Mapped[Optional["Driver"]] = relationship(
        "Driver", foreign_keys=[current_driver_id]
    )
    routes: Mapped[list["Route"]] = relationship(
        "Route", back_populates="vehicle"
    )
    
    def __repr__(self) -> str:
        return f"<Vehicle(id={self.id}, number='{self.vehicle_number}', type='{self.type}')>"

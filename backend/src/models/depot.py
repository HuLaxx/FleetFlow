"""Depot (Warehouse/Distribution Center) model."""

from datetime import time, datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy import String, Integer, Boolean, Time, Numeric, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from geoalchemy2 import Geography

from src.database import Base


class Depot(Base):
    """
    Depot/Warehouse/Distribution Center.
    
    Represents a physical location from which deliveries originate.
    """
    __tablename__ = "depots"
    
    # Primary Key
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    
    # Basic Info
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    address: Mapped[str] = mapped_column(String, nullable=False)
    
    # Location (PostGIS)
    latitude: Mapped[Decimal] = mapped_column(Numeric(10, 7), nullable=False)
    longitude: Mapped[Decimal] = mapped_column(Numeric(10, 7), nullable=False)
    location: Mapped[str] = mapped_column(
        Geography(geometry_type="POINT", srid=4326),
        nullable=False,
    )
    
    # Capacity
    capacity_vehicles: Mapped[Optional[int]] = mapped_column(Integer, default=50)
    
    # Operating Hours
    operating_hours_start: Mapped[Optional[time]] = mapped_column(
        Time, default=time(6, 0)
    )
    operating_hours_end: Mapped[Optional[time]] = mapped_column(
        Time, default=time(22, 0)
    )
    
    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), onupdate=func.now(), nullable=False
    )
    
    # Relationships
    drivers: Mapped[list["Driver"]] = relationship(
        "Driver", back_populates="preferred_depot"
    )
    vehicles: Mapped[list["Vehicle"]] = relationship(
        "Vehicle", back_populates="depot"
    )
    orders: Mapped[list["Order"]] = relationship(
        "Order", back_populates="depot"
    )
    routes: Mapped[list["Route"]] = relationship(
        "Route", back_populates="depot"
    )
    
    def __repr__(self) -> str:
        return f"<Depot(id={self.id}, name='{self.name}')>"

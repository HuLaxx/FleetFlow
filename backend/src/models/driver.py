"""Driver model."""

from datetime import date, datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID, uuid4

from geoalchemy2 import Geography
from sqlalchemy import Date, ForeignKey, Integer, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database import Base


class Driver(Base):
    """
    Driver/Delivery Personnel.

    Represents a person who delivers orders.
    """

    __tablename__ = "drivers"

    # Primary Key
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)

    # Identification
    employee_id: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    phone: Mapped[str | None] = mapped_column(String(20))

    # License
    license_number: Mapped[str | None] = mapped_column(String(50))
    license_expiry: Mapped[date | None] = mapped_column(Date)

    # Home Location (PostGIS)
    home_location: Mapped[str | None] = mapped_column(Geography(geometry_type="POINT", srid=4326))

    # Depot Assignment
    preferred_depot_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("depots.id", ondelete="SET NULL")
    )

    # Working Hours
    max_working_hours_per_day: Mapped[Decimal] = mapped_column(
        Numeric(4, 2), default=Decimal("8.00")
    )

    # Status: available, on_route, on_break, offline
    status: Mapped[str] = mapped_column(String(20), default="available", nullable=False)

    # Performance Metrics
    rating: Mapped[Decimal] = mapped_column(Numeric(3, 2), default=Decimal("5.00"))
    total_deliveries: Mapped[int] = mapped_column(Integer, default=0)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    preferred_depot: Mapped[Optional["Depot"]] = relationship("Depot", back_populates="drivers")
    routes: Mapped[list["Route"]] = relationship("Route", back_populates="driver")

    @property
    def full_name(self) -> str:
        """Get driver's full name."""
        return f"{self.first_name} {self.last_name}"

    def __repr__(self) -> str:
        return f"<Driver(id={self.id}, name='{self.full_name}', status='{self.status}')>"

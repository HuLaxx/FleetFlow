"""Route Stop model."""

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Optional
from uuid import UUID, uuid4

from geoalchemy2 import Geography
from sqlalchemy import ForeignKey, Integer, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database import Base

if TYPE_CHECKING:
    from src.models import Order, Route


class RouteStop(Base):
    """
    Individual Stop in a Route.

    Represents a specific delivery stop in an optimized route.
    """

    __tablename__ = "route_stops"

    # Primary Key
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)

    # Foreign Keys
    route_id: Mapped[UUID | None] = mapped_column(ForeignKey("routes.id", ondelete="CASCADE"))
    order_id: Mapped[UUID | None] = mapped_column(ForeignKey("orders.id", ondelete="SET NULL"))

    # Sequence
    stop_sequence: Mapped[int] = mapped_column(Integer, nullable=False)

    # Location (PostGIS)
    latitude: Mapped[Decimal] = mapped_column(Numeric(10, 7), nullable=False)
    longitude: Mapped[Decimal] = mapped_column(Numeric(10, 7), nullable=False)
    location: Mapped[str] = mapped_column(
        Geography(geometry_type="POINT", srid=4326),
        nullable=False,
    )
    address: Mapped[str] = mapped_column(String, nullable=False)

    # Timing - Planned
    planned_arrival: Mapped[datetime | None] = mapped_column()
    planned_departure: Mapped[datetime | None] = mapped_column()

    # Timing - Actual
    actual_arrival: Mapped[datetime | None] = mapped_column()
    actual_departure: Mapped[datetime | None] = mapped_column()

    # Distance from Previous Stop
    distance_from_prev_km: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    duration_from_prev_minutes: Mapped[int | None] = mapped_column(Integer)

    # Status: pending, en_route, arrived, completed, skipped, failed
    status: Mapped[str] = mapped_column(String(20), default="pending")
    failure_reason: Mapped[str | None] = mapped_column(String)

    # Proof of Delivery
    signature_url: Mapped[str | None] = mapped_column(String)
    photo_url: Mapped[str | None] = mapped_column(String)
    recipient_name: Mapped[str | None] = mapped_column(String(255))

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    route: Mapped[Optional["Route"]] = relationship("Route", back_populates="stops")
    order: Mapped[Optional["Order"]] = relationship("Order")

    def __repr__(self) -> str:
        return f"<RouteStop(id={self.id}, sequence={self.stop_sequence}, status='{self.status}')>"

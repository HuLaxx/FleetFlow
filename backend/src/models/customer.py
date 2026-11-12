"""Customer model."""

from datetime import datetime, time
from decimal import Decimal
from uuid import UUID, uuid4

from geoalchemy2 import Geography
from sqlalchemy import Integer, Numeric, String, Time, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database import Base


class Customer(Base):
    """
    Customer/Delivery Recipient.

    Represents an end customer receiving deliveries.
    """

    __tablename__ = "customers"

    # Primary Key
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)

    # Identification
    external_id: Mapped[str | None] = mapped_column(String(100))
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str | None] = mapped_column(String(255))
    phone: Mapped[str | None] = mapped_column(String(20))

    # Address & Location (PostGIS)
    address: Mapped[str] = mapped_column(String, nullable=False)
    latitude: Mapped[Decimal] = mapped_column(Numeric(10, 7), nullable=False)
    longitude: Mapped[Decimal] = mapped_column(Numeric(10, 7), nullable=False)
    location: Mapped[str] = mapped_column(
        Geography(geometry_type="POINT", srid=4326),
        nullable=False,
    )

    # Delivery Preferences
    delivery_instructions: Mapped[str | None] = mapped_column(String)
    preferred_time_window_start: Mapped[time | None] = mapped_column(Time)
    preferred_time_window_end: Mapped[time | None] = mapped_column(Time)
    priority: Mapped[int] = mapped_column(Integer, default=1)  # 1-5

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    orders: Mapped[list["Order"]] = relationship("Order", back_populates="customer")

    def __repr__(self) -> str:
        return f"<Customer(id={self.id}, name='{self.name}')>"

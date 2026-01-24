"""Order model."""

from datetime import date, datetime
from decimal import Decimal
from typing import Optional, Any
from uuid import UUID, uuid4

from sqlalchemy import String, Integer, Date, Numeric, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import JSONB

from src.database import Base


class Order(Base):
    """
    Order/Delivery Request.
    
    Represents a customer order to be delivered.
    """
    __tablename__ = "orders"
    
    # Primary Key
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    
    # Identification
    order_number: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    
    # Foreign Keys
    customer_id: Mapped[Optional[UUID]] = mapped_column(
        ForeignKey("customers.id", ondelete="SET NULL")
    )
    depot_id: Mapped[Optional[UUID]] = mapped_column(
        ForeignKey("depots.id", ondelete="SET NULL")
    )
    
    # Order Details
    items: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB, default=list, nullable=False
    )
    total_weight_kg: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    total_value: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 2))
    
    # Delivery Requirements
    delivery_date: Mapped[date] = mapped_column(Date, nullable=False)
    time_window_start: Mapped[datetime] = mapped_column(nullable=False)
    time_window_end: Mapped[datetime] = mapped_column(nullable=False)
    service_time_minutes: Mapped[int] = mapped_column(Integer, default=5)
    
    # Status: pending, assigned, in_transit, arrived, delivered, failed, cancelled, rescheduled
    status: Mapped[str] = mapped_column(String(30), default="pending")
    priority: Mapped[int] = mapped_column(Integer, default=1)  # 1-5
    
    # Integration
    source: Mapped[str] = mapped_column(String(50), default="manual")
    external_order_id: Mapped[Optional[str]] = mapped_column(String(100))
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), onupdate=func.now(), nullable=False
    )
    
    # Relationships
    customer: Mapped[Optional["Customer"]] = relationship(
        "Customer", back_populates="orders"
    )
    depot: Mapped[Optional["Depot"]] = relationship(
        "Depot", back_populates="orders"
    )
    
    def __repr__(self) -> str:
        return f"<Order(id={self.id}, number='{self.order_number}', status='{self.status}')>"

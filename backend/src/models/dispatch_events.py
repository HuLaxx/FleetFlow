"""Durable approval audit, transactional event outbox and consumer inbox.

The approval audit is append-only at the database boundary when the accompanying
SQL migration installs its UPDATE/DELETE trigger. An application-only row model
is not sufficient to make a record immutable.
"""

from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from src.database import Base


class RouteApprovalAudit(Base):
    """One durable approval fact per route, tied to the authenticated user."""

    __tablename__ = "route_approval_audit"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    route_id: Mapped[UUID] = mapped_column(
        ForeignKey("routes.id", ondelete="RESTRICT"), nullable=False, unique=True
    )
    approved_by_user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    event_id: Mapped[UUID] = mapped_column(nullable=False, unique=True)
    previous_status: Mapped[str] = mapped_column(String(20), nullable=False)
    new_status: Mapped[str] = mapped_column(String(20), nullable=False)
    approved_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class DispatchOutboxEvent(Base):
    """Kafka event to publish after the same DB transaction commits."""

    __tablename__ = "dispatch_outbox"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    topic: Mapped[str] = mapped_column(String(100), nullable=False)
    message_key: Mapped[str] = mapped_column(String(100), nullable=False)
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    next_attempt_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_error: Mapped[str | None] = mapped_column(String(150))

    __table_args__ = (Index("ix_dispatch_outbox_ready", "status", "next_attempt_at"),)


class DispatchConsumerInbox(Base):
    """Committed processing receipt for the idempotent consumer handler."""

    __tablename__ = "dispatch_consumer_inbox"

    consumer_name: Mapped[str] = mapped_column(String(100), primary_key=True)
    event_id: Mapped[UUID] = mapped_column(primary_key=True)
    processed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        UniqueConstraint("consumer_name", "event_id", name="uq_dispatch_consumer_receipt"),
    )

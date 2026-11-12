"""
Order events consumer.

Consumes order creation/cancellation events and updates the database.
"""

from datetime import datetime, UTC
from uuid import UUID

import structlog
from fastapi import WebSocketDisconnect
from sqlalchemy import select

from src.consumers.base import BaseKafkaConsumer
from src.database import AsyncSessionLocal
from src.models import Order

logger = structlog.get_logger()


class OrderEventsConsumer(BaseKafkaConsumer):
    """
    Consumes order-related events.

    Topics: orders.created, orders.cancelled

    Event formats:

    orders.created:
    {
        "order_id": "uuid",
        "order_number": "ORD-20240115-ABC123",
        "customer_id": "uuid",
        "delivery_address": {...},
        "delivery_date": "2024-01-15",
        "time_window": {"start": "...", "end": "..."},
        "items": [...],
        "total_weight_kg": 25.5,
        "priority": 2,
        "timestamp": "2024-01-15T10:30:00Z"
    }

    orders.cancelled:
    {
        "order_id": "uuid",
        "order_number": "ORD-20240115-ABC123",
        "reason": "Customer request",
        "cancelled_by": "dispatcher",
        "timestamp": "2024-01-15T11:00:00Z"
    }
    """

    def __init__(self):
        super().__init__(
            topics=["orders.created", "orders.cancelled"],
            group_id="order-events-consumer",
        )
        self.websocket_manager = None

    def set_websocket_manager(self, manager):
        """Inject WebSocket manager."""
        self.websocket_manager = manager

    async def handle_message(
        self,
        topic: str,
        key: str | None,
        value: dict,
        timestamp: int,
    ):
        """Process order event based on topic."""
        if topic == "orders.created":
            await self._handle_order_created(value)
        elif topic == "orders.cancelled":
            await self._handle_order_cancelled(value)
        else:
            logger.warning("Unknown order topic", topic=topic)

    async def _handle_order_created(self, event_data: dict):
        """Handle order creation event."""
        try:
            order_id = UUID(event_data["order_id"])

            # Order should already be in DB (created by API)
            # But we can update status or trigger optimization
            async with AsyncSessionLocal() as session:
                stmt = select(Order).where(Order.id == order_id)
                result = await session.execute(stmt)
                order = result.scalar_one_or_none()

                if order:
                    logger.info(
                        "Order creation event processed",
                        order_id=str(order_id),
                        order_number=event_data["order_number"],
                        status=order.status,
                    )

                    # TODO: Trigger route optimization
                    # TODO: Check if order should be auto-assigned
                else:
                    logger.warning("Order not found in database", order_id=str(order_id))

            # Broadcast to WebSocket
            if self.websocket_manager:
                await self._broadcast_order_update(event_data, "order_created")

        except Exception as e:
            logger.error("Failed to process order created event", error=str(e))
            raise

    async def _handle_order_cancelled(self, event_data: dict):
        """Handle order cancellation event."""
        try:
            order_id = UUID(event_data["order_id"])

            # Verify cancellation in database
            async with AsyncSessionLocal() as session:
                stmt = select(Order).where(Order.id == order_id)
                result = await session.execute(stmt)
                order = result.scalar_one_or_none()

                if order and order.status == "cancelled":
                    logger.info(
                        "Order cancelled", order_id=str(order_id), reason=event_data.get("reason")
                    )

                    # TODO: Remove from active routes if assigned
                    # TODO: Trigger route re-optimization

            # Broadcast to WebSocket
            if self.websocket_manager:
                await self._broadcast_order_update(event_data, "order_cancelled")

        except Exception as e:
            logger.error("Failed to process order cancelled event", error=str(e))
            raise

    async def _broadcast_order_update(self, event_data: dict, event_type: str):
        """Broadcast order update to WebSocket clients."""
        if not self.websocket_manager:
            return

        try:
            from src.websocket_server import WebSocketMessage

            message = WebSocketMessage(
                type=event_type,
                data={
                    "order_id": event_data["order_id"],
                    "order_number": event_data.get("order_number"),
                    "status": "pending" if event_type == "order_created" else "cancelled",
                    "reason": event_data.get("reason"),
                    "updated_at": event_data.get("timestamp", datetime.now(UTC).isoformat()),
                },
            )

            sent_count = await self.websocket_manager.broadcast(message, channel="orders")
            logger.debug(
                f"Order {event_type} broadcasted",
                order_id=event_data["order_id"],
                clients=sent_count,
            )

        except (WebSocketDisconnect, RuntimeError, OSError) as e:
            logger.error("Failed to broadcast order update", error=str(e))

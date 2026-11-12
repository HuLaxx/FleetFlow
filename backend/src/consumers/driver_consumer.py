"""
Driver status event consumer.

Consumes driver status changes and updates the database.
"""

from datetime import datetime, UTC
from uuid import UUID

import structlog
from sqlalchemy import select

from src.consumers.base import BaseKafkaConsumer
from src.database import AsyncSessionLocal
from src.models import Driver

logger = structlog.get_logger()


class DriverStatusConsumer(BaseKafkaConsumer):
    """
    Consumes driver status change events.

    Topic: drivers.status

    Event format:
    {
        "driver_id": "uuid",
        "previous_status": "available",
        "new_status": "on_route",
        "reason": "Started route R-123",
        "timestamp": "2024-01-15T10:30:00Z"
    }
    """

    def __init__(self):
        super().__init__(
            topics=["drivers.status"],
            group_id="driver-status-consumer",
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
        """Process driver status event."""
        try:
            driver_id = UUID(value["driver_id"])
            new_status = value["new_status"]

            # Update driver in database
            async with AsyncSessionLocal() as session:
                stmt = select(Driver).where(Driver.id == driver_id)
                result = await session.execute(stmt)
                driver = result.scalar_one_or_none()

                if driver:
                    driver.status = new_status
                    driver.updated_at = datetime.now(UTC)

                    await session.commit()

                    logger.info(
                        "Driver status updated",
                        driver_id=str(driver_id),
                        old_status=value.get("previous_status"),
                        new_status=new_status,
                    )
                else:
                    logger.warning("Driver not found", driver_id=str(driver_id))

            # Broadcast to WebSocket
            if self.websocket_manager:
                await self._broadcast_to_websocket(value)

        except Exception as e:
            logger.error("Failed to process driver status event", error=str(e))
            raise

    async def _broadcast_to_websocket(self, event_data: dict):
        """Broadcast driver status update."""
        if not self.websocket_manager:
            return

        try:
            from src.websocket_server import WebSocketMessage

            message = WebSocketMessage(
                type="driver_status_update",
                data={
                    "driver_id": event_data["driver_id"],
                    "status": event_data["new_status"],
                    "previous_status": event_data.get("previous_status"),
                    "reason": event_data.get("reason"),
                    "updated_at": event_data.get("timestamp", datetime.now(UTC).isoformat()),
                },
            )

            sent_count = await self.websocket_manager.broadcast(message, channel="all")
            logger.debug(
                "Driver status broadcasted", driver_id=event_data["driver_id"], clients=sent_count
            )

        except Exception as e:
            logger.error("Failed to broadcast driver status", error=str(e))

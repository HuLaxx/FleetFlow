"""
GPS location event consumer.

Consumes GPS updates from Kafka and:
1. Updates vehicle location in PostgreSQL
2. Stores history in TimescaleDB
3. Broadcasts to WebSocket clients
"""

from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID

import structlog
from sqlalchemy import select

from src.consumers.base import BaseKafkaConsumer
from src.database import AsyncSessionLocal
from src.models import Vehicle

logger = structlog.get_logger()


class GPSLocationConsumer(BaseKafkaConsumer):
    """
    Consumes GPS location events and updates vehicle positions.

    Topic: gps.location

    Event format:
    {
        "driver_id": "uuid",
        "vehicle_id": "uuid",
        "location": {"latitude": 40.7484, "longitude": -73.9857},
        "speed_kmh": 35.5,
        "heading": 45.0,
        "accuracy_m": 5.0,
        "altitude_m": 10.0,
        "battery_level": 85,
        "is_moving": true,
        "timestamp": "2024-01-15T10:30:00Z"
    }
    """

    def __init__(self):
        super().__init__(
            topics=["gps.location"],
            group_id="gps-location-consumer",
        )
        self.websocket_manager = None  # Will be injected

    def set_websocket_manager(self, manager):
        """Inject WebSocket manager for broadcasting."""
        self.websocket_manager = manager

    async def handle_message(
        self,
        topic: str,
        key: str | None,
        value: dict,
        timestamp: int,
    ):
        """Process GPS location event."""
        try:
            # Parse event
            vehicle_id = UUID(value["vehicle_id"])
            driver_id = UUID(value["driver_id"]) if value.get("driver_id") else None
            location = value["location"]
            latitude = Decimal(str(location["latitude"]))
            longitude = Decimal(str(location["longitude"]))

            # Update vehicle location in PostgreSQL
            async with AsyncSessionLocal() as session:
                stmt = select(Vehicle).where(Vehicle.id == vehicle_id)
                result = await session.execute(stmt)
                vehicle = result.scalar_one_or_none()

                if vehicle:
                    vehicle.latitude = latitude
                    vehicle.longitude = longitude
                    vehicle.updated_at = datetime.now(timezone.utc)

                    await session.commit()

                    logger.info(
                        "Vehicle location updated",
                        vehicle_id=str(vehicle_id),
                        latitude=float(latitude),
                        longitude=float(longitude),
                    )
                else:
                    logger.warning("Vehicle not found", vehicle_id=str(vehicle_id))

            # TODO: Store in TimescaleDB gps_history
            # TODO: Broadcast to WebSocket clients
            if self.websocket_manager:
                await self._broadcast_to_websocket(value)

        except Exception as e:
            logger.error(
                "Failed to process GPS event",
                error=str(e),
                event_id=value.get("event_id"),
                vehicle_id=value.get("vehicle_id"),
            )
            raise

    async def _broadcast_to_websocket(self, event_data: dict):
        """Broadcast GPS update to WebSocket clients."""
        if not self.websocket_manager:
            return

        try:
            # Import here to avoid circular dependency
            from src.websocket_server import WebSocketMessage

            message = WebSocketMessage(
                type="vehicle_update",
                data={
                    "vehicle_id": event_data["vehicle_id"],
                    "driver_id": event_data.get("driver_id"),
                    "location": {
                        "latitude": event_data["location"]["latitude"],
                        "longitude": event_data["location"]["longitude"],
                    },
                    "speed_kmh": event_data.get("speed_kmh"),
                    "heading": event_data.get("heading"),
                    "updated_at": event_data.get("timestamp", datetime.now(timezone.utc).isoformat()),
                },
            )

            # Broadcast to 'vehicles' channel
            sent_count = await self.websocket_manager.broadcast(message, channel="vehicles")

            logger.debug(
                "GPS update broadcasted", vehicle_id=event_data["vehicle_id"], clients=sent_count
            )

        except Exception as e:
            logger.error("Failed to broadcast GPS update", error=str(e))

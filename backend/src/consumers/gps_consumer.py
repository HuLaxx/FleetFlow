"""Kafka GPS consumer: validated event-time position -> PostgreSQL -> WebSocket.

Broker offsets advance after the durable database write. Browser delivery is
best effort; a reconnect retrieves the latest persisted positions via the same
FastAPI WebSocket. We do not claim exactly-once external broadcasts.
"""

import math
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import structlog
from geoalchemy2.elements import WKTElement
from pydantic import ValidationError
from sqlalchemy import select

from src.consumers.base import BaseKafkaConsumer
from src.database import AsyncSessionLocal
from src.events.models import GPSLocationEvent
from src.models import Route, Vehicle

logger = structlog.get_logger()


def validate_gps_event(raw: dict) -> GPSLocationEvent:
    """Reject unversioned, missing-id or physically impossible GPS events."""
    if raw.get("schema_version") != 1 or "event_id" not in raw:
        raise ValueError("GPS event must have schema_version=1 and event_id")
    try:
        event = GPSLocationEvent.model_validate(raw)
    except ValidationError as exc:
        raise ValueError("Invalid GPS event contract") from exc
    if event.timestamp.tzinfo is None:
        raise ValueError("GPS event time must have an explicit UTC offset")
    if event.timestamp.astimezone(UTC) > datetime.now(UTC) + timedelta(minutes=5):
        raise ValueError("GPS event time is in the future")
    numbers = [
        event.location.latitude,
        event.location.longitude,
        event.speed_kmh,
        event.heading,
        event.accuracy_m,
    ]
    if any(value is not None and not math.isfinite(value) for value in numbers):
        raise ValueError("GPS numeric fields must be finite")
    return event


class GPSLocationConsumer(BaseKafkaConsumer):
    """Update only known vehicles and broadcast accepted fresh GPS coordinates."""

    def __init__(self):
        super().__init__(topics=["gps.location"], group_id="gps-location-consumer")
        self.websocket_manager = None

    def set_websocket_manager(self, manager):
        self.websocket_manager = manager

    async def handle_message(
        self, topic: str, key: str | None, value: dict, timestamp: int
    ) -> None:
        if topic != "gps.location":
            raise ValueError("Unsupported GPS topic")
        event = validate_gps_event(value)
        observed = event.timestamp.astimezone(UTC).replace(tzinfo=None)

        # Lock position updates so duplicates or delayed telemetry cannot
        # overwrite a newer event when consumers rebalance/replay.
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(Vehicle).where(Vehicle.id == event.vehicle_id).with_for_update()
            )
            vehicle = result.scalar_one_or_none()
            if vehicle is None:
                raise ValueError("Unknown GPS vehicle")
            if vehicle.current_driver_id != event.driver_id:
                raise ValueError("GPS driver is not assigned to this vehicle")

            if event.route_id is not None:
                route = await session.get(Route, event.route_id)
                if (route is None or route.driver_id != event.driver_id
                    or route.vehicle_id != event.vehicle_id
                    or route.status != "in_progress" or route.started_at is None
                    or observed < route.started_at):
                    raise ValueError("GPS route is not actively dispatched for this driver/vehicle")

            previous = vehicle.last_gps_at
            if previous is not None and observed <= previous:
                # Duplicate or late event: no DB mutation or WebSocket signal.
                return

            latitude = Decimal(str(event.location.latitude))
            longitude = Decimal(str(event.location.longitude))
            vehicle.latitude = latitude
            vehicle.longitude = longitude
            vehicle.current_location = WKTElement(f"POINT({longitude} {latitude})", srid=4326)
            vehicle.last_gps_at = observed
            vehicle.last_gps_event_id = event.event_id
            vehicle.updated_at = datetime.now(UTC).replace(tzinfo=None)
            await session.commit()

        logger.info(
            "Validated GPS location persisted",
            vehicle_id=str(event.vehicle_id),
            event_id=str(event.event_id),
        )

        if self.websocket_manager is not None:
            from src.websocket_server import WebSocketMessage

            # No broadcast history is persisted; snapshot-on-reconnect is the
            # recovery contract. Socket failures must not trigger duplicate DB
            # writes or block the Kafka offset after DB commit.
            try:
                await self.websocket_manager.broadcast(
                    WebSocketMessage(
                        type="vehicle_update",
                        data={
                            "vehicle_id": str(event.vehicle_id),
                            "driver_id": str(event.driver_id),
                            "event_id": str(event.event_id),
                            "location": {
                                "latitude": event.location.latitude,
                                "longitude": event.location.longitude,
                            },
                            "speed_kmh": event.speed_kmh,
                            "heading": event.heading,
                            "observed_at": event.timestamp.astimezone(UTC).isoformat(),
                            "source": "kafka",
                        },
                    ),
                    channel="vehicles",
                )
            except (RuntimeError, OSError) as exc:
                logger.warning(
                    "Best-effort GPS broadcast unavailable",
                    error_type=type(exc).__name__,
                    vehicle_id=str(event.vehicle_id),
                )

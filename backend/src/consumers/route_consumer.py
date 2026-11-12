"""
Route events consumer.

Consumes route lifecycle events (started, stops completed) and updates database.
"""

from datetime import datetime, timezone
from uuid import UUID

import structlog
from sqlalchemy import select

from src.consumers.base import BaseKafkaConsumer
from src.database import AsyncSessionLocal
from src.models import Route, RouteStop

logger = structlog.get_logger()


class RouteEventsConsumer(BaseKafkaConsumer):
    """
    Consumes route-related events.

    Topics: routes.started, routes.stops

    Event formats:

    routes.started:
    {
        "route_id": "uuid",
        "driver_id": "uuid",
        "started_at": "2024-01-15T08:00:00Z",
        "first_stop_eta": "2024-01-15T08:30:00Z",
        "timestamp": "2024-01-15T08:00:00Z"
    }

    routes.stops:
    {
        "route_id": "uuid",
        "stop_id": "uuid",
        "order_id": "uuid",
        "driver_id": "uuid",
        "completed_at": "2024-01-15T09:15:00Z",
        "actual_service_time_minutes": 5,
        "next_stop_eta": "2024-01-15T09:45:00Z",
        "timestamp": "2024-01-15T09:15:00Z"
    }
    """

    def __init__(self):
        super().__init__(
            topics=["routes.started", "routes.stops"],
            group_id="route-events-consumer",
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
        """Process route event based on topic."""
        if topic == "routes.started":
            await self._handle_route_started(value)
        elif topic == "routes.stops":
            await self._handle_stop_completed(value)
        else:
            logger.warning("Unknown route topic", topic=topic)

    async def _handle_route_started(self, event_data: dict):
        """Handle route start event."""
        try:
            route_id = UUID(event_data["route_id"])

            # Route should already be updated by API
            # This is for additional processing/notifications
            async with AsyncSessionLocal() as session:
                stmt = select(Route).where(Route.id == route_id)
                result = await session.execute(stmt)
                route = result.scalar_one_or_none()

                if route and route.status == "in_progress":
                    logger.info(
                        "Route started",
                        route_id=str(route_id),
                        driver_id=str(route.driver_id),
                        stops=route.planned_stops,
                    )

                    # TODO: Start ETA tracking
                    # TODO: Enable real-time deviation alerts

            # Broadcast to WebSocket
            if self.websocket_manager:
                await self._broadcast_route_update(event_data, "route_started")

        except Exception as e:
            logger.error("Failed to process route started event", error=str(e))
            raise

    async def _handle_stop_completed(self, event_data: dict):
        """Handle stop completion event."""
        try:
            route_id = UUID(event_data["route_id"])
            stop_id = UUID(event_data["stop_id"])

            # Verify stop is marked complete
            async with AsyncSessionLocal() as session:
                stmt = select(RouteStop).where(RouteStop.id == stop_id)
                result = await session.execute(stmt)
                stop = result.scalar_one_or_none()

                if stop and stop.status == "completed":
                    logger.info(
                        "Stop completed",
                        route_id=str(route_id),
                        stop_id=str(stop_id),
                        sequence=stop.stop_sequence,
                    )

                    # TODO: Update route progress metrics
                    # TODO: Recalculate ETAs for remaining stops
                    # TODO: Check if route is complete (all stops done)

            # Broadcast to WebSocket
            if self.websocket_manager:
                await self._broadcast_route_update(event_data, "stop_completed")

        except Exception as e:
            logger.error("Failed to process stop completed event", error=str(e))
            raise

    async def _broadcast_route_update(self, event_data: dict, event_type: str):
        """Broadcast route update to WebSocket clients."""
        if not self.websocket_manager:
            return

        try:
            from src.websocket_server import WebSocketMessage

            message = WebSocketMessage(
                type=event_type,
                data={
                    "route_id": event_data["route_id"],
                    "driver_id": event_data.get("driver_id"),
                    "stop_id": event_data.get("stop_id"),
                    "order_id": event_data.get("order_id"),
                    "completed_at": event_data.get("completed_at"),
                    "next_stop_eta": event_data.get("next_stop_eta"),
                    "updated_at": event_data.get("timestamp", datetime.now(timezone.utc).isoformat()),
                },
            )

            sent_count = await self.websocket_manager.broadcast(message, channel="routes")
            logger.debug(
                f"Route {event_type} broadcasted",
                route_id=event_data["route_id"],
                clients=sent_count,
            )

        except Exception as e:
            logger.error("Failed to broadcast route update", error=str(e))

"""
GraphQL Subscriptions for real-time updates.
"""

import asyncio
from collections.abc import AsyncGenerator

import strawberry

from src.graphql.types import Location


@strawberry.type
class Subscription:
    """GraphQL Subscriptions for real-time data."""

    @strawberry.subscription
    async def driver_location_updates(
        self,
        driver_ids: list[strawberry.ID],
    ) -> AsyncGenerator[Location, None]:
        """
        Subscribe to driver location updates.

        In production, this would connect to Kafka or Redis pub/sub.
        For now, simulates periodic updates.
        """
        # In production, connect to WebSocket manager or Kafka consumer
        while True:
            # Simulate location update
            yield Location(
                latitude=40.7128 + (asyncio.get_event_loop().time() % 0.01),
                longitude=-74.0060 + (asyncio.get_event_loop().time() % 0.01),
            )
            await asyncio.sleep(5)  # Update every 5 seconds

    @strawberry.subscription
    async def order_status_updates(
        self,
        order_ids: list[strawberry.ID],
    ) -> AsyncGenerator[str, None]:
        """
        Subscribe to order status changes.
        """
        statuses = ["pending", "assigned", "in_transit", "arrived", "delivered"]
        index = 0

        while True:
            yield statuses[index % len(statuses)]
            index += 1
            await asyncio.sleep(10)

    @strawberry.subscription
    async def dashboard_updates(self) -> AsyncGenerator[str, None]:
        """
        Subscribe to dashboard metric updates.
        """
        while True:
            yield "dashboard_updated"
            await asyncio.sleep(30)

"""Unit tests for actual Kafka consumer handlers.

No Kafka broker is started here: the consumer receives a decoded event, while
SQLAlchemy session IO is mocked and explicit side effects are asserted.
Full broker/replay integration remains a separate acceptance gate.
"""
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from src.consumers.driver_consumer import DriverStatusConsumer
from src.consumers.gps_consumer import GPSLocationConsumer
from src.consumers.order_consumer import OrderEventsConsumer


def mock_db_session(found_record):
    """Create a context-managed async session with a deterministic query result."""
    session = AsyncMock()
    query_result = MagicMock()
    query_result.scalar_one_or_none.return_value = found_record
    session.execute.return_value = query_result

    context = MagicMock()
    context.__aenter__ = AsyncMock(return_value=session)
    context.__aexit__ = AsyncMock(return_value=None)
    return context, session


@pytest.mark.asyncio
async def test_gps_updates_vehicle_coordinates_and_commits():
    vehicle_id = uuid4()
    driver_id = uuid4()
    vehicle = MagicMock()
    context, session = mock_db_session(vehicle)

    event = {
        "vehicle_id": str(vehicle_id),
        "driver_id": str(driver_id),
        "location": {"latitude": 55.8642, "longitude": -4.2518},
        "timestamp": "2026-11-12T10:00:00Z",
    }

    with patch("src.consumers.gps_consumer.AsyncSessionLocal", return_value=context):
        await GPSLocationConsumer().handle_message("gps.location", None, event, 0)

    assert vehicle.latitude == Decimal("55.8642")
    assert vehicle.longitude == Decimal("-4.2518")
    session.execute.assert_awaited_once()
    session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_invalid_gps_payload_raises_instead_of_silently_passing():
    with pytest.raises(KeyError):
        await GPSLocationConsumer().handle_message("gps.location", None, {"invalid": "data"}, 0)


@pytest.mark.asyncio
async def test_driver_status_update_persists_new_state():
    driver_id = uuid4()
    driver = MagicMock()
    context, session = mock_db_session(driver)

    event = {
        "driver_id": str(driver_id),
        "previous_status": "available",
        "new_status": "on_route",
        "timestamp": "2026-11-12T10:00:00Z",
    }
    with patch("src.consumers.driver_consumer.AsyncSessionLocal", return_value=context):
        await DriverStatusConsumer().handle_message("drivers.status", None, event, 0)

    assert driver.status == "on_route"
    session.execute.assert_awaited_once()
    session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_existing_order_created_event_queries_record_without_duplicate_insert():
    order_id = uuid4()
    order = MagicMock()
    context, session = mock_db_session(order)

    event = {
        "order_id": str(order_id),
        "order_number": "DEMO-001",
        "timestamp": "2026-11-12T10:00:00Z",
    }
    with patch("src.consumers.order_consumer.AsyncSessionLocal", return_value=context):
        await OrderEventsConsumer().handle_message("orders.created", None, event, 0)

    session.execute.assert_awaited_once()
    session.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_cancelled_order_event_checks_persisted_cancel_status():
    order_id = uuid4()
    order = MagicMock()
    order.status = "cancelled"
    context, session = mock_db_session(order)

    event = {
        "order_id": str(order_id),
        "order_number": "DEMO-001",
        "reason": "Customer request",
        "timestamp": "2026-11-12T10:05:00Z",
    }
    with patch("src.consumers.order_consumer.AsyncSessionLocal", return_value=context):
        await OrderEventsConsumer().handle_message("orders.cancelled", None, event, 0)

    session.execute.assert_awaited_once()
    session.commit.assert_not_awaited()

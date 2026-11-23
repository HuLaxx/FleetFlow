"""Contract tests for FleetFlow's public Kafka event payload models.

These tests use only Pydantic and do not claim broker or consumer delivery.
"""
from datetime import datetime, timezone
from uuid import uuid4

import pytest
from pydantic import ValidationError

from src.events.models import (
    Address,
    EventType,
    GPSLocationEvent,
    Location,
    OrderCreatedEvent,
    OrderItem,
    TimeWindow,
)


def test_gps_event_has_unique_id_utc_timestamp_and_contract_version():
    first = GPSLocationEvent(
        driver_id=uuid4(),
        vehicle_id=uuid4(),
        location=Location(latitude=51.5072, longitude=-0.1276),
    )
    second = GPSLocationEvent(
        driver_id=first.driver_id,
        vehicle_id=first.vehicle_id,
        location=first.location,
    )
    assert first.schema_version == second.schema_version == 1
    assert first.event_type == EventType.DRIVER_LOCATION_UPDATED
    assert first.event_id != second.event_id
    assert first.timestamp.tzinfo is not None
    assert first.timestamp.utcoffset().total_seconds() == 0

    wire_event = first.model_dump(mode="json")
    assert wire_event["schema_version"] == 1
    assert wire_event["event_id"] == str(first.event_id)
    assert wire_event["timestamp"].endswith("Z")


def test_unsupported_schema_version_fails_closed():
    with pytest.raises(ValidationError):
        GPSLocationEvent(
            schema_version=2,
            driver_id=uuid4(),
            vehicle_id=uuid4(),
            location=Location(latitude=0, longitude=0),
        )


@pytest.mark.parametrize("latitude,longitude", [(91, 0), (-91, 0), (0, 181), (0, -181)])
def test_invalid_gps_coordinates_are_rejected(latitude, longitude):
    with pytest.raises(ValidationError):
        GPSLocationEvent(
            driver_id=uuid4(),
            vehicle_id=uuid4(),
            location=Location(latitude=latitude, longitude=longitude),
        )


def test_order_event_serializes_contract_fields_without_external_services():
    start = datetime(2026, 11, 12, 9, tzinfo=timezone.utc)
    event = OrderCreatedEvent(
        order_id=uuid4(),
        order_number="DEMO-001",
        customer_id=uuid4(),
        delivery_address=Address(
            street="Example Street",
            city="Glasgow",
            state="Scotland",
            postal_code="G1 1AA",
            country="GB",
            location=Location(latitude=55.8642, longitude=-4.2518),
        ),
        delivery_date="2026-11-12",
        time_window=TimeWindow(start=start, end=start.replace(hour=11)),
        items=[OrderItem(sku="BOOK", name="Sample parcel", quantity=1, weight_kg=1.0)],
        total_weight_kg=1.0,
    )
    payload = event.model_dump(mode="json")
    assert payload["schema_version"] == 1
    assert payload["event_type"] == EventType.ORDER_CREATED.value
    assert payload["time_window"]["start"] == "2026-11-12T09:00:00Z"

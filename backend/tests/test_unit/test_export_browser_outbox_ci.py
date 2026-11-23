"""No GPS analytics can be exported before broker ACK and DB commit."""

from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

import pytest

from src.events.models import GPSLocationEvent, Location
from scripts.export_browser_outbox_gps_ci import validate_persisted_browser_gps


def test_valid_same_event_and_reject_uncorroborated_gps():
    vehicle_id, driver_id = uuid4(), uuid4()
    event = GPSLocationEvent(
        vehicle_id=vehicle_id,
        driver_id=driver_id,
        timestamp=datetime(2026, 11, 20, tzinfo=UTC),
        location=Location(latitude=55.8, longitude=-4.2),
    )
    row = SimpleNamespace(
        id=event.event_id,
        topic="gps.location",
        status="published",
        message_key=str(vehicle_id),
        payload=event.model_dump(mode="json"),
    )
    vehicle = SimpleNamespace(
        id=vehicle_id,
        current_driver_id=driver_id,
        last_gps_event_id=event.event_id,
        last_gps_at=datetime(2026, 11, 20),
    )
    assert validate_persisted_browser_gps(row, vehicle, vehicle_id) == event
    row.status = "pending"
    with pytest.raises(ValueError, match="durably"):
        validate_persisted_browser_gps(row, vehicle, vehicle_id)
    row.status = "published"
    row.payload = {**row.payload, "event_id": str(uuid4())}
    with pytest.raises(ValueError, match="disagree"):
        validate_persisted_browser_gps(row, vehicle, vehicle_id)
    row.payload = event.model_dump(mode="json")
    vehicle.last_gps_event_id = uuid4()
    with pytest.raises(ValueError, match="disagree"):
        validate_persisted_browser_gps(row, vehicle, vehicle_id)

"""Local-only outbox to Parquet acceptance: export the same browser GPS event.

An authenticated, accepted browser GPS event is stored in PostgreSQL, broker
published and consumer-applied before this exporter reads it. Refuse anything
other than the ephemeral loopback fleetflow_test database.
"""

import argparse
import asyncio
import hashlib
import json
from pathlib import Path
from uuid import UUID

from sqlalchemy import select

from src.database import AsyncSessionLocal, engine
from src.events.models import GPSLocationEvent
from src.models import DispatchOutboxEvent, Vehicle


def validate_persisted_browser_gps(row, vehicle, expected_vehicle_id: UUID) -> GPSLocationEvent:
    if (
        row is None
        or vehicle is None
        or row.status != "published"
        or row.topic != "gps.location"
        or row.message_key != str(expected_vehicle_id)
    ):
        raise ValueError("Browser GPS is not durably published to the broker")
    if not isinstance(row.payload, dict):
        raise ValueError("Invalid outbox payload")
    if not {"schema_version", "event_id", "timestamp", "driver_id", "vehicle_id"} <= set(
        row.payload
    ):
        raise ValueError("Missing source identity fields")
    event = GPSLocationEvent.model_validate(row.payload)
    if (
        event.event_id != row.id
        or event.vehicle_id != expected_vehicle_id
        or vehicle.id != event.vehicle_id
        or vehicle.current_driver_id != event.driver_id
        or vehicle.last_gps_event_id != event.event_id
        or vehicle.last_gps_at is None
        or event.timestamp.tzinfo is None
    ):
        raise ValueError("Broker event and accepted PostGIS vehicle disagree")
    return event


async def export(expected_vehicle_id: UUID, output: Path) -> dict:
    if (
        engine.url.database != "fleetflow_test"
        or engine.url.host not in {"localhost", "127.0.0.1"}
    ):
        raise RuntimeError("Refusing non-test or remote GPS data")
    async with AsyncSessionLocal() as session:
        vehicle = await session.scalar(select(Vehicle).where(Vehicle.id == expected_vehicle_id))
        rows = (
            await session.scalars(
                select(DispatchOutboxEvent).where(
                    DispatchOutboxEvent.topic == "gps.location",
                    DispatchOutboxEvent.message_key == str(expected_vehicle_id),
                )
            )
        ).all()
        if len(rows) != 1:
            raise ValueError("Expected exactly one distinct browser GPS outbox event")
        event = validate_persisted_browser_gps(rows[0], vehicle, expected_vehicle_id)
        content = (
            json.dumps(event.model_dump(mode="json"), sort_keys=True, allow_nan=False) + "\n"
        ).encode("utf-8")
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("xb") as handle:
        handle.write(content)
    return {
        "scope": "disposable_browser_test_only",
        "vehicle_id": str(expected_vehicle_id),
        "driver_id": str(event.driver_id),
        "event_id": str(event.event_id),
        "source_sha256": hashlib.sha256(content).hexdigest(),
        "outbox_published": True,
        "postgis_consumer_accepted": True,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--vehicle-id", type=UUID, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = asyncio.run(export(args.vehicle_id, args.output))
        print(json.dumps(result, sort_keys=True))
    finally:
        asyncio.run(engine.dispose())


if __name__ == "__main__":
    main()

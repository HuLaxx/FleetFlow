"""Deterministic, explicitly synthetic GPS fixture for local lake/dbt review."""

import argparse
import json
from pathlib import Path


def create(path: Path) -> None:
    base = {
        "schema_version": 1,
        "event_type": "driver.location_updated",
        "driver_id": "55555555-5555-4555-8555-555555555555",
        "vehicle_id": "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
        "location": {"latitude": 55.8642, "longitude": -4.2518},
        "is_moving": True,
    }
    records = [
        dict(base, event_id="11111111-1111-4111-8111-111111111111",
             timestamp="2026-11-12T10:00:00Z", speed_kmh=10.0),
        dict(base, event_id="22222222-2222-4222-8222-222222222222",
             timestamp="2026-11-12T10:20:00Z", speed_kmh=20.0),
        dict(base, event_id="33333333-3333-4333-8333-333333333333",
             timestamp="2026-11-12T09:20:00Z", speed_kmh=30.0),
    ]
    # One duplicate is deliberate, should be counted but never become a fact.
    records.append(records[1])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(record, sort_keys=True) + "\n" for record in records),
        encoding="utf-8",
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Create synthetic historical GPS events")
    parser.add_argument("path", type=Path)
    create(parser.parse_args().path)

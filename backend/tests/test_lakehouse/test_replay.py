"""Reproducible local lake replay tests: actual Parquet, no network or AWS."""
import json
from datetime import UTC, datetime, timedelta
from uuid import UUID

import pyarrow.parquet as pq
import pytest

from src.lakehouse.replay import prepare_events, replay


def event(
    event_id: str, timestamp: str, *,
    speed: float = 25.0, latitude: float = 55.8642,
    schema_version: int = 1, event_type: str = "driver.location_updated"
) -> dict:
    return {
        "event_id": event_id,
        "schema_version": schema_version,
        "event_type": event_type,
        "timestamp": timestamp,
        "driver_id": "55555555-5555-4555-8555-555555555555",
        "vehicle_id": "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
        "location": {"latitude": latitude, "longitude": -4.2518},
        "speed_kmh": speed,
        "is_moving": True,
    }


def write_events(path, values):
    path.write_text(
        "".join(json.dumps(value, sort_keys=True) + "\n" for value in values),
        encoding="utf-8",
    )


def test_replay_materialises_partitioned_clean_and_curated_parquet(tmp_path):
    ids = [
        "11111111-1111-4111-8111-111111111111",
        "22222222-2222-4222-8222-222222222222",
        "33333333-3333-4333-8333-333333333333",
        "44444444-4444-4444-8444-444444444444",
    ]
    first = event(ids[0], "2026-11-12T10:00:00+00:00", speed=10)
    second = event(ids[1], "2026-11-12T10:20:00Z", speed=20)
    late = event(ids[2], "2026-11-12T09:30:00Z", speed=30)
    next_day = event(ids[3], "2026-11-13T01:15:00Z", speed=40)
    conflicting = dict(first, speed_kmh=99.0)
    invalid_latitude = event("55555555-5555-4555-8555-555555555555", "2026-11-12T10:30:00Z", latitude=91)
    naive_time = event("66666666-6666-4666-8666-666666666666", "2026-11-12T10:30:00")
    invalid_version = event("77777777-7777-4777-8777-777777777777", "2026-11-12T10:30:00Z", schema_version=2)
    invalid_type = event("88888888-8888-4888-8888-888888888888", "2026-11-12T10:30:00Z", event_type="order.created")

    source = tmp_path / "sample.jsonl"
    write_events(
        source,
        [first, second, late, next_day, second, conflicting,
         invalid_latitude, naive_time, invalid_version, invalid_type],
    )

    run_dir, manifest = replay(source, tmp_path / "lake")
    assert manifest["contract"] == "fleetflow.gps.v1"
    assert manifest["counts"] == {
        "accepted": 4, "duplicates": 1, "late": 1, "quarantined": 5,
    }
    assert len(manifest["artifacts"]) == 5
    assert (run_dir / "raw/events.jsonl").read_bytes() == source.read_bytes()

    day_12 = pq.read_table(run_dir / "clean/event_date=2026-11-12/telemetry.parquet").to_pylist()
    day_13 = pq.read_table(run_dir / "clean/event_date=2026-11-13/telemetry.parquet").to_pylist()
    assert len(day_12) == 3
    assert len(day_13) == 1
    assert sum(item["is_late"] for item in day_12) == 1
    assert len({item["event_id"] for item in day_12 + day_13}) == 4
    assert all(item["event_time"].tzinfo is not None for item in day_12 + day_13)

    mart = pq.read_table(run_dir / "curated/hourly_vehicle_telemetry.parquet").to_pylist()
    assert sum(item["event_count"] for item in mart) == 4
    by_hour = {item["hour_utc"].hour: item for item in mart}
    assert by_hour[10]["event_count"] == 2
    assert by_hour[10]["avg_speed_kmh"] == pytest.approx(15)
    assert by_hour[9]["late_event_count"] == 1
    assert by_hour[1]["last_latitude"] == pytest.approx(55.8642)

    quarantine = [
        json.loads(line)
        for line in (run_dir / "quarantine/rejected.jsonl").read_text().splitlines()
    ]
    assert len(quarantine) == 5
    assert any(item["reason"] == "conflicting_event_id" for item in quarantine)
    # No full rejected payloads are duplicated into the quarantine file.
    assert all("location" not in item for item in quarantine)


def test_replay_is_immutable_and_idempotent_across_retries(tmp_path):
    source = tmp_path / "sample.jsonl"
    write_events(
        source,
        [event("11111111-1111-4111-8111-111111111111", "2026-11-12T10:00:00Z")],
    )
    root = tmp_path / "lake"
    first_path, first_manifest = replay(source, root)
    original_parquet = (first_path / "curated/hourly_vehicle_telemetry.parquet").read_bytes()
    replayed_path, replayed_manifest = replay(source, root)

    assert replayed_path == first_path
    assert replayed_manifest == first_manifest
    assert (first_path / "curated/hourly_vehicle_telemetry.parquet").read_bytes() == original_parquet

    different_lateness_path, different_manifest = replay(
        source, root, allowed_lateness=timedelta(minutes=5)
    )
    assert different_lateness_path != first_path
    assert different_manifest["allowed_lateness_seconds"] == 300

    with source.open("a", encoding="utf-8") as handle:
        handle.write(
            json.dumps(
                event("22222222-2222-4222-8222-222222222222", "2026-11-12T10:05:00Z")
            )
            + "\n"
        )
    updated_path, updated_manifest = replay(source, root)
    assert updated_path != first_path
    assert updated_manifest["counts"]["accepted"] == 2
    assert (first_path / "curated/hourly_vehicle_telemetry.parquet").read_bytes() == original_parquet


def test_invalid_json_events_are_quarantined_not_promoted(tmp_path):
    source = tmp_path / "bad.jsonl"
    source.write_text('{broken-json\n[]\n{"event_id":"not-enough"}\n', encoding="utf-8")
    rows, rejects, counts = prepare_events(source)

    assert rows == []
    assert len(rejects) == 3
    assert counts == {"accepted": 0, "duplicates": 0, "late": 0, "quarantined": 3}

    path, manifest = replay(source, tmp_path / "lake")
    assert manifest["counts"]["accepted"] == 0
    assert pq.read_table(path / "clean/empty.parquet").num_rows == 0
    assert pq.read_table(path / "curated/hourly_vehicle_telemetry.parquet").num_rows == 0


def test_negative_lateness_is_rejected(tmp_path):
    source = tmp_path / "empty.jsonl"
    source.write_text("", encoding="utf-8")
    with pytest.raises(ValueError, match="allowed_lateness"):
        replay(source, tmp_path / "lake", allowed_lateness=timedelta(seconds=-1))

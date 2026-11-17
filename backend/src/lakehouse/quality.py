"""Independent reconciliation of an immutable GPS raw/clean/curated replay.

This checks the *persisted Parquet bytes*, not just the in-memory replay
counters. No cloud dependency or customer details are emitted in reports.
"""

import argparse
import json
import math
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from src.lakehouse.replay import sha256_file


def _rows(path: Path) -> list[dict[str, Any]]:
    import pyarrow.parquet as pq

    return pq.ParquetFile(path).read().to_pylist()


def audit_run(run_dir: Path) -> dict[str, Any]:
    """Fail closed for missing files, checksum drift or disagreeing layer counts."""
    root = Path(run_dir).resolve()
    manifest_path = root / "manifest.json"
    if not manifest_path.is_file():
        raise ValueError("GPS replay manifest missing")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("contract") != "fleetflow.gps.v1":
        raise ValueError("Unexpected GPS replay contract")
    artifacts = manifest.get("artifacts")
    digests = manifest.get("artifact_sha256")
    if not isinstance(artifacts, list) or not artifacts or not isinstance(digests, dict):
        raise ValueError("Incomplete GPS replay manifest")
    if len(artifacts) != len(set(artifacts)) or set(artifacts) != set(digests):
        raise ValueError("GPS replay manifest artifact mismatch")
    for relative in artifacts:
        if not isinstance(relative, str):
            raise TypeError("Invalid artifact path")
        path = (root / relative).resolve()
        if not path.is_relative_to(root) or not path.is_file():
            raise ValueError("Unsafe or missing replay artifact")
        if sha256_file(path) != digests[relative]:
            raise ValueError("Replay artifact checksum mismatch")
    raw = root / "raw/events.jsonl"
    quarantine = root / "quarantine/rejected.jsonl"
    curated = root / "curated/hourly_vehicle_telemetry.parquet"
    if not raw.is_file() or not quarantine.is_file() or not curated.is_file():
        raise ValueError("Replay is missing a mandatory layer")

    counts = manifest.get("counts")
    if not isinstance(counts, dict):
        raise TypeError("Missing manifest counts")
    if set(counts) != {"accepted", "duplicates", "late", "quarantined"}:
        raise ValueError("Unexpected manifest count keys")
    if any(not isinstance(x, int) or x < 0 for x in counts.values()):
        raise ValueError("Invalid replay counts")
    raw_count = sum(bool(line.strip()) for line in raw.read_text(encoding="utf-8").splitlines())
    reject_count = sum(
        bool(line.strip()) for line in quarantine.read_text(encoding="utf-8").splitlines()
    )
    if raw_count != counts["accepted"] + counts["duplicates"] + counts["quarantined"]:
        raise ValueError("Source reconciliation mismatch")
    if reject_count != counts["quarantined"]:
        raise ValueError("Quarantine reconciliation mismatch")

    partition_paths = [
        name for name in artifacts if name.startswith("clean/") and name.endswith(".parquet")
    ]
    if not partition_paths:
        raise ValueError("No clean Parquet artifacts")
    clean_rows: list[dict[str, Any]] = []
    event_ids: set[str] = set()
    for relative in partition_paths:
        if relative != "clean/empty.parquet" and not relative.startswith("clean/event_date="):
            raise ValueError("Unexpected clean partition name")
        for record in _rows(root / relative):
            event_id = record["event_id"]
            if event_id in event_ids:
                raise ValueError("Duplicate event ID in clean Parquet")
            event_ids.add(event_id)
            timestamp = record["event_time"]
            if not isinstance(timestamp, datetime) or timestamp.tzinfo is None:
                raise ValueError("Clean event timestamps must be timezone-aware")
            if timestamp.astimezone(UTC).date().isoformat() != record["event_date"]:
                raise ValueError("Clean event date mismatch")
            expected_path = f"clean/event_date={record['event_date']}/telemetry.parquet"
            if relative != expected_path:
                raise ValueError("Clean event placed in wrong partition")
            clean_rows.append(record)

    if len(clean_rows) != counts["accepted"]:
        raise ValueError("Clean accepted count mismatch")
    if sum(bool(record["is_late"]) for record in clean_rows) != counts["late"]:
        raise ValueError("Late event count mismatch")
    if "clean/empty.parquet" in partition_paths and clean_rows:
        raise ValueError("Non-empty data written to empty partition")

    by_hour: dict[tuple[str, datetime], list[dict[str, Any]]] = defaultdict(list)
    for record in clean_rows:
        hour = record["event_time"].replace(minute=0, second=0, microsecond=0)
        by_hour[(record["vehicle_id"], hour)].append(record)

    mart_rows = _rows(curated)
    actual_keys: set[tuple[str, datetime]] = set()
    for row in mart_rows:
        key = (row["vehicle_id"], row["hour_utc"])
        if key in actual_keys or key not in by_hour:
            raise ValueError("Curated group keys are missing, duplicated or unexpected")
        actual_keys.add(key)
        events = by_hour[key]
        speeds = [event["speed_kmh"] for event in events if event["speed_kmh"] is not None]
        expected_speed = sum(speeds) / len(speeds) if speeds else None
        if row["event_count"] != len(events):
            raise ValueError("Curated event counts disagree with clean Parquet")
        if row["late_event_count"] != sum(int(event["is_late"]) for event in events):
            raise ValueError("Curated late counts disagree with clean Parquet")
        if (expected_speed is None) != (row["avg_speed_kmh"] is None):
            raise ValueError("Curated speed availability mismatch")
        if expected_speed is not None and not math.isclose(
            expected_speed, row["avg_speed_kmh"], rel_tol=1e-10, abs_tol=1e-8
        ):
            raise ValueError("Curated average speed mismatch")
        latest = max(events, key=lambda record: record["event_time"])
        if row["last_event_time"] != latest["event_time"]:
            raise ValueError("Curated latest event time mismatch")
        for source, dest in (("latitude", "last_latitude"), ("longitude", "last_longitude")):
            if not math.isclose(latest[source], row[dest], abs_tol=1e-7):
                raise ValueError("Curated last coordinates mismatch")
    if actual_keys != set(by_hour):
        raise ValueError("Missing curated hourly vehicle groups")
    if sum(row["event_count"] for row in mart_rows) != counts["accepted"]:
        raise ValueError("Curated total does not reconcile")

    return {
        "run_key": manifest.get("run_key"),
        "source_rows": raw_count,
        "accepted_events": len(clean_rows),
        "duplicate_events": counts["duplicates"],
        "late_events": counts["late"],
        "quarantined_events": reject_count,
        "curated_hourly_groups": len(mart_rows),
        "status": "reconciled",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Verify immutable FleetFlow GPS layers")
    parser.add_argument("--run", required=True, type=Path)
    args = parser.parse_args()
    print(json.dumps(audit_run(args.run), sort_keys=True, indent=2))


if __name__ == "__main__":
    main()

"""Deterministic GPS event replay into a small, inspectable local data lake.

This is a *batch replay* of event snapshots, not a live Kafka consumer. Raw
bytes are preserved; accepted events and hourly aggregates are written as
partitioned Parquet. Input SHA-256 addresses immutable runs so repeated
backfills never silently overwrite historical evidence.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import tempfile
from collections import defaultdict
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from src.events.models import EventType, GPSLocationEvent


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _normalise_event(payload: dict[str, Any]) -> dict[str, Any]:
    required = ("event_id", "timestamp", "schema_version", "event_type")
    missing = [name for name in required if name not in payload]
    if missing:
        raise ValueError("required event metadata missing: " + ", ".join(missing))
    event = GPSLocationEvent.model_validate(payload)
    if event.event_type != EventType.DRIVER_LOCATION_UPDATED:
        raise ValueError("event_type must be driver.location_updated")
    if event.timestamp.tzinfo is None or event.timestamp.utcoffset() is None:
        raise ValueError("timestamp must include an explicit UTC offset")

    event_time = event.timestamp.astimezone(UTC)
    if not 2000 <= event_time.year <= 2100:
        raise ValueError("timestamp is outside the supported historical interval")

    return {
        "event_id": str(event.event_id),
        "vehicle_id": str(event.vehicle_id),
        "driver_id": str(event.driver_id),
        "schema_version": event.schema_version,
        "event_time": event_time,
        "latitude": event.location.latitude,
        "longitude": event.location.longitude,
        "speed_kmh": event.speed_kmh,
        "is_moving": event.is_moving,
        "event_date": event_time.date().isoformat(),
    }


def _canonical_digest(event: dict[str, Any]) -> str:
    serializable = {
        key: (value.isoformat() if isinstance(value, datetime) else value)
        for key, value in event.items()
    }
    return hashlib.sha256(
        json.dumps(serializable, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def prepare_events(
    input_file: Path, *, allowed_lateness: timedelta = timedelta(minutes=15)
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, int]]:
    """Validate in source order, deduplicate by event_id and flag late arrivals.

    A duplicate event_id with a *different* canonical payload is quarantined,
    not silently accepted. Late records remain in the historical analytics:
    they are flagged rather than discarded.
    """
    if allowed_lateness < timedelta(0):
        raise ValueError("allowed_lateness must not be negative")

    rows: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    seen: dict[str, str] = {}
    high_watermark: dict[str, datetime] = {}
    duplicates = 0
    late = 0

    with input_file.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                payload = json.loads(line)
                if not isinstance(payload, dict):
                    raise TypeError("JSON event must be an object")
                record = _normalise_event(payload)
            except (ValueError, TypeError, ValidationError) as error:
                rejected.append(
                    {"line": line_number, "reason": "invalid_contract", "detail": str(error)[:300]}
                )
                continue

            event_id = record["event_id"]
            checksum = _canonical_digest(record)
            if event_id in seen:
                if seen[event_id] == checksum:
                    duplicates += 1
                else:
                    rejected.append(
                        {
                            "line": line_number,
                            "event_id": event_id,
                            "reason": "conflicting_event_id",
                        }
                    )
                continue

            seen[event_id] = checksum
            vehicle_id = record["vehicle_id"]
            previous_max = high_watermark.get(vehicle_id)
            is_late = (
                previous_max is not None and record["event_time"] < previous_max - allowed_lateness
            )
            record["is_late"] = is_late
            record["source_line"] = line_number
            rows.append(record)
            if is_late:
                late += 1
            if previous_max is None or record["event_time"] > previous_max:
                high_watermark[vehicle_id] = record["event_time"]

    rows.sort(key=lambda row: (row["event_time"], row["vehicle_id"], row["event_id"]))
    return (
        rows,
        rejected,
        {
            "accepted": len(rows),
            "duplicates": duplicates,
            "late": late,
            "quarantined": len(rejected),
        },
    )


def _write_parquet(rows: list[dict[str, Any]], path: Path, schema: Any) -> None:
    # Imported lazily so contract-validation unit tests work without PyArrow.
    import pyarrow as pa
    import pyarrow.parquet as pq

    path.parent.mkdir(parents=True, exist_ok=True)
    table = pa.Table.from_pylist(rows, schema=schema)
    pq.write_table(table, path, compression="zstd")


def _build_parquet(staging: Path, rows: list[dict[str, Any]]) -> list[str]:
    import pyarrow as pa

    clean_schema = pa.schema(
        [
            ("event_id", pa.string()),
            ("vehicle_id", pa.string()),
            ("driver_id", pa.string()),
            ("schema_version", pa.int16()),
            ("event_time", pa.timestamp("us", tz="UTC")),
            ("latitude", pa.float64()),
            ("longitude", pa.float64()),
            ("speed_kmh", pa.float64()),
            ("is_moving", pa.bool_()),
            ("event_date", pa.string()),
            ("is_late", pa.bool_()),
            ("source_line", pa.int64()),
        ]
    )
    partitions: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        partitions[row["event_date"]].append(row)

    paths = []
    for day in sorted(partitions):
        relative = "clean/event_date=" + day + "/telemetry.parquet"
        _write_parquet(partitions[day], staging / relative, clean_schema)
        paths.append(relative)

    # Always materialise an explicit schema even when the source has no valid events.
    if not partitions:
        relative = "clean/empty.parquet"
        _write_parquet([], staging / relative, clean_schema)
        paths.append(relative)

    hourly: dict[tuple[str, datetime], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        event_time = row["event_time"]
        hour = event_time.replace(minute=0, second=0, microsecond=0)
        hourly[(row["vehicle_id"], hour)].append(row)

    marts = []
    for (vehicle_id, hour), events in sorted(hourly.items()):
        speeds = [event["speed_kmh"] for event in events if event["speed_kmh"] is not None]
        most_recent = max(events, key=lambda event: event["event_time"])
        marts.append(
            {
                "vehicle_id": vehicle_id,
                "hour_utc": hour,
                "event_count": len(events),
                "late_event_count": sum(int(event["is_late"]) for event in events),
                "avg_speed_kmh": sum(speeds) / len(speeds) if speeds else None,
                "last_event_time": most_recent["event_time"],
                "last_latitude": most_recent["latitude"],
                "last_longitude": most_recent["longitude"],
            }
        )

    curated_schema = pa.schema(
        [
            ("vehicle_id", pa.string()),
            ("hour_utc", pa.timestamp("us", tz="UTC")),
            ("event_count", pa.int64()),
            ("late_event_count", pa.int64()),
            ("avg_speed_kmh", pa.float64()),
            ("last_event_time", pa.timestamp("us", tz="UTC")),
            ("last_latitude", pa.float64()),
            ("last_longitude", pa.float64()),
        ]
    )
    relative = "curated/hourly_vehicle_telemetry.parquet"
    _write_parquet(marts, staging / relative, curated_schema)
    paths.append(relative)
    return paths


def replay(
    input_file: Path,
    output_root: Path,
    *,
    allowed_lateness: timedelta = timedelta(minutes=15),
) -> tuple[Path, dict[str, Any]]:
    """Rebuild an immutable lake snapshot; never overwrite another source run."""
    input_file = Path(input_file).resolve()
    output_root = Path(output_root).resolve()
    if not input_file.is_file():
        raise FileNotFoundError(input_file)
    if allowed_lateness < timedelta(0):
        raise ValueError("allowed_lateness must not be negative")

    source_digest = sha256_file(input_file)
    config_key = f"{source_digest}:{int(allowed_lateness.total_seconds())}"
    run_key = hashlib.sha256(config_key.encode("ascii")).hexdigest()
    run_dir = output_root / "runs" / run_key
    if run_dir.exists():
        manifest_path = run_dir / "manifest.json"
        if not manifest_path.is_file():
            raise RuntimeError("Existing replay directory is incomplete; refusing to overwrite")
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if manifest.get("source_sha256") != source_digest or manifest.get("run_key") != run_key:
            raise RuntimeError("Existing run manifest does not match source digest")
        artifacts = manifest.get("artifacts", [])
        checksums = manifest.get("artifact_sha256", {})
        if not artifacts or set(artifacts) != set(checksums):
            raise RuntimeError("Existing run manifest is missing artifact checksums")
        for relative in artifacts:
            artifact = run_dir / relative
            if not artifact.is_file():
                raise RuntimeError("Existing run has missing output artifacts")
            if sha256_file(artifact) != checksums[relative]:
                raise RuntimeError("Existing run artifact failed integrity verification")
        return run_dir, manifest

    output_root.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=".fleetflow-replay-", dir=output_root))
    try:
        raw_path = staging / "raw" / "events.jsonl"
        raw_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(input_file, raw_path)

        rows, rejects, counts = prepare_events(raw_path, allowed_lateness=allowed_lateness)
        artifacts = ["raw/events.jsonl"]
        artifacts.extend(_build_parquet(staging, rows))

        quarantine = staging / "quarantine" / "rejected.jsonl"
        quarantine.parent.mkdir(parents=True, exist_ok=True)
        quarantine.write_text(
            "".join(json.dumps(record, sort_keys=True) + "\n" for record in rejects),
            encoding="utf-8",
        )
        artifacts.append("quarantine/rejected.jsonl")

        manifest = {
            "contract": "fleetflow.gps.v1",
            "source_sha256": source_digest,
            "run_key": run_key,
            "allowed_lateness_seconds": int(allowed_lateness.total_seconds()),
            "counts": counts,
            "artifacts": sorted(artifacts),
            "artifact_sha256": {
                relative: sha256_file(staging / relative) for relative in sorted(artifacts)
            },
        }
        (staging / "manifest.json").write_text(
            json.dumps(manifest, sort_keys=True, indent=2) + "\n",
            encoding="utf-8",
        )
        run_dir.parent.mkdir(parents=True, exist_ok=True)
        # The content-and-configuration-addressed output makes retries/backfills reproducible.
        staging.rename(run_dir)
        return run_dir, manifest
    finally:
        if staging.exists():
            shutil.rmtree(staging)


def main() -> None:
    parser = argparse.ArgumentParser(description="Replay FleetFlow GPS events to local Parquet")
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--lateness-minutes", type=int, default=15)
    args = parser.parse_args()
    run_dir, manifest = replay(
        args.input,
        args.output,
        allowed_lateness=timedelta(minutes=args.lateness_minutes),
    )
    print(json.dumps({"run_dir": str(run_dir), **manifest}, indent=2))


if __name__ == "__main__":
    main()

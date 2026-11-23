"""Inspect a replay run, independently reconcile clean Parquet against curated marts.

A manifest is a *claim*, not proof: verify all artifact hashes, row IDs,
partition dates, UTC event times, hours, late counts and numeric aggregates.
Designed for small local fixtures; does not claim scalable distributed SQL.
"""

from __future__ import annotations

import argparse
import json
import math
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from src.lakehouse.replay import sha256_file


class ReconciliationError(ValueError):
    """Lake run cannot be trusted for analysis."""


def _artifact(run_dir: Path, relative: str) -> Path:
    path = Path(relative)
    if path.is_absolute() or ".." in path.parts or not path.parts:
        raise ReconciliationError("Unsafe artifact path in manifest")
    resolved = (run_dir / path).resolve()
    if not resolved.is_relative_to(run_dir.resolve()):
        raise ReconciliationError("Artifact escapes the replay directory")
    return resolved


def _nonneg_int(value: Any, field: str) -> int:
    if type(value) is not int or value < 0:
        raise ReconciliationError(f"Invalid manifest count: {field}")
    return value


def _close(actual: Any, expected: Any, field: str) -> None:
    if expected is None:
        if actual is not None:
            raise ReconciliationError(f"Non-null {field} without observed values")
        return
    if actual is None or not math.isfinite(float(actual)):
        raise ReconciliationError(f"Missing/nonfinite {field}")
    if not math.isclose(float(actual), float(expected), abs_tol=1e-8, rel_tol=1e-10):
        raise ReconciliationError(f"Curated {field} differs from clean telemetry")


def reconcile(run_dir: Path) -> dict[str, Any]:
    """Return evidence counts or fail closed on inconsistent parquet/manifest."""
    import pyarrow.parquet as pq

    run_dir = Path(run_dir).resolve()
    manifest_file = run_dir / "manifest.json"
    if not manifest_file.is_file():
        raise ReconciliationError("Missing replay manifest")
    manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
    if manifest.get("contract") != "fleetflow.gps.v1":
        raise ReconciliationError("Unsupported lake replay contract")
    counts = manifest.get("counts")
    if not isinstance(counts, dict):
        raise ReconciliationError("Missing manifest counts")
    expected = {
        field: _nonneg_int(counts.get(field), field)
        for field in ("accepted", "duplicates", "late", "quarantined")
    }
    artifacts = manifest.get("artifacts")
    hashes = manifest.get("artifact_sha256")
    if not isinstance(artifacts, list) or not isinstance(hashes, dict):
        raise ReconciliationError("Incomplete manifest artifact inventory")
    if len(artifacts) != len(set(artifacts)) or set(artifacts) != set(hashes):
        raise ReconciliationError("Duplicate or missing manifest artifacts")
    if "raw/events.jsonl" not in artifacts or "quarantine/rejected.jsonl" not in artifacts:
        raise ReconciliationError("Missing raw or quarantine evidence")
    mart = "curated/hourly_vehicle_telemetry.parquet"
    if mart not in artifacts:
        raise ReconciliationError("Missing curated hourly mart")

    for relative in artifacts:
        path = _artifact(run_dir, relative)
        if not path.is_file() or sha256_file(path) != hashes[relative]:
            raise ReconciliationError(f"Missing/tampered artifact: {relative}")

    if sha256_file(run_dir / "raw/events.jsonl") != manifest.get("source_sha256"):
        raise ReconciliationError("Raw input differs from manifest source")
    clean_files = sorted(
        relative
        for relative in artifacts
        if relative.startswith("clean/") and relative.endswith(".parquet")
    )
    if not clean_files:
        raise ReconciliationError("No clean parquet partitions")

    clean = []
    for relative in clean_files:
        path = _artifact(run_dir, relative)
        # read_table() can infer hive partition columns from parent paths;
        # ParquetFile.read() reads *only* the physical columns saved in the file.
        rows = pq.ParquetFile(path).read().to_pylist()
        if relative == "clean/empty.parquet":
            if rows:
                raise ReconciliationError("Nonempty empty-partition marker")
            continue
        if not relative.startswith("clean/event_date=") or not relative.endswith(
            "/telemetry.parquet"
        ):
            raise ReconciliationError("Unexpected clean partition layout")
        partition_day = relative.split("/")[1].removeprefix("event_date=")
        for row in rows:
            timestamp = row["event_time"]
            if not isinstance(timestamp, datetime) or timestamp.tzinfo is None:
                raise ReconciliationError("Clean event lacks a timezone")
            if timestamp.utcoffset().total_seconds() != 0:
                raise ReconciliationError("Clean event time is not UTC")
            if row["event_date"] != timestamp.astimezone(UTC).date().isoformat():
                raise ReconciliationError("Event date does not match UTC timestamp")
            if row["event_date"] != partition_day:
                raise ReconciliationError("Event stored in incorrect date partition")
            if not math.isfinite(row["latitude"]) or not math.isfinite(row["longitude"]):
                raise ReconciliationError("Clean coordinates are not finite")
            if not (-90 <= row["latitude"] <= 90 and -180 <= row["longitude"] <= 180):
                raise ReconciliationError("Clean coordinates exceed geographic bounds")
            if row["speed_kmh"] is not None and (
                not math.isfinite(row["speed_kmh"]) or row["speed_kmh"] < 0
            ):
                raise ReconciliationError("Invalid clean speed")
        clean.extend(rows)

    if len(clean) != expected["accepted"]:
        raise ReconciliationError("Clean row count disagrees with manifest")
    if len({row["event_id"] for row in clean}) != len(clean):
        raise ReconciliationError("Duplicate IDs present in clean telemetry")
    if sum(int(row["is_late"]) for row in clean) != expected["late"]:
        raise ReconciliationError("Late event count disagrees with manifest")
    if expected["accepted"] == 0 and clean_files != ["clean/empty.parquet"]:
        raise ReconciliationError("Empty runs must use the empty-partition marker")

    quarantine = [
        json.loads(line)
        for line in (run_dir / "quarantine/rejected.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if len(quarantine) != expected["quarantined"]:
        raise ReconciliationError("Quarantine count disagrees with manifest")

    groups = defaultdict(list)
    for row in clean:
        hour = row["event_time"].replace(minute=0, second=0, microsecond=0)
        groups[(row["vehicle_id"], hour)].append(row)
    curated = pq.ParquetFile(_artifact(run_dir, mart)).read().to_pylist()
    observed = {}
    for row in curated:
        key = (row["vehicle_id"], row["hour_utc"])
        if key in observed:
            raise ReconciliationError("Duplicate vehicle/hour in curated mart")
        observed[key] = row
    if set(groups) != set(observed):
        raise ReconciliationError("Curated vehicle/hour keys do not match clean events")
    for key, events in groups.items():
        item = observed[key]
        speeds = [e["speed_kmh"] for e in events if e["speed_kmh"] is not None]
        latest = max(events, key=lambda e: (e["event_time"], e["event_id"]))
        if item["event_count"] != len(events):
            raise ReconciliationError("Curated event count does not match clean data")
        if item["late_event_count"] != sum(int(e["is_late"]) for e in events):
            raise ReconciliationError("Curated late count does not match clean data")
        if item["last_event_time"] != latest["event_time"]:
            raise ReconciliationError("Curated latest event time does not match clean data")
        _close(
            item["avg_speed_kmh"], sum(speeds) / len(speeds) if speeds else None, "avg_speed_kmh"
        )
        _close(item["last_latitude"], latest["latitude"], "last_latitude")
        _close(item["last_longitude"], latest["longitude"], "last_longitude")

    return {
        "status": "reconciled",
        "contract": manifest["contract"],
        "run_key": manifest["run_key"],
        "accepted": len(clean),
        "duplicates": expected["duplicates"],
        "late": expected["late"],
        "quarantined": len(quarantine),
        "clean_partitions": len(clean_files),
        "curated_vehicle_hours": len(curated),
        "verified_artifacts": len(artifacts),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Reconcile local GPS clean/curated Parquet")
    parser.add_argument("run_dir", type=Path)
    args = parser.parse_args()
    print(json.dumps(reconcile(args.run_dir), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

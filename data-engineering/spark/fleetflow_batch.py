"""FleetFlow Spark batch transform for accepted GPS Parquet replay events.

Input is the already-validated immutable clean Parquet from
backend/src/lakehouse/replay.py. This is a real distributed DataFrame
transformation, not a Kafka streaming job or a replacement for source validation.
"""
from __future__ import annotations

import re
import hashlib
import json
from pathlib import Path
from typing import Any

from pyspark.sql import DataFrame, Window
from pyspark.sql import functions as F

REQUIRED = {
    "event_id", "vehicle_id", "event_time", "latitude", "longitude",
    "speed_kmh", "is_late",
}


def hourly_vehicle_facts(events: DataFrame, run_key: str) -> DataFrame:
    """One observed UTC vehicle/hour fact per run.

    Reject invalid records and duplicated event IDs. Deterministically select
    the latest observed location, breaking equal-time ties by event UUID.
    Never fabricate tracking, availability, distance or delivery metrics.
    """
    if not re.fullmatch(r"[0-9a-f]{64}", run_key):
        raise ValueError("run_key must be the 64-character replay manifest digest")
    missing = REQUIRED - set(events.columns)
    if missing:
        raise ValueError(f"clean GPS input is missing columns: {sorted(missing)}")

    invalid = events.filter(
        F.col("event_id").isNull()
        | F.col("vehicle_id").isNull()
        | F.col("event_time").isNull()
        | F.col("latitude").isNull()
        | F.col("longitude").isNull()
        | F.isnan("latitude")
        | F.isnan("longitude")
        | (F.abs(F.col("latitude")) > 90)
        | (F.abs(F.col("longitude")) > 180)
        | F.col("is_late").isNull()
        | (F.col("speed_kmh").isNotNull() & (F.isnan("speed_kmh") | (F.col("speed_kmh") < 0)))
    )
    if invalid.limit(1).count():
        raise ValueError("clean GPS input failed the strict Spark validation gate")
    if events.groupBy("event_id").count().filter(F.col("count") > 1).limit(1).count():
        raise ValueError("duplicate event_id in immutable clean GPS input")

    prepared = events.withColumn("hour_utc", F.date_trunc("hour", F.col("event_time")))
    keys = ["vehicle_id", "hour_utc"]
    stats = prepared.groupBy(*keys).agg(
        F.count(F.lit(1)).cast("long").alias("event_count"),
        F.sum(F.col("is_late").cast("long")).alias("late_event_count"),
        F.avg("speed_kmh").alias("avg_speed_kmh"),
    )
    ordering = Window.partitionBy(*keys).orderBy(
        F.col("event_time").desc(), F.col("event_id").desc()
    )
    last = (
        prepared.withColumn("_rn", F.row_number().over(ordering))
        .filter(F.col("_rn") == 1)
        .select(
            *keys,
            F.col("event_time").alias("last_event_time"),
            F.col("latitude").alias("last_latitude"),
            F.col("longitude").alias("last_longitude"),
        )
    )
    return (
        stats.join(last, on=keys, how="inner")
        .withColumn("run_key", F.lit(run_key))
        .select(
            "run_key", "vehicle_id", "hour_utc", "event_count",
            "late_event_count", "avg_speed_kmh", "last_event_time",
            "last_latitude", "last_longitude",
        )
    )


def verified_clean_parquet(manifest_path: Path) -> tuple[dict[str, Any], list[str]]:
    """Verify the replay manifest and every referenced artifact before Spark reads.

    Requires the original run directory layout with manifest.json at its root.
    Verifies bytes (integrity), NOT the authenticity of the manifest's creator.
    """
    manifest_path = Path(manifest_path).resolve()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("contract") != "fleetflow.gps.v1":
        raise ValueError("unrecognised replay manifest contract")
    if not re.fullmatch(r"[0-9a-f]{64}", str(manifest.get("run_key", ""))):
        raise ValueError("invalid replay run key")
    artifacts = manifest.get("artifacts")
    checksums = manifest.get("artifact_sha256")
    if not isinstance(artifacts, list) or not artifacts or not isinstance(checksums, dict):
        raise ValueError("incomplete source manifest")
    if len(artifacts) != len(set(artifacts)) or set(artifacts) != set(checksums):
        raise ValueError("duplicate or inconsistent manifest artifacts")
    root = manifest_path.parent
    clean = []
    for relative in artifacts:
        if not isinstance(relative, str) or Path(relative).is_absolute():
            raise ValueError("unsafe artifact location")
        target = (root / relative).resolve()
        if not target.is_relative_to(root) or not target.is_file():
            raise ValueError("missing or escaping replay artifact")
        expected = checksums[relative]
        if not isinstance(expected, str) or not re.fullmatch(r"[0-9a-f]{64}", expected):
            raise ValueError("invalid artifact digest")
        hasher = hashlib.sha256()
        with target.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                hasher.update(chunk)
        if hasher.hexdigest() != expected:
            raise ValueError("replay artifact integrity failure")
        if relative.startswith("clean/") and relative.endswith(".parquet"):
            clean.append(str(target))
    if not clean:
        raise ValueError("manifest contains no validated clean Parquet files")
    return manifest, clean

"""FleetFlow Spark batch transform for accepted GPS Parquet replay events.

Input is the already-validated immutable clean Parquet from
backend/src/lakehouse/replay.py. This is a real distributed DataFrame
transformation, not a Kafka streaming job or a replacement for source validation.
"""
from __future__ import annotations

import re

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

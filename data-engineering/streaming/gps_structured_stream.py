"""Spark Structured Streaming: Kafka `gps.location` -> validated, de-duplicated Parquet.

Contract: the backend's GPSLocationEvent v1 (schema_version=1, event_id,
ISO-8601 timestamp with an explicit UTC offset, location.latitude/longitude).

Guarantees, and how they are tested in CI against a real Kafka broker:
  * Exactly-once output: Spark's file sink plus a checkpoint. Re-running with
    no new data writes nothing new.
  * De-duplication: dropDuplicatesWithinWatermark on event_id drops duplicates
    inside a batch and replays across runs while the id is in state.
  * Late data: events older than the event-time watermark (max seen event time
    minus WATERMARK) are dropped.
  * Invalid events go to a separate quarantine sink instead of failing the job.

Run (needs Java; the spark-sql-kafka package is fetched on first use):
    PYTHONPATH=data-engineering python -m streaming.gps_structured_stream --bootstrap 127.0.0.1:9092
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from pyspark.sql import DataFrame, SparkSession
from pyspark.sql import functions as F
from pyspark.sql.types import (
    BooleanType, DoubleType, IntegerType, StringType, StructField, StructType,
)

SPARK_KAFKA_PACKAGE = "org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.3"
TOPIC = "gps.location"
WATERMARK = "10 minutes"

LOCATION = StructType([
    StructField("latitude", DoubleType()),
    StructField("longitude", DoubleType()),
])
GPS_EVENT_V1 = StructType([
    StructField("event_type", StringType()),
    StructField("schema_version", IntegerType()),
    StructField("event_id", StringType()),
    StructField("timestamp", StringType()),
    StructField("driver_id", StringType()),
    StructField("vehicle_id", StringType()),
    StructField("route_id", StringType()),
    StructField("location", LOCATION),
    StructField("speed_kmh", DoubleType()),
    StructField("heading", DoubleType()),
    StructField("accuracy_m", DoubleType()),
    StructField("is_moving", BooleanType()),
])


def spark_session(
    app: str = "fleetflow-gps-stream", master: str = "local[2]", *, kafka: bool = True
) -> SparkSession:
    builder = SparkSession.builder.appName(app).master(master)
    if kafka:
        builder = builder.config("spark.jars.packages", SPARK_KAFKA_PACKAGE)
    return (
        builder.config("spark.sql.session.timeZone", "UTC")
        .config("spark.sql.shuffle.partitions", "4")
        .config("spark.ui.enabled", "false")
        .getOrCreate()
    )


def parse(raw: DataFrame) -> DataFrame:
    """Kafka rows -> typed events with an `is_valid` flag and a rejection reason."""
    parsed = raw.select(
        F.col("value").cast("string").alias("raw_json"),
        F.col("partition").alias("kafka_partition"),
        F.col("offset").alias("kafka_offset"),
        F.from_json(F.col("value").cast("string"), GPS_EVENT_V1).alias("e"),
    ).select("raw_json", "kafka_partition", "kafka_offset", "e.*")
    has_offset = F.col("timestamp").rlike(r"(Z|[+-]\d{2}:\d{2})$")
    event_time = F.to_timestamp("timestamp")
    lat, lon = F.col("location.latitude"), F.col("location.longitude")
    reason = (
        F.when(F.col("schema_version").isNull() | (F.col("schema_version") != 1), "schema_version")
        .when(F.col("event_id").isNull(), "missing_event_id")
        .when(~has_offset | event_time.isNull(), "timestamp_without_utc_offset")
        .when(F.col("vehicle_id").isNull(), "missing_vehicle_id")
        .when(lat.isNull() | lon.isNull() | (F.abs(lat) > 90) | (F.abs(lon) > 180), "location_out_of_range")
        .when(F.col("speed_kmh") < 0, "negative_speed")
    )
    return parsed.withColumn("event_time", event_time).withColumn("rejection_reason", reason)


def silver(events: DataFrame) -> DataFrame:
    valid = events.where(F.col("rejection_reason").isNull())
    if events.isStreaming:
        deduped = valid.withWatermark("event_time", WATERMARK).dropDuplicatesWithinWatermark(
            ["event_id"]
        )
    else:  # Spark only allows the watermark-bounded variant on streams.
        deduped = valid.dropDuplicates(["event_id"])
    return (
        deduped
        .select(
            "event_id", "event_time", "vehicle_id", "driver_id", "route_id",
            F.col("location.latitude").alias("latitude"),
            F.col("location.longitude").alias("longitude"),
            "speed_kmh", "heading", "accuracy_m", "is_moving",
            "kafka_partition", "kafka_offset",
            F.to_date("event_time").alias("event_date"),
        )
    )


def quarantine(events: DataFrame) -> DataFrame:
    return events.where(F.col("rejection_reason").isNotNull()).select(
        "raw_json", "rejection_reason", "kafka_partition", "kafka_offset"
    )


def run_available_now(spark: SparkSession, bootstrap: str, out_dir: Path, topic: str = TOPIC) -> dict:
    """Process everything currently in the topic, then stop. Safe to call repeatedly."""
    raw = (
        spark.readStream.format("kafka")
        .option("kafka.bootstrap.servers", bootstrap)
        .option("subscribe", topic)
        .option("startingOffsets", "earliest")
        .option("failOnDataLoss", "true")
        .load()
    )
    events = parse(raw)
    queries = {
        "silver": silver(events).writeStream.format("parquet")
        .option("path", str(out_dir / "silver"))
        .option("checkpointLocation", str(out_dir / "_checkpoints" / "silver"))
        .partitionBy("event_date").outputMode("append")
        .trigger(availableNow=True).start(),
        "quarantine": quarantine(events).writeStream.format("parquet")
        .option("path", str(out_dir / "quarantine"))
        .option("checkpointLocation", str(out_dir / "_checkpoints" / "quarantine"))
        .outputMode("append").trigger(availableNow=True).start(),
    }
    summary = {}
    for name, query in queries.items():
        query.awaitTermination()
        progress = [p for p in query.recentProgress if p.get("numInputRows", 0) > 0]
        summary[name] = {
            "input_rows": sum(p["numInputRows"] for p in progress),
            "batches": len(progress),
            "processed_rows_per_second": max(
                (p.get("processedRowsPerSecond") or 0.0 for p in progress), default=0.0
            ),
            "watermark": (query.lastProgress or {}).get("eventTime", {}).get("watermark"),
        }
    return summary


def count_parquet(spark: SparkSession, path: Path) -> int:
    return spark.read.parquet(str(path)).count() if path.exists() else 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--bootstrap", default="127.0.0.1:9092")
    parser.add_argument("--topic", default=TOPIC)
    parser.add_argument("--out", type=Path, default=Path("data/streaming"))
    args = parser.parse_args(argv)
    spark = spark_session()
    summary = run_available_now(spark, args.bootstrap, args.out, args.topic)
    summary["silver_rows_total"] = count_parquet(spark, args.out / "silver")
    summary["quarantine_rows_total"] = count_parquet(spark, args.out / "quarantine")
    print(json.dumps(summary, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

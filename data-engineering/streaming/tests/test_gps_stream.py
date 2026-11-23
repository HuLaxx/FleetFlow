"""GPS Structured Streaming tests.

Offline tests run the same parse/silver logic on batch DataFrames. The
integration test (set KAFKA_BOOTSTRAP) runs the real streaming job against a
real Kafka broker: duplicates, late data, replays and an idempotent re-run.
"""
import json
import os
import uuid

import pytest

from streaming.gps_structured_stream import count_parquet, parse, quarantine, run_available_now, silver
from streaming.synthetic_gps import gps_event, invalid_events, publish

KAFKA = os.getenv("KAFKA_BOOTSTRAP")


def kafka_like(spark, events):
    rows = [(json.dumps(e).encode(), 0, i) for i, e in enumerate(events)]
    return spark.createDataFrame(rows, "value binary, partition int, offset long")


def test_rejects_each_invalid_kind_with_a_reason(spark):
    events = [gps_event(i, i) for i in range(5)] + invalid_events(100, 4)
    parsed = parse(kafka_like(spark, events))
    reasons = {r["rejection_reason"] for r in quarantine(parsed).collect()}
    assert reasons == {"schema_version", "location_out_of_range", "timestamp_without_utc_offset", "missing_event_id"}
    assert silver(parsed).count() == 5


def test_duplicate_event_ids_are_dropped(spark):
    events = [gps_event(i, i) for i in range(20)] + [gps_event(i, i) for i in range(5)]
    assert silver(parse(kafka_like(spark, events))).count() == 20


def test_silver_columns_are_typed_and_partitioned_by_date(spark):
    row = silver(parse(kafka_like(spark, [gps_event(1, 30)]))).collect()[0]
    assert str(row["event_date"]) == "2026-11-01"
    assert -90 <= row["latitude"] <= 90 and row["speed_kmh"] >= 0


@pytest.mark.skipif(not KAFKA, reason="set KAFKA_BOOTSTRAP to run against a real broker")
def test_streaming_exactly_once_dedupe_and_late_data(spark, tmp_path):
    topic = f"gps.location.test.{uuid.uuid4().hex[:8]}"
    # Run 1: 1,000 valid events over 50 minutes, 100 in-batch duplicates, 20 invalid.
    batch1 = [gps_event(i, i * 0.05) for i in range(1000)]
    batch1 += [gps_event(i, i * 0.05) for i in range(0, 1000, 10)]
    batch1 += invalid_events(50_000, 20)
    publish(spark, KAFKA, topic, batch1)
    first = run_available_now(spark, KAFKA, tmp_path, topic)
    assert first["silver"]["input_rows"] == 1120
    assert count_parquet(spark, tmp_path / "silver") == 1000
    assert count_parquet(spark, tmp_path / "quarantine") == 20

    # Run 2, no new data: exactly-once file sink writes nothing new.
    again = run_available_now(spark, KAFKA, tmp_path, topic)
    assert again["silver"]["input_rows"] == 0
    assert count_parquet(spark, tmp_path / "silver") == 1000

    # Run 3: 200 new events, 50 late events (30 minutes before the watermark),
    # and 30 replays of recent run-1 events that are still in dedupe state.
    batch2 = [gps_event(2000 + i, 60 + i * 0.05) for i in range(200)]
    batch2 += [gps_event(3000 + i, 10 + i * 0.01) for i in range(50)]
    batch2 += [gps_event(i, i * 0.05) for i in range(970, 1000)]
    publish(spark, KAFKA, topic, batch2)
    third = run_available_now(spark, KAFKA, tmp_path, topic)
    assert third["silver"]["input_rows"] == 280
    assert count_parquet(spark, tmp_path / "silver") == 1200
    ids = {r["event_id"] for r in spark.read.parquet(str(tmp_path / "silver")).select("event_id").collect()}
    assert len(ids) == 1200

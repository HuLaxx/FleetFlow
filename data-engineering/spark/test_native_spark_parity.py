"""One real synthetic GPS snapshot through native replay and real Spark.

This is local Spark, not evidence that a Databricks workspace ran.
"""
from datetime import UTC, datetime
import json
import math
from pathlib import Path
from uuid import UUID

import pyarrow.parquet as pq
import pytest
from pyspark.sql import SparkSession

from fleetflow_batch import hourly_vehicle_facts, verified_clean_parquet
from src.events.models import GPSLocationEvent, Location
from src.lakehouse.reconcile import reconcile
from src.lakehouse.replay import replay


@pytest.fixture(scope="module")
def spark():
    session = (
        SparkSession.builder.master("local[2]")
        .appName("fleetflow-native-pyspark-parity")
        .config("spark.sql.session.timeZone", "UTC")
        .config("spark.ui.enabled", "false")
        .getOrCreate()
    )
    yield session
    session.stop()


def _gps(event_number, minute, latitude, *, vehicle=1, speed=None):
    return GPSLocationEvent(
        event_id=UUID(int=event_number),
        timestamp=datetime(2026, 11, 22, 10 if vehicle == 1 else 11, minute, tzinfo=UTC),
        driver_id=UUID(int=100 + vehicle),
        vehicle_id=UUID(int=200 + vehicle),
        route_id=UUID(int=300 + vehicle),
        location=Location(latitude=latitude, longitude=-0.15),
        speed_kmh=speed,
        is_moving=True,
    ).model_dump(mode="json")


def test_native_and_real_spark_match_same_content_addressed_snapshot(spark, tmp_path):
    """Tie timestamps, late source arrival, nullable speed and duplicate input."""
    events = [
        _gps(1, 5, 51.1, speed=10.0),
        _gps(2, 20, 51.2, speed=20.0),
        _gps(3, 20, 51.3, speed=30.0),
        _gps(4, 0, 51.4, speed=None),
        _gps(5, 0, 52.0, vehicle=2, speed=None),
        _gps(1, 5, 51.1, speed=10.0),  # exact duplicate is not counted twice
    ]
    source = tmp_path / "gps.jsonl"
    source.write_text(
        "".join(json.dumps(event) + "\n" for event in events), encoding="utf-8"
    )
    run_dir, manifest = replay(source, tmp_path / "lake")
    receipt = reconcile(run_dir)
    assert receipt["status"] == "reconciled"
    assert manifest["counts"]["accepted"] == 5
    assert manifest["counts"]["duplicates"] == 1
    assert manifest["counts"]["late"] == 1

    checked, clean_paths = verified_clean_parquet(run_dir / "manifest.json")
    assert checked["run_key"] == receipt["run_key"]
    spark_facts = hourly_vehicle_facts(
        spark.read.parquet(*clean_paths), checked["run_key"]
    ).collect()
    native_path = run_dir / "curated" / "hourly_vehicle_telemetry.parquet"
    native_facts = pq.ParquetFile(native_path).read().to_pylist()
    assert len(spark_facts) == len(native_facts) == 2

    native = {
        (row["vehicle_id"], row["hour_utc"]): row
        for row in native_facts
    }
    for actual in spark_facts:
        # Session UTC means Spark timestamps materialise as naive UTC datetimes.
        assert actual.hour_utc.tzinfo is None
        key = (actual.vehicle_id, actual.hour_utc.replace(tzinfo=UTC))
        expected = native[key]
        for name in ("event_count", "late_event_count", "last_latitude", "last_longitude"):
            assert getattr(actual, name) == expected[name]
        assert actual.last_event_time.replace(tzinfo=UTC) == expected["last_event_time"]
        average = expected["avg_speed_kmh"]
        if average is None:
            assert actual.avg_speed_kmh is None
        else:
            assert math.isclose(actual.avg_speed_kmh, average, rel_tol=1e-12)

    v1 = next(row for row in spark_facts if row.vehicle_id == str(UUID(int=201)))
    assert v1.last_latitude == 51.3  # deterministic largest event UUID on timestamp tie
    assert v1.event_count == 4
    assert v1.late_event_count == 1


def test_replay_same_input_is_idempotent_and_reconciled(spark, tmp_path):
    events = [_gps(91, 1, 50.0, speed=20)]
    src = tmp_path / "one.jsonl"
    src.write_text(json.dumps(events[0]) + "\n")
    first_run, first = replay(src, tmp_path / "lake")
    second_run, second = replay(src, tmp_path / "lake")
    assert first_run == second_run
    assert first == second
    manifest, paths = verified_clean_parquet(first_run / "manifest.json")
    rows = hourly_vehicle_facts(spark.read.parquet(*paths), manifest["run_key"]).collect()
    assert len(rows) == rows[0].event_count == 1

"""Real local PySpark assertions; no mocked Spark or cloud credentials."""
from datetime import UTC, datetime

import pytest
from pyspark.sql import SparkSession
from pyspark.sql.types import (
    BooleanType, DoubleType, StringType, StructField, StructType, TimestampType,
)

from fleetflow_batch import hourly_vehicle_facts

KEY = "a" * 64
SCHEMA = StructType([
    StructField("event_id", StringType(), True),
    StructField("vehicle_id", StringType(), True),
    StructField("event_time", TimestampType(), True),
    StructField("latitude", DoubleType(), True),
    StructField("longitude", DoubleType(), True),
    StructField("speed_kmh", DoubleType(), True),
    StructField("is_late", BooleanType(), True),
])


@pytest.fixture(scope="module")
def spark():
    session = (
        SparkSession.builder.master("local[2]")
        .appName("fleetflow-gps-batch-contract")
        .config("spark.sql.session.timeZone", "UTC")
        .config("spark.ui.enabled", "false")
        .getOrCreate()
    )
    yield session
    session.stop()


def _rows():
    return [
        ("a", "v-1", datetime(2026, 11, 22, 10, 0, tzinfo=UTC), 51.1, -0.1, 20.0, False),
        ("b", "v-1", datetime(2026, 11, 22, 10, 10, tzinfo=UTC), 51.2, -0.2, 30.0, True),
        ("c", "v-2", datetime(2026, 11, 22, 11, 0, tzinfo=UTC), 51.3, -0.3, None, False),
    ]


def test_real_spark_hourly_metrics_and_deterministic_location(spark):
    observed = hourly_vehicle_facts(spark.createDataFrame(_rows(), SCHEMA), KEY).collect()
    assert len(observed) == 2
    by_vehicle = {row.vehicle_id: row for row in observed}
    one = by_vehicle["v-1"]
    assert one.run_key == KEY
    assert one.event_count == 2
    assert one.late_event_count == 1
    assert one.avg_speed_kmh == 25.0
    assert one.last_latitude == 51.2
    assert one.last_longitude == -0.2
    assert one.hour_utc.hour == 10
    assert by_vehicle["v-2"].avg_speed_kmh is None


@pytest.mark.parametrize("bad", ["duplicate", "invalid_lat", "missing_key"])
def test_fail_closed_on_invalid_batch(spark, bad):
    rows = _rows()
    if bad == "duplicate":
        rows.append(rows[0])
    elif bad == "invalid_lat":
        rows[0] = (rows[0][0], rows[0][1], rows[0][2], 91.0, *rows[0][4:])
    events = spark.createDataFrame(rows, SCHEMA)
    with pytest.raises(ValueError):
        hourly_vehicle_facts(events, "wrong" if bad == "missing_key" else KEY)


def test_reject_missing_contract_column(spark):
    events = spark.createDataFrame(_rows(), SCHEMA).drop("is_late")
    with pytest.raises(ValueError, match="missing columns"):
        hourly_vehicle_facts(events, KEY)


def test_deterministic_tie_break_on_event_id(spark):
    rows = _rows()[:1] + [
        ("z", "v-1", _rows()[0][2], 53.0, -2.0, 30.0, False)
    ]
    actual = hourly_vehicle_facts(spark.createDataFrame(rows, SCHEMA), KEY).first()
    assert actual.last_latitude == 53.0
    assert actual.last_longitude == -2.0

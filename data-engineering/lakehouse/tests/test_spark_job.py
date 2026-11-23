"""Spark integration tests. Skipped automatically when PySpark isn't installed (they run in CI)."""
import pandas as pd
import pytest

pyspark = pytest.importorskip("pyspark")

from lakehouse import quality, spark_job  # noqa: E402


@pytest.fixture(scope="module")
def spark():
    s = spark_job.build_spark("fleetflow-tests")
    yield s
    s.stop()


@pytest.fixture(scope="module")
def silver(lake, spark):
    root, _ = lake
    quality.run(root, min_pass_rate=0.9)
    first = spark_job.run(str(root), "2026-01-01", "2026-01-03", spark)
    second = spark_job.run(str(root), "2026-01-01", "2026-01-03", spark)   # re-run must be idempotent
    return root, first, second


def test_rerun_is_idempotent(silver):
    _, first, second = silver
    assert first["rows"]["deliveries_total_in_silver"] == second["rows"]["deliveries_total_in_silver"]
    assert second["duplicate_event_ids_in_silver"] == 0


def test_fact_matches_validated_rows(silver):
    root, first, _ = silver
    validated = pd.read_csv(root / "validated/deliveries/deliveries.csv")
    assert first["rows"]["deliveries_in_range"] == len(validated)


def test_backfill_of_one_day_does_not_touch_other_partitions(silver, spark):
    root, first, _ = silver
    spark_job.run(str(root), "2026-01-02", "2026-01-02", spark)
    df = spark.read.parquet(f"{root}/silver/deliveries")
    assert df.count() == first["rows"]["deliveries_total_in_silver"]
    assert sorted(r[0].isoformat() for r in df.select("delivery_date").distinct().collect()) == \
        ["2026-01-01", "2026-01-02", "2026-01-03"]


def test_derived_columns(silver, spark):
    root, _, _ = silver
    df = spark.read.parquet(f"{root}/silver/deliveries").toPandas()
    assert df["is_on_time"].sum() > 0
    assert not (df["is_on_time"] & ~df["is_delivered"]).any()
    assert (df.loc[df["is_on_time"], "lateness_minutes"] <= spark_job.ON_TIME_GRACE_MINUTES).all()

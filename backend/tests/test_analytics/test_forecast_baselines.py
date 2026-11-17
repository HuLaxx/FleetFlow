"""Temporal backtest and fail-closed Airflow scheduling regression."""

import ast
import csv
from datetime import timedelta
from pathlib import Path

import pytest

from src.analytics.forecast_baselines import (
    evaluate,
    prediction,
    read_hourly_csv,
    synthetic_counts,
    validate_hourly,
)

ROOT = Path(__file__).resolve().parents[3]


def test_fixed_seed_is_reproducible_and_chronological():
    first = synthetic_counts(seed=42)
    second = synthetic_counts(seed=42)
    assert first == second
    assert len(first) == 12 * 7 * 24
    validate_hourly(first)
    assert first[1][0] - first[0][0] == timedelta(hours=1)
    assert all(count >= 0 for _, count in first)


def test_chronological_holdout_has_no_target_or_future_feature_leakage():
    observations = synthetic_counts(seed=4)
    n = 168
    result = evaluate(observations, holdout_hours=n)
    assert result["train_hours"] + n == len(observations)
    assert result["holdout_start_utc"] == observations[-n][0].isoformat()
    assert all(record["test_n"] == n for record in result["baselines"])
    assert {r["method"] for r in result["baselines"]} == {
        "last_hour", "last_day", "last_week", "trailing_day_mean"
    }
    assert all(r["mae"] >= 0 and r["rmse"] >= 0 for r in result["baselines"])

    # Deliberately alter the test target/future: the one-step-ahead prediction
    # at the first held-out hour cannot change.
    values = [count for _, count in observations]
    changed_future = values[:]
    changed_future[-n:] = [1000] * n
    for method in ("last_hour", "last_day", "last_week", "trailing_day_mean"):
        assert prediction(values[:-n], method) == prediction(changed_future[:-n], method)


def test_zero_demand_has_undefined_wape_not_fabricated_accuracy():
    zeroes = [(at, 0) for at, _ in synthetic_counts(seed=8)]
    result = evaluate(zeroes)
    assert all(item["mae"] == 0.0 for item in result["baselines"])
    assert all(item["rmse"] == 0.0 for item in result["baselines"])
    assert all(item["wape_pct"] is None for item in result["baselines"])


def test_missing_duplicate_unsorted_and_naive_times_fail_closed():
    original = synthetic_counts(seed=1)
    with pytest.raises(ValueError, match="Missing, duplicated or unsorted"):
        validate_hourly(original[:10] + original[11:])
    duplicate = list(original)
    duplicate[1] = duplicate[0]
    with pytest.raises(ValueError, match="Missing, duplicated or unsorted"):
        validate_hourly(duplicate)
    naive = list(original)
    naive[0] = naive[0][0].replace(tzinfo=None), 5
    with pytest.raises(ValueError, match="UTC"):
        validate_hourly(naive)
    with pytest.raises(ValueError, match="history"):
        evaluate(original[:], holdout_hours=len(original) - 100)


def test_csv_schema_is_strict_and_no_arbitrary_columns(tmp_path):
    source = tmp_path / "hourly.csv"
    with source.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["timestamp_utc", "count"])
        writer.writerows((at.isoformat(), count) for at, count in synthetic_counts(seed=11))
    assert read_hourly_csv(source) == synthetic_counts(seed=11)
    source.write_text("timestamp_utc,count,email\n", encoding="utf-8")
    with pytest.raises(ValueError, match="CSV header"):
        read_hourly_csv(source)


def test_airflow_legacy_dags_are_manual_and_cannot_auto_assign_or_fake_forecasts():
    source_root = ROOT / "data-engineering" / "airflow" / "dags"
    for name in ("daily_optimization.py", "hourly_forecast.py"):
        source = (source_root / name).read_text(encoding="utf-8")
        tree = ast.parse(source)
        schedules = [
            keyword.value
            for node in ast.walk(tree) if isinstance(node, ast.Call)
            for keyword in node.keywords if keyword.arg == "schedule_interval"
        ]
        assert schedules and all(
            isinstance(value, ast.Constant) and value.value is None for value in schedules
        )
        assert "schedule_interval=None" in source
        assert not any(
            forbidden in source for forbidden in (
                "requests.post(", "INSERT INTO routes", "UPDATE routes",
                "confidence': 0.8", "avg_orders = 5", "NYC Main Hub",
            )
        )
    daily = (source_root / "daily_optimization.py").read_text(encoding="utf-8")
    assert "SET TRANSACTION READ ONLY" in daily
    assert "route_date" in daily
    hourly = (source_root / "hourly_forecast.py").read_text(encoding="utf-8")
    assert "check=True" in hourly
    assert "FLEETFLOW_HOURLY_COUNTS_CSV" in hourly

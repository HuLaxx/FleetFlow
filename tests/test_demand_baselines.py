"""Past-only demand baseline acceptance using synthetic, labelled fixtures."""

import json
from datetime import UTC, datetime, timedelta
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

import pytest


def _isolated_source(name: str, relative: str):
    # The old ml/__init__.py imports optional Prophet/Torch/MLflow modules
    # at package import time. A pure stdlib baseline does not need them.
    spec = spec_from_file_location(name, Path(__file__).resolve().parents[1] / "ml" / relative)
    assert spec and spec.loader
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_fixture = _isolated_source("fleetflow_demand_fixture", "data/generate_demand_fixture.py")
_baselines = _isolated_source("fleetflow_demand_baselines", "evaluation/demand_baselines.py")
create = _fixture.create
evaluate = _baselines.evaluate
load_counts = _baselines.load_counts
predict_at = _baselines.predict_at


def test_rolling_evaluation_has_explicit_chronological_holdout(tmp_path):
    path = tmp_path / "synthetic.jsonl"
    create(path)
    series = load_counts(path)
    report = evaluate(series)
    assert report["train_hours"] == 35 * 24 - 168
    assert report["holdout_hours"] == 168
    assert report["train_end_utc"] < report["holdout_start_utc"]
    assert report["evaluation_type"] == "rolling_observed_history_one_step_ahead"
    assert set(report["metrics"]) == {
        "last_hour", "same_hour_yesterday", "same_hour_last_week",
        "trailing_24h_mean",
    }
    for metric in report["metrics"].values():
        assert metric["n"] == 168
        assert metric["mae"] >= 0 and metric["rmse"] >= metric["mae"] - 1e-6
        assert metric["wape_pct"] >= 0


def test_predictions_cannot_use_future_or_target_observation():
    history = list(range(200))
    origin = 180
    original = predict_at(history, origin)
    modified = history.copy()
    modified[origin:] = [10**8] * (len(modified) - origin)
    assert original == predict_at(modified, origin)
    assert original["last_hour"] == 179
    assert original["same_hour_yesterday"] == 156
    assert original["same_hour_last_week"] == 12


def test_zero_demand_reports_undefined_wape_and_mase():
    start = datetime(2026, 9, 7, tzinfo=UTC)
    series = [(start + timedelta(hours=i), 0) for i in range(200)]
    metric = evaluate(series, holdout_hours=24)["metrics"]["last_hour"]
    assert metric["mae"] == 0
    assert metric["wape_pct"] is None
    assert metric["mase_lag1"] is None


@pytest.mark.parametrize(
    "bad_row",
    [
        {"hour_utc": "2026-01-01T01:00:00", "order_count": 2},
        {"hour_utc": "2026-01-01T01:00:00+01:00", "order_count": 2},
        {"hour_utc": "2026-01-01T01:30:00Z", "order_count": 2},
        {"hour_utc": "2026-01-01T01:00:00Z", "order_count": -1},
        {"hour_utc": "2026-01-01T01:00:00Z", "order_count": 2.5},
        {"hour_utc": "2026-01-01T01:00:00Z", "order_count": True},
    ],
)
def test_invalid_times_and_counts_are_rejected(tmp_path, bad_row):
    path = tmp_path / "bad.jsonl"
    path.write_text(json.dumps(bad_row) + "\n", encoding="utf-8")
    with pytest.raises(ValueError):
        load_counts(path)


def test_missing_and_duplicate_hour_rejected(tmp_path):
    start = datetime(2026, 9, 7, tzinfo=UTC)
    path = tmp_path / "bad-gap.jsonl"
    path.write_text(
        "".join(
            json.dumps({"hour_utc": (start + timedelta(hours=i)).isoformat(), "order_count": 2})
            + "\n"
            for i in [0, 2]
        ),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="consecutive"):
        load_counts(path)
    path.write_text(
        "".join(
            json.dumps({"hour_utc": start.isoformat(), "order_count": 2}) + "\n"
            for _ in range(2)
        ),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="consecutive"):
        load_counts(path)


def test_too_short_training_history_rejected():
    start = datetime(2026, 9, 7, tzinfo=UTC)
    series = [(start + timedelta(hours=i), 4) for i in range(100)]
    with pytest.raises(ValueError, match="168"):
        evaluate(series, holdout_hours=24)

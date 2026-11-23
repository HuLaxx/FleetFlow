"""Leakage-aware, deterministic *one-step-ahead* hourly demand baselines.

Explicitly evaluates synthetic or appropriately licensed historical counts;
there is NO asserted accuracy for real FleetFlow orders or trained LSTM.
At each forecast origin t only observations at hours < t are permitted.
"""

from __future__ import annotations

import argparse
import json
import math
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any


def load_counts(path: Path) -> list[tuple[datetime, int]]:
    """Require chronological, gapless UTC hourly observations."""
    rows = []
    with Path(path).open("r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            item = json.loads(line)
            if not isinstance(item, dict) or set(item) != {"hour_utc", "order_count"}:
                raise ValueError("Every row needs only hour_utc and order_count")
            raw = item["hour_utc"]
            if not isinstance(raw, str):
                raise ValueError("hour_utc must be a timestamp string")
            timestamp = datetime.fromisoformat(raw.replace("Z", "+00:00"))
            if timestamp.tzinfo is None or timestamp.utcoffset() != timedelta(0):
                raise ValueError("hour_utc must carry an explicit UTC offset")
            if timestamp.minute or timestamp.second or timestamp.microsecond:
                raise ValueError("hour_utc must align to an exact UTC hour")
            amount = item["order_count"]
            if type(amount) is not int or amount < 0:
                raise ValueError("order_count must be a nonnegative integer")
            if rows and timestamp != rows[-1][0] + timedelta(hours=1):
                raise ValueError("Hours must be strictly consecutive and unique")
            rows.append((timestamp, amount))
    if not rows:
        raise ValueError("No hourly demand observations")
    return rows


def predict_at(counts: list[int], t: int) -> dict[str, float]:
    """Forecast origin t: NO feature at index >= t may enter a prediction."""
    if t < 168 or t >= len(counts):
        raise ValueError("At least 168 earlier hourly observations are required")
    history = counts[:t]
    return {
        "last_hour": float(history[-1]),
        "same_hour_yesterday": float(history[-24]),
        "same_hour_last_week": float(history[-168]),
        "trailing_24h_mean": sum(history[-24:]) / 24,
    }


def _metrics(actual: list[int], predicted: list[float], scale: float | None) -> dict[str, Any]:
    errors = [p - y for y, p in zip(actual, predicted, strict=True)]
    n = len(actual)
    mae = sum(abs(error) for error in errors) / n
    rmse = math.sqrt(sum(error * error for error in errors) / n)
    observed = sum(actual)
    return {
        "n": n,
        "mae": round(mae, 6),
        "rmse": round(rmse, 6),
        "wape_pct": round(sum(abs(e) for e in errors) / observed * 100, 6)
        if observed else None,
        "mase_lag1": round(mae / scale, 6) if scale else None,
        "mean_error": round(sum(errors) / n, 6),
    }


def evaluate(
    series: list[tuple[datetime, int]], *, holdout_hours: int = 168
) -> dict[str, Any]:
    """Chronological holdout; no shuffling, no whole-series fitted statistics."""
    if type(holdout_hours) is not int or holdout_hours < 24:
        raise ValueError("Holdout requires at least 24 hours")
    if len(series) - holdout_hours < 168:
        raise ValueError("Training history requires 168 full hourly observations")
    timestamps = [item[0] for item in series]
    if any(
        timestamps[i] != timestamps[i - 1] + timedelta(hours=1)
        for i in range(1, len(timestamps))
    ):
        raise ValueError("Hourly chronology contains gaps or duplicates")
    if any(timestamp.tzinfo is None or timestamp.utcoffset() != timedelta(0) for timestamp in timestamps):
        raise ValueError("Series must carry explicit UTC timestamps")
    counts = [item[1] for item in series]
    if any(type(value) is not int or value < 0 for value in counts):
        raise ValueError("Counts must be nonnegative integers")
    split = len(counts) - holdout_hours
    train = counts[:split]
    lag1_scale = (
        sum(abs(train[i] - train[i - 1]) for i in range(1, len(train)))
        / (len(train) - 1)
    )
    predictions = {name: [] for name in predict_at(counts, split)}
    actual = counts[split:]
    for t in range(split, len(counts)):
        for name, forecast in predict_at(counts, t).items():
            predictions[name].append(forecast)
    return {
        "dataset": "caller-provided-hourly-counts",
        "evaluation_type": "rolling_observed_history_one_step_ahead",
        "leakage_rule": "prediction at t uses only observed counts at indexes < t",
        "train_start_utc": timestamps[0].astimezone(UTC).isoformat(),
        "train_end_utc": timestamps[split - 1].astimezone(UTC).isoformat(),
        "holdout_start_utc": timestamps[split].astimezone(UTC).isoformat(),
        "holdout_end_utc": timestamps[-1].astimezone(UTC).isoformat(),
        "train_hours": split,
        "holdout_hours": holdout_hours,
        "metrics": {
            name: _metrics(actual, forecast, lag1_scale)
            for name, forecast in predictions.items()
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate chronological demand baselines")
    parser.add_argument("input", type=Path, help="JSONL: hour_utc and order_count")
    parser.add_argument("--holdout-hours", type=int, default=168)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = evaluate(load_counts(args.input), holdout_hours=args.holdout_hours)
    content = json.dumps(report, sort_keys=True, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(content, encoding="utf-8")
    print(content, end="")


if __name__ == "__main__":
    main()

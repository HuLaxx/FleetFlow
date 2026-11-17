"""Leakage-safe chronological evaluation of simple hourly-demand baselines.

No claimed predictive ML model: last-hour, last-day, last-week and trailing
24h average are explicit *baseline* forecasts. The synthetic generator uses
a fixed seed, no customer information, and a fixed UTC time grid.
"""

import argparse
import csv
import json
import math
import random
from datetime import UTC, datetime, timedelta
from pathlib import Path


def synthetic_counts(seed: int = 42, *, weeks: int = 12) -> list[tuple[datetime, int]]:
    """Reproducible seasonality/noise fixture, not real FleetFlow demand."""
    if weeks < 3:
        raise ValueError("At least 3 weeks required")
    rng = random.Random(seed)
    start = datetime(2026, 1, 5, tzinfo=UTC)
    data = []
    for hour in range(weeks * 7 * 24):
        at = start + timedelta(hours=hour)
        peak = 16 if 11 <= at.hour <= 14 or 18 <= at.hour <= 21 else 4
        weekend = 1.25 if at.weekday() >= 5 else 1.0
        # Deterministic, bounded integer demand; no hidden evaluation leakage.
        demand = max(
            0,
            round(
                (peak + 2 * math.sin(at.hour / 24 * 2 * math.pi)) * weekend
                + rng.gauss(0, 2.0)
            ),
        )
        data.append((at, int(demand)))
    return data


def validate_hourly(rows: list[tuple[datetime, int]]) -> None:
    """Require strictly contiguous, timezone-aware UTC hours and nonnegative counts."""
    if len(rows) < 3 * 7 * 24:
        raise ValueError("Require at least three weeks of hourly observations")
    previous = None
    for observed_at, count in rows:
        if (
            observed_at.tzinfo is None
            or observed_at.utcoffset() != timedelta(0)
            or observed_at.minute != 0
            or observed_at.second != 0
            or observed_at.microsecond != 0
        ):
            raise ValueError("Observations must be on exact UTC hour boundaries")
        if not isinstance(count, int) or isinstance(count, bool) or count < 0:
            raise ValueError("Hourly counts must be nonnegative integers")
        if previous is not None and observed_at - previous != timedelta(hours=1):
            raise ValueError("Missing, duplicated or unsorted UTC hour")
        previous = observed_at


def read_hourly_csv(path: Path) -> list[tuple[datetime, int]]:
    """Allow only timestamp_utc,count CSV; no addresses, user IDs or extra columns."""
    rows = []
    with Path(path).open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != ["timestamp_utc", "count"]:
            raise ValueError("CSV header must be timestamp_utc,count")
        for row in reader:
            if not row["timestamp_utc"] or not row["count"]:
                raise ValueError("Blank timestamps/counts not permitted")
            timestamp = row["timestamp_utc"]
            if timestamp.endswith("Z"):
                timestamp = timestamp[:-1] + "+00:00"
            rows.append((datetime.fromisoformat(timestamp), int(row["count"])))
    validate_hourly(rows)
    return rows


def prediction(history: list[int], method: str) -> float:
    """Forecast next hour from values strictly earlier than the target."""
    if method == "last_hour":
        return float(history[-1])
    if method == "last_day":
        return float(history[-24])
    if method == "last_week":
        return float(history[-168])
    if method == "trailing_day_mean":
        return sum(history[-24:]) / 24
    raise ValueError("Unknown baseline method")


def evaluate(
    rows: list[tuple[datetime, int]], *, holdout_hours: int = 7 * 24
) -> dict:
    """Walk-forward test; never uses a target observation or future feature."""
    validate_hourly(rows)
    if holdout_hours < 24 or len(rows) - holdout_hours < 2 * 7 * 24:
        raise ValueError("Need at least 2 weeks of train history plus >=24h holdout")
    counts = [count for _, count in rows]
    split = len(rows) - holdout_hours
    methods = ("last_hour", "last_day", "last_week", "trailing_day_mean")
    results = []
    truth = counts[split:]
    for method in methods:
        forecast = [
            prediction(counts[:index], method)
            for index in range(split, len(rows))
        ]
        errors = [pred - actual for pred, actual in zip(forecast, truth)]
        mae = sum(abs(e) for e in errors) / len(errors)
        rmse = math.sqrt(sum(e * e for e in errors) / len(errors))
        absolute_demand = sum(truth)
        results.append(
            {
                "method": method,
                "test_n": len(truth),
                "mae": round(mae, 4),
                "rmse": round(rmse, 4),
                # WAPE undefined on a zero-demand evaluation window.
                "wape_pct": (
                    round(sum(abs(e) for e in errors) / absolute_demand * 100, 4)
                    if absolute_demand > 0
                    else None
                ),
            }
        )
    return {
        "contract": "fleetflow.chronological.hourly-demand.baselines.v1",
        "train_hours": split,
        "holdout_hours": holdout_hours,
        "train_end_utc": rows[split - 1][0].isoformat(),
        "holdout_start_utc": rows[split][0].isoformat(),
        "holdout_end_utc": rows[-1][0].isoformat(),
        "protocol": "expanding walk-forward one-hour-ahead; strictly past observations",
        "baselines": results,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Chronological hourly-demand baselines")
    parser.add_argument("--input", type=Path, help="Optional validated historical hourly CSV")
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--weeks", type=int, default=12)
    parser.add_argument("--holdout-hours", type=int, default=168)
    args = parser.parse_args()
    rows = (
        read_hourly_csv(args.input)
        if args.input
        else synthetic_counts(args.seed, weeks=args.weeks)
    )
    result = evaluate(rows, holdout_hours=args.holdout_hours)
    result["data_source"] = "validated-user-csv" if args.input else "seeded-synthetic-only"
    if not args.input:
        result["random_seed"] = args.seed
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "source": result["data_source"],
                "test_hours": args.holdout_hours,
                "models": len(result["baselines"]),
                "artifact": str(args.output),
            }
        )
    )


if __name__ == "__main__":
    main()

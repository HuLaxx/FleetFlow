"""Original, deterministic synthetic hourly order counts. No real customers."""

import argparse
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path


def create(path: Path, days: int = 35) -> None:
    if days < 14:
        raise ValueError("At least fourteen fixture days needed")
    start = datetime(2026, 9, 7, tzinfo=UTC)
    rows = []
    for hour_index in range(days * 24):
        timestamp = start + timedelta(hours=hour_index)
        hour = timestamp.hour
        workday = timestamp.weekday() < 5
        morning = 7 <= hour < 11
        evening = 16 <= hour < 20
        # Explicitly synthetic deterministic periodic demand, not fitted.
        amount = 2 + 5 * int(workday) + 7 * int(morning) + 9 * int(evening)
        amount += (hour_index // 24) % 3
        rows.append({
            "hour_utc": timestamp.isoformat(),
            "order_count": amount,
        })
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(item, sort_keys=True) + "\n" for item in rows),
        encoding="utf-8",
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    parser.add_argument("--days", type=int, default=35)
    args = parser.parse_args()
    create(args.output, days=args.days)

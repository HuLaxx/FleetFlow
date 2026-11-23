"""Deterministic synthetic data generator for the FleetFlow lakehouse (bronze layer).

Writes one CSV per raw table into ``<out>/bronze/<table>/<table>.csv``.

The data is synthetic and seeded, so every run with the same arguments produces
byte-identical files. A configurable share of rows is deliberately corrupted
(nulls, out-of-range values, unknown foreign keys, duplicate events, invalid
statuses) so the data-quality layer has real defects to catch.

Usage:
    python -m lakehouse.generate --out data/lakehouse --start-date 2026-01-01 --days 30
"""
from __future__ import annotations

import argparse
import json
import time
from dataclasses import dataclass, asdict
from datetime import date, datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

CITIES = [
    ("Glasgow", 55.8642, -4.2518),
    ("Edinburgh", 55.9533, -3.1883),
    ("Aberdeen", 57.1497, -2.0943),
    ("Dundee", 56.4620, -2.9707),
    ("Stirling", 56.1165, -3.9369),
]
VEHICLE_TYPES = [("van_small", 800), ("van_large", 1500), ("truck_7t", 4000)]
SEGMENTS = ["retail", "business", "healthcare", "hospitality"]


@dataclass
class GenerationSummary:
    start_date: str
    days: int
    orders_per_day: int
    seed: int
    defect_rate: float
    rows: dict
    defects_injected: dict
    seconds: float
    rows_per_second: float


def _ts(d: date, minutes: np.ndarray) -> pd.Series:
    base = pd.Timestamp(d)
    return base + pd.to_timedelta(minutes, unit="m")


def generate(out: Path, start_date: date, days: int = 30, orders_per_day: int = 2000,
             seed: int = 42, defect_rate: float = 0.01) -> GenerationSummary:
    t0 = time.perf_counter()
    rng = np.random.default_rng(seed)
    bronze = out / "bronze"

    # ---- dimensions -------------------------------------------------------
    depots = pd.DataFrame({
        "depot_id": [f"DEP-{i:03d}" for i in range(1, len(CITIES) + 1)],
        "depot_name": [f"{c} Hub" for c, _, _ in CITIES],
        "city": [c for c, _, _ in CITIES],
        "latitude": [lat for _, lat, _ in CITIES],
        "longitude": [lon for _, _, lon in CITIES],
    })

    n_vehicles = 60
    vt_idx = rng.integers(0, len(VEHICLE_TYPES), n_vehicles)
    vehicles = pd.DataFrame({
        "vehicle_id": [f"VEH-{i:04d}" for i in range(1, n_vehicles + 1)],
        "depot_id": rng.choice(depots.depot_id, n_vehicles),
        "vehicle_type": [VEHICLE_TYPES[i][0] for i in vt_idx],
        "capacity_kg": [VEHICLE_TYPES[i][1] for i in vt_idx],
    })

    n_drivers = 70
    drivers = pd.DataFrame({
        "driver_id": [f"DRV-{i:04d}" for i in range(1, n_drivers + 1)],
        "employee_id": [f"E{100000 + i}" for i in range(1, n_drivers + 1)],
        "depot_id": rng.choice(depots.depot_id, n_drivers),
        "hired_date": [str(start_date - timedelta(days=int(x))) for x in rng.integers(30, 2000, n_drivers)],
        "rating": np.round(rng.uniform(3.2, 5.0, n_drivers), 2),
    })

    n_customers = 5000
    customers = pd.DataFrame({
        "customer_id": [f"CUS-{i:05d}" for i in range(1, n_customers + 1)],
        "city": rng.choice([c for c, _, _ in CITIES], n_customers),
        "segment": rng.choice(SEGMENTS, n_customers),
    })

    # ---- facts --------------------------------------------------------------
    order_frames, event_frames = [], []
    order_seq = 0
    for day in range(days):
        d = start_date + timedelta(days=day)
        n = orders_per_day
        ids = np.arange(order_seq + 1, order_seq + n + 1)
        order_seq += n
        win_start_min = rng.integers(7 * 60, 17 * 60, n)          # 07:00 - 17:00
        win_len = rng.choice([60, 120, 180], n)
        orders = pd.DataFrame({
            "order_id": [f"ORD-{i:08d}" for i in ids],
            "order_number": [f"FF{d:%Y%m%d}-{i:06d}" for i in ids],
            "customer_id": rng.choice(customers.customer_id, n),
            "depot_id": rng.choice(depots.depot_id, n),
            "delivery_date": str(d),
            "window_start": _ts(d, win_start_min).astype(str),
            "window_end": _ts(d, win_start_min + win_len).astype(str),
            "weight_kg": np.round(rng.gamma(2.0, 6.0, n), 2),
            "value_gbp": np.round(rng.lognormal(3.6, 0.6, n), 2),
            "priority": rng.choice([1, 2, 3, 4, 5], n, p=[0.1, 0.5, 0.25, 0.1, 0.05]),
            "created_at": _ts(d - timedelta(days=1), rng.integers(0, 24 * 60, n)).astype(str),
        })
        order_frames.append(orders)

        # one delivery attempt per order; arrival is centred on the window with noise
        lateness = rng.normal(-10, 35, n)                           # minutes vs window end
        attempted_min = np.round(win_start_min + win_len + lateness)
        status = np.where(rng.random(n) < 0.94, "delivered", "failed")
        events = pd.DataFrame({
            "event_id": [f"EVT-{i:08d}" for i in ids],
            "order_id": orders.order_id.values,
            "vehicle_id": rng.choice(vehicles.vehicle_id, n),
            "driver_id": rng.choice(drivers.driver_id, n),
            "attempted_at": _ts(d, attempted_min).astype(str),
            "status": status,
            "distance_km": np.round(rng.gamma(2.5, 4.0, n), 2),
            "ingested_at": _ts(d, attempted_min + rng.integers(1, 30, n)).astype(str),
        })
        event_frames.append(events)

    orders = pd.concat(order_frames, ignore_index=True)
    events = pd.concat(event_frames, ignore_index=True)

    # ---- defect injection (deterministic) ------------------------------------
    defects = {}

    def pick(frame: pd.DataFrame, share: float) -> np.ndarray:
        k = max(1, int(len(frame) * share))
        return rng.choice(frame.index.values, k, replace=False)

    share = defect_rate / 5
    idx = pick(orders, share); orders.loc[idx, "customer_id"] = None; defects["orders.null_customer_id"] = len(idx)
    idx = pick(orders, share); orders.loc[idx, "weight_kg"] = -orders.loc[idx, "weight_kg"]; defects["orders.negative_weight"] = len(idx)
    idx = pick(orders, share); orders.loc[idx, "priority"] = 9; defects["orders.priority_out_of_range"] = len(idx)
    idx = pick(orders, share); orders.loc[idx, "depot_id"] = "DEP-999"; defects["orders.unknown_depot"] = len(idx)
    idx = pick(events, share); events.loc[idx, "status"] = "lost_in_space"; defects["deliveries.invalid_status"] = len(idx)
    # late-arriving duplicates: same event_id re-sent later with a corrected distance
    dup_idx = pick(events, share)
    dups = events.loc[dup_idx].copy()
    dups["ingested_at"] = (pd.to_datetime(dups["ingested_at"]) + pd.Timedelta(hours=6)).astype(str)
    dups["distance_km"] = np.round(dups["distance_km"] * 1.05, 2)
    events = pd.concat([events, dups], ignore_index=True)
    defects["deliveries.duplicate_events"] = len(dups)

    tables = {"depots": depots, "vehicles": vehicles, "drivers": drivers,
              "customers": customers, "orders": orders, "deliveries": events}
    for name, df in tables.items():
        target = bronze / name
        target.mkdir(parents=True, exist_ok=True)
        df.to_csv(target / f"{name}.csv", index=False)

    seconds = time.perf_counter() - t0
    rows = {k: int(len(v)) for k, v in tables.items()}
    summary = GenerationSummary(str(start_date), days, orders_per_day, seed, defect_rate,
                                rows, defects, round(seconds, 3),
                                round(sum(rows.values()) / seconds, 1))
    (out / "generation_summary.json").write_text(json.dumps(asdict(summary), indent=2))
    return summary


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--out", type=Path, default=Path("data/lakehouse"))
    p.add_argument("--start-date", type=lambda s: datetime.strptime(s, "%Y-%m-%d").date(),
                   default=date(2026, 1, 1))
    p.add_argument("--days", type=int, default=30)
    p.add_argument("--orders-per-day", type=int, default=2000)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--defect-rate", type=float, default=0.01)
    a = p.parse_args()
    s = generate(a.out, a.start_date, a.days, a.orders_per_day, a.seed, a.defect_rate)
    print(json.dumps(asdict(s), indent=2))


if __name__ == "__main__":
    main()

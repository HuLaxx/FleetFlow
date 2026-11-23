import hashlib
from datetime import date

import pandas as pd

from lakehouse.generate import generate


def _digest(root):
    h = hashlib.sha256()
    for f in sorted((root / "bronze").rglob("*.csv")):
        h.update(f.read_bytes())
    return h.hexdigest()


def test_generation_is_deterministic(tmp_path):
    a, b = tmp_path / "a", tmp_path / "b"
    generate(a, date(2026, 1, 1), days=2, orders_per_day=200, seed=1)
    generate(b, date(2026, 1, 1), days=2, orders_per_day=200, seed=1)
    assert _digest(a) == _digest(b)


def test_different_seed_changes_data(tmp_path):
    a, b = tmp_path / "a", tmp_path / "b"
    generate(a, date(2026, 1, 1), days=1, orders_per_day=100, seed=1)
    generate(b, date(2026, 1, 1), days=1, orders_per_day=100, seed=2)
    assert _digest(a) != _digest(b)


def test_row_counts_and_defects(lake):
    root, summary = lake
    assert summary.rows["orders"] == 3 * 500
    # deliveries = one per order + injected late duplicates
    assert summary.rows["deliveries"] == 1500 + summary.defects_injected["deliveries.duplicate_events"]
    orders = pd.read_csv(root / "bronze/orders/orders.csv")
    assert orders["customer_id"].isna().sum() == summary.defects_injected["orders.null_customer_id"]
    assert (orders["priority"] == 9).sum() == summary.defects_injected["orders.priority_out_of_range"]


def test_delivery_dates_cover_requested_range(lake):
    root, _ = lake
    orders = pd.read_csv(root / "bronze/orders/orders.csv")
    assert sorted(orders["delivery_date"].unique()) == ["2026-01-01", "2026-01-02", "2026-01-03"]

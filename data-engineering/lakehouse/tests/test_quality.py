import json

import pandas as pd
import pytest

from lakehouse.quality import CONTRACTS, run, validate_table


@pytest.fixture(scope="module")
def report(lake):
    root, _ = lake
    return root, run(root, min_pass_rate=0.9)


def test_gate_passes_and_writes_outputs(report):
    root, rep = report
    assert rep["passed"] is True
    for t in ["depots", "vehicles", "drivers", "customers", "orders", "deliveries"]:
        assert (root / "validated" / t / f"{t}.csv").exists()
        assert (root / "quarantine" / f"{t}.csv").exists()
    assert json.loads((root / "quality_report.json").read_text())["passed"] is True


def test_every_injected_order_defect_is_quarantined(report):
    root, _ = report
    clean = pd.read_csv(root / "validated/orders/orders.csv")
    assert clean["customer_id"].notna().all()
    assert (clean["weight_kg"] >= 0).all()
    assert clean["priority"].between(1, 5).all()
    assert not clean["depot_id"].eq("DEP-999").any()
    quar = pd.read_csv(root / "quarantine/orders.csv")
    assert quar["dq_reasons"].str.len().gt(0).all()


def test_deliveries_are_deduplicated_and_referentially_intact(report):
    root, _ = report
    clean = pd.read_csv(root / "validated/deliveries/deliveries.csv")
    orders = pd.read_csv(root / "validated/orders/orders.csv")
    assert clean["event_id"].is_unique
    assert clean["order_id"].isin(orders["order_id"]).all()
    assert set(clean["status"]) <= {"delivered", "failed"}


def test_late_duplicate_keeps_latest_version(report):
    root, _ = report
    raw = pd.read_csv(root / "bronze/deliveries/deliveries.csv")
    dup_ids = raw[raw.duplicated("event_id", keep=False)]
    clean = pd.read_csv(root / "validated/deliveries/deliveries.csv").set_index("event_id")
    checked = 0
    for eid, grp in dup_ids.groupby("event_id"):
        if eid in clean.index:
            latest = grp.sort_values("ingested_at").iloc[-1]
            assert clean.loc[eid, "distance_km"] == pytest.approx(latest["distance_km"])
            checked += 1
    assert checked > 0


def test_missing_column_fails_schema_check():
    df = pd.DataFrame({"depot_id": ["DEP-001"], "city": ["Glasgow"]})
    clean, quar, rep = validate_table("depots", df, CONTRACTS["depots"], {})
    assert rep["schema_ok"] is False
    assert "latitude" in rep["schema_errors"]["missing_columns"]
    assert clean.empty


def test_gate_fails_when_pass_rate_too_low(lake):
    root, _ = lake
    assert run(root, min_pass_rate=0.999)["passed"] is False


def test_validated_csv_is_strictly_typed(report):
    root, _ = report
    line = (root / "validated/orders/orders.csv").read_text().splitlines()[1].split(",")
    header = (root / "validated/orders/orders.csv").read_text().splitlines()[0].split(",")
    row = dict(zip(header, line))
    assert "." not in row["priority"]                      # ints are not written as 3.0
    assert len(row["window_start"]) == len("2026-01-01 08:00:00")
    assert len(row["delivery_date"]) == len("2026-01-01")

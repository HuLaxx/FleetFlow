"""Data contracts and quality gate between the bronze and silver layers.

Each raw table has a contract: required columns, types, uniqueness, allowed
values, numeric ranges and foreign keys. Rows that break a row-level rule are
moved to ``<out>/quarantine/<table>.csv`` with the reason, and clean rows are
written to ``<out>/validated/<table>/<table>.csv`` for the Spark job.

The gate fails (exit code 1) if a schema check fails or a table's pass rate drops
below ``--min-pass-rate``, so a bad batch stops the pipeline instead of reaching
the warehouse.

Usage:
    python -m lakehouse.quality --root data/lakehouse --min-pass-rate 0.95
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd


@dataclass
class Contract:
    columns: dict[str, str]                       # column -> "str" | "float" | "int" | "date" | "timestamp"
    primary_key: str
    not_null: list[str] = field(default_factory=list)
    allowed: dict[str, list] = field(default_factory=dict)
    ranges: dict[str, tuple] = field(default_factory=dict)   # column -> (min, max); None = open
    foreign_keys: dict[str, tuple[str, str]] = field(default_factory=dict)  # col -> (table, col)
    dedupe_on: str | None = None                  # keep latest row per primary key by this column


CONTRACTS: dict[str, Contract] = {
    "depots": Contract(
        columns={"depot_id": "str", "depot_name": "str", "city": "str", "latitude": "float", "longitude": "float"},
        primary_key="depot_id", not_null=["depot_id", "city"],
        ranges={"latitude": (49.0, 61.0), "longitude": (-9.0, 2.0)},
    ),
    "vehicles": Contract(
        columns={"vehicle_id": "str", "depot_id": "str", "vehicle_type": "str", "capacity_kg": "int"},
        primary_key="vehicle_id", not_null=["vehicle_id", "depot_id"],
        ranges={"capacity_kg": (100, 40000)},
        foreign_keys={"depot_id": ("depots", "depot_id")},
    ),
    "drivers": Contract(
        columns={"driver_id": "str", "employee_id": "str", "depot_id": "str", "hired_date": "date", "rating": "float"},
        primary_key="driver_id", not_null=["driver_id", "employee_id"],
        ranges={"rating": (0.0, 5.0)},
        foreign_keys={"depot_id": ("depots", "depot_id")},
    ),
    "customers": Contract(
        columns={"customer_id": "str", "city": "str", "segment": "str"},
        primary_key="customer_id", not_null=["customer_id"],
        allowed={"segment": ["retail", "business", "healthcare", "hospitality"]},
    ),
    "orders": Contract(
        columns={"order_id": "str", "order_number": "str", "customer_id": "str", "depot_id": "str",
                 "delivery_date": "date", "window_start": "timestamp", "window_end": "timestamp",
                 "weight_kg": "float", "value_gbp": "float", "priority": "int", "created_at": "timestamp"},
        primary_key="order_id", not_null=["order_id", "customer_id", "depot_id", "delivery_date"],
        allowed={"priority": [1, 2, 3, 4, 5]},
        ranges={"weight_kg": (0.0, 5000.0), "value_gbp": (0.0, None)},
        foreign_keys={"customer_id": ("customers", "customer_id"), "depot_id": ("depots", "depot_id")},
    ),
    "deliveries": Contract(
        columns={"event_id": "str", "order_id": "str", "vehicle_id": "str", "driver_id": "str",
                 "attempted_at": "timestamp", "status": "str", "distance_km": "float", "ingested_at": "timestamp"},
        primary_key="event_id", not_null=["event_id", "order_id", "attempted_at"],
        allowed={"status": ["delivered", "failed"]},
        ranges={"distance_km": (0.0, 1000.0)},
        foreign_keys={"order_id": ("orders", "order_id"), "vehicle_id": ("vehicles", "vehicle_id"),
                      "driver_id": ("drivers", "driver_id")},
        dedupe_on="ingested_at",
    ),
}
# Parents are validated before children so foreign keys point at clean rows.
ORDER = ["depots", "vehicles", "drivers", "customers", "orders", "deliveries"]


def _coerce(df: pd.DataFrame, contract: Contract) -> tuple[pd.DataFrame, pd.Series]:
    """Cast columns to contract types; returns frame and a per-row 'unparseable' reason series."""
    reasons = pd.Series("", index=df.index, dtype="object")
    out = df.copy()
    for col, kind in contract.columns.items():
        raw = out[col]
        if kind == "str":
            continue
        if kind in ("float", "int"):
            conv = pd.to_numeric(raw, errors="coerce")
        elif kind == "date":
            conv = pd.to_datetime(raw, errors="coerce", format="%Y-%m-%d")
        else:
            conv = pd.to_datetime(raw, errors="coerce")
        bad = raw.notna() & conv.isna()
        reasons[bad] += f"bad_{kind}:{col};"
        out[col] = conv
    return out, reasons


def validate_table(name: str, df: pd.DataFrame, contract: Contract,
                   parents: dict[str, pd.DataFrame]) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    report: dict = {"table": name, "rows_in": int(len(df)), "schema_ok": True, "checks": {}}

    missing = [c for c in contract.columns if c not in df.columns]
    extra = [c for c in df.columns if c not in contract.columns]
    if missing:
        report["schema_ok"] = False
        report["schema_errors"] = {"missing_columns": missing, "unexpected_columns": extra}
        return df.iloc[0:0], df, report
    if extra:
        report["unexpected_columns"] = extra

    df = df[list(contract.columns)].copy()
    df, reasons = _coerce(df, contract)

    def flag(mask: pd.Series, label: str) -> None:
        mask = mask.fillna(False)
        report["checks"][label] = int(mask.sum())
        reasons.loc[mask] += label + ";"

    for col in contract.not_null:
        flag(df[col].isna(), f"not_null:{col}")
    for col, values in contract.allowed.items():
        flag(df[col].notna() & ~df[col].isin(values), f"accepted_values:{col}")
    for col, (lo, hi) in contract.ranges.items():
        m = pd.Series(False, index=df.index)
        if lo is not None:
            m |= df[col] < lo
        if hi is not None:
            m |= df[col] > hi
        flag(m, f"range:{col}")
    for col, (ptable, pcol) in contract.foreign_keys.items():
        parent_keys = set(parents[ptable][pcol]) if ptable in parents else set()
        flag(df[col].notna() & ~df[col].isin(parent_keys), f"foreign_key:{col}->{ptable}")

    bad = reasons != ""
    quarantine = df[bad].copy()
    quarantine["dq_reasons"] = reasons[bad].str.rstrip(";")
    clean = df[~bad].copy()

    # Duplicates: keep the latest version of each key (late-arriving corrections win).
    before = len(clean)
    if contract.dedupe_on:
        clean = clean.sort_values(contract.dedupe_on).drop_duplicates(contract.primary_key, keep="last")
    else:
        clean = clean.drop_duplicates(contract.primary_key, keep="first")
    report["checks"]["deduplicated:" + contract.primary_key] = int(before - len(clean))

    report["rows_quarantined"] = int(len(quarantine))
    report["rows_out"] = int(len(clean))
    report["pass_rate"] = round(1 - len(quarantine) / max(len(df), 1), 5)
    return clean, quarantine, report


def serialise(df: pd.DataFrame, contract: Contract) -> pd.DataFrame:
    """Format typed columns so downstream readers (Spark FAILFAST schemas, dbt) parse them exactly."""
    out = df.copy()
    for col, kind in contract.columns.items():
        if col not in out:
            continue
        if kind == "int":
            out[col] = out[col].astype("Int64")
        elif kind == "date":
            out[col] = pd.to_datetime(out[col]).dt.strftime("%Y-%m-%d")
        elif kind == "timestamp":
            out[col] = pd.to_datetime(out[col]).dt.strftime("%Y-%m-%d %H:%M:%S")
    return out


def run(root: Path, min_pass_rate: float = 0.95) -> dict:
    t0 = time.perf_counter()
    bronze, validated, quarantine_dir = root / "bronze", root / "validated", root / "quarantine"
    quarantine_dir.mkdir(parents=True, exist_ok=True)
    clean_tables: dict[str, pd.DataFrame] = {}
    reports = []
    rows_in = 0
    for name in ORDER:
        raw = pd.read_csv(bronze / name / f"{name}.csv", dtype=str, keep_default_na=True)
        rows_in += len(raw)
        clean, quar, rep = validate_table(name, raw, CONTRACTS[name], clean_tables)
        clean_tables[name] = clean
        reports.append(rep)
        out_dir = validated / name
        out_dir.mkdir(parents=True, exist_ok=True)
        serialise(clean, CONTRACTS[name]).to_csv(out_dir / f"{name}.csv", index=False)
        quar.to_csv(quarantine_dir / f"{name}.csv", index=False)

    seconds = time.perf_counter() - t0
    failed = [r["table"] for r in reports if not r["schema_ok"] or r["pass_rate"] < min_pass_rate]
    summary = {
        "passed": not failed,
        "failed_tables": failed,
        "min_pass_rate": min_pass_rate,
        "rows_validated": rows_in,
        "seconds": round(seconds, 3),
        "rows_per_second": round(rows_in / seconds, 1),
        "tables": reports,
    }
    (root / "quality_report.json").write_text(json.dumps(summary, indent=2))
    return summary


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--root", type=Path, default=Path("data/lakehouse"))
    p.add_argument("--min-pass-rate", type=float, default=0.95)
    a = p.parse_args()
    s = run(a.root, a.min_pass_rate)
    print(json.dumps({k: v for k, v in s.items() if k != "tables"}, indent=2))
    for r in s["tables"]:
        print(f"  {r['table']:<11} in={r['rows_in']:>7} out={r['rows_out']:>7} "
              f"quarantined={r['rows_quarantined']:>5} pass_rate={r['pass_rate']:.4f}")
    sys.exit(0 if s["passed"] else 1)


if __name__ == "__main__":
    main()

"""End-to-end benchmark for the lakehouse pipeline on synthetic data.

Measures each stage (generate -> quality gate -> Spark silver -> idempotent re-run)
and writes ``benchmark.json`` plus a Markdown table. dbt timings are added by CI.

These are synthetic, single-machine numbers for comparing changes over time,
not production performance claims.

Usage:
    python -m lakehouse.benchmark --root data/lakehouse --days 30 --orders-per-day 5000
"""
from __future__ import annotations

import argparse
import json
import os
import platform
import time
from datetime import date, timedelta
from pathlib import Path

from lakehouse import quality
from lakehouse.generate import generate


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--root", type=Path, default=Path("data/lakehouse"))
    p.add_argument("--days", type=int, default=30)
    p.add_argument("--orders-per-day", type=int, default=5000)
    p.add_argument("--skip-spark", action="store_true")
    a = p.parse_args()

    start = date(2026, 1, 1)
    end = start + timedelta(days=a.days - 1)
    results: dict = {
        "environment": {"python": platform.python_version(), "machine": platform.machine(),
                        "cpus": os.cpu_count(), "runner": os.environ.get("RUNNER_NAME", "local")},
        "dataset": {"days": a.days, "orders_per_day": a.orders_per_day},
        "stages": {},
    }

    g = generate(a.root, start, a.days, a.orders_per_day, seed=42, defect_rate=0.01)
    results["stages"]["generate"] = {"rows": sum(g.rows.values()), "seconds": g.seconds,
                                     "rows_per_second": g.rows_per_second}

    q = quality.run(a.root, min_pass_rate=0.95)
    results["stages"]["quality_gate"] = {
        "rows": q["rows_validated"], "seconds": q["seconds"], "rows_per_second": q["rows_per_second"],
        "passed": q["passed"],
        "quarantined": {t["table"]: t["rows_quarantined"] for t in q["tables"]},
    }

    if not a.skip_spark:
        from lakehouse import spark_job
        spark = spark_job.build_spark("fleetflow-benchmark")
        t0 = time.perf_counter()
        first = spark_job.run(str(a.root), str(start), str(end), spark)
        cold = time.perf_counter() - t0
        t0 = time.perf_counter()
        second = spark_job.run(str(a.root), str(start), str(end), spark)
        warm = time.perf_counter() - t0
        spark.stop()
        results["stages"]["spark_silver"] = {
            "fact_rows": first["rows"]["deliveries_in_range"],
            "cold_seconds": round(cold, 2), "rerun_seconds": round(warm, 2),
            "fact_rows_per_second_cold": round(first["rows"]["deliveries_in_range"] / cold, 1),
            "idempotent": first["rows"]["deliveries_total_in_silver"] == second["rows"]["deliveries_total_in_silver"]
                          and second["duplicate_event_ids_in_silver"] == 0,
            "spark_version": first["spark_version"],
        }

    (a.root / "benchmark.json").write_text(json.dumps(results, indent=2))
    lines = ["| Stage | Rows | Time | Throughput |", "| --- | ---: | ---: | ---: |"]
    s = results["stages"]
    lines.append(f"| Generate (bronze CSV) | {s['generate']['rows']:,} | {s['generate']['seconds']} s | {s['generate']['rows_per_second']:,.0f} rows/s |")
    lines.append(f"| Quality gate | {s['quality_gate']['rows']:,} | {s['quality_gate']['seconds']} s | {s['quality_gate']['rows_per_second']:,.0f} rows/s |")
    if "spark_silver" in s:
        sp = s["spark_silver"]
        lines.append(f"| Spark silver (cold) | {sp['fact_rows']:,} | {sp['cold_seconds']} s | {sp['fact_rows_per_second_cold']:,.0f} rows/s |")
        lines.append(f"| Spark silver (re-run, idempotent={sp['idempotent']}) | {sp['fact_rows']:,} | {sp['rerun_seconds']} s | |")
    (a.root / "benchmark.md").write_text("\n".join(lines) + "\n")
    print(json.dumps(results, indent=2))
    print("\n".join(lines))


if __name__ == "__main__":
    main()

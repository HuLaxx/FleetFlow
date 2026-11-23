"""Source freshness: read dbt's ``sources.json`` and re-derive every verdict.

``dbt source freshness`` writes ``target/sources.json``. This module

1. parses it into :class:`FreshnessResult` objects (tolerating runtime errors),
2. independently recomputes each status from ``max_loaded_at``,
   ``snapshotted_at`` and the configured thresholds using dbt's rule
   (``error`` if age > error_after, else ``warn`` if age > warn_after, else
   ``pass``) so a misconfigured artifact or a silent dbt behaviour change is
   caught, and
3. turns the results into Prometheus metrics and alerts.
"""

from __future__ import annotations

import json
import os
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from .metrics import MetricFamily
from .runs import parse_ts

PERIOD_SECONDS = {"minute": 60, "hour": 3600, "day": 86400}
STATUS_CODES = {"pass": 0, "warn": 1, "error": 2, "runtime error": 3}
SEVERITY_ORDER = ("pass", "warn", "error", "runtime error")


def threshold_seconds(threshold: dict[str, Any] | None) -> float | None:
    if not threshold or threshold.get("count") is None or threshold.get("period") is None:
        return None
    period = threshold["period"]
    if period not in PERIOD_SECONDS:
        raise ValueError(f"unknown freshness period {period!r}")
    count = threshold["count"]
    if count <= 0:
        raise ValueError("freshness count must be positive")
    return float(count) * PERIOD_SECONDS[period]


def evaluate(age_seconds: float, warn_after_s: float | None, error_after_s: float | None) -> str:
    """dbt's freshness rule; thresholds are exclusive (age must *exceed* them)."""
    if age_seconds < 0:
        # Clock skew between the loader and the database: treat as just loaded.
        age_seconds = 0.0
    if error_after_s is not None and age_seconds > error_after_s:
        return "error"
    if warn_after_s is not None and age_seconds > warn_after_s:
        return "warn"
    return "pass"


@dataclass(frozen=True)
class FreshnessResult:
    unique_id: str
    source: str
    table: str
    status: str
    max_loaded_at: datetime | None
    snapshotted_at: datetime | None
    age_seconds: float | None
    warn_after_seconds: float | None
    error_after_seconds: float | None
    error: str | None = None

    @property
    def name(self) -> str:
        return f"{self.source}.{self.table}"

    @property
    def recomputed_status(self) -> str:
        if self.status == "runtime error" or self.age_seconds is None:
            return "runtime error"
        return evaluate(self.age_seconds, self.warn_after_seconds, self.error_after_seconds)


@dataclass(frozen=True)
class FreshnessReport:
    results: tuple[FreshnessResult, ...]
    generated_at: datetime | None
    dbt_version: str | None

    def worst(self) -> str:
        if not self.results:
            return "pass"
        return max((r.status for r in self.results), key=SEVERITY_ORDER.index)

    def counts(self) -> dict[str, int]:
        out = {s: 0 for s in SEVERITY_ORDER}
        for r in self.results:
            out[r.status] += 1
        return out

    def disagreements(self) -> list[FreshnessResult]:
        return [r for r in self.results if r.status != r.recomputed_status]

    def by_table(self) -> dict[str, FreshnessResult]:
        return {r.table: r for r in self.results}


def _split_unique_id(unique_id: str) -> tuple[str, str]:
    parts = unique_id.split(".")
    if len(parts) < 4 or parts[0] != "source":
        raise ValueError(f"not a dbt source unique_id: {unique_id!r}")
    return parts[2], ".".join(parts[3:])


def parse_sources_json(data: dict[str, Any]) -> FreshnessReport:
    if "results" not in data or not isinstance(data["results"], list):
        raise ValueError("sources.json has no 'results' list")
    meta = data.get("metadata") or {}
    results = []
    for item in data["results"]:
        status = item.get("status")
        if status not in STATUS_CODES:
            raise ValueError(f"{item.get('unique_id')}: unknown freshness status {status!r}")
        source, table = _split_unique_id(item["unique_id"])
        criteria = item.get("criteria") or {}
        max_loaded = parse_ts(item.get("max_loaded_at"))
        snap = parse_ts(item.get("snapshotted_at"))
        age = item.get("max_loaded_at_time_ago_in_s")
        if age is None and max_loaded and snap:
            age = (snap - max_loaded).total_seconds()
        results.append(
            FreshnessResult(
                unique_id=item["unique_id"],
                source=source,
                table=table,
                status=status,
                max_loaded_at=max_loaded,
                snapshotted_at=snap,
                age_seconds=float(age) if age is not None else None,
                warn_after_seconds=threshold_seconds(criteria.get("warn_after")),
                error_after_seconds=threshold_seconds(criteria.get("error_after")),
                error=(item.get("error") or item.get("message")) if status == "runtime error" else None,
            )
        )
    results.sort(key=lambda r: r.unique_id)
    return FreshnessReport(tuple(results), parse_ts(meta.get("generated_at")), meta.get("dbt_version"))


def load_sources_json(path: str | os.PathLike[str]) -> FreshnessReport:
    with Path(path).open(encoding="utf-8") as fh:
        return parse_sources_json(json.load(fh))


def freshness_metric_families(report: FreshnessReport) -> list[MetricFamily]:
    age = MetricFamily("fleetflow_source_freshness_age_seconds", "Seconds between max(loaded_at) and the check.")
    code = MetricFamily(
        "fleetflow_source_freshness_status_code",
        "dbt freshness verdict: 0=pass 1=warn 2=error 3=runtime error.",
    )
    warn = MetricFamily("fleetflow_source_freshness_warn_after_seconds", "Configured warn_after threshold.")
    err = MetricFamily("fleetflow_source_freshness_error_after_seconds", "Configured error_after threshold.")
    checked = MetricFamily(
        "fleetflow_source_freshness_check_timestamp_seconds",
        "Unix time of the freshness check; alerting uses it to detect a check that stopped running.",
    )
    summary = MetricFamily("fleetflow_source_freshness_sources", "Number of sources by freshness verdict.")
    for r in report.results:
        labels = {"source": r.source, "table": r.table}
        code.add(labels, STATUS_CODES[r.status])
        if r.age_seconds is not None:
            age.add(labels, r.age_seconds)
        if r.warn_after_seconds is not None:
            warn.add(labels, r.warn_after_seconds)
        if r.error_after_seconds is not None:
            err.add(labels, r.error_after_seconds)
    checked_at = report.generated_at or max(
        (r.snapshotted_at for r in report.results if r.snapshotted_at), default=None
    )
    if checked_at is not None:
        checked.add({}, checked_at.timestamp())
    for status, n in report.counts().items():
        summary.add({"status": status}, n)
    return [f for f in (age, code, warn, err, checked, summary) if f.samples]


def _human(seconds: float | None) -> str:
    if seconds is None:
        return "-"
    return str(timedelta(seconds=round(seconds)))


def markdown_summary(report: FreshnessReport) -> str:
    lines = [
        "| Source | dbt status | Recomputed | Age | warn_after | error_after |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for r in report.results:
        lines.append(
            f"| `{r.name}` | {r.status} | {r.recomputed_status} | {_human(r.age_seconds)} "
            f"| {_human(r.warn_after_seconds)} | {_human(r.error_after_seconds)} |"
        )
    counts = ", ".join(f"{k}={v}" for k, v in report.counts().items())
    lines.append("")
    lines.append(f"Worst: **{report.worst()}** ({counts}); dbt {report.dbt_version or 'unknown'}.")
    return "\n".join(lines)


def check_expectations(report: FreshnessReport, expected: dict[str, str]) -> list[str]:
    """Compare statuses with ``{"table": "status"}``; returns human-readable problems."""
    problems = []
    found = report.by_table()
    for table, status in sorted(expected.items()):
        if table not in found:
            problems.append(f"{table}: expected {status}, but no freshness result was produced")
        elif found[table].status != status:
            problems.append(f"{table}: expected {status}, dbt reported {found[table].status}")
    for table in sorted(set(found) - set(expected)):
        problems.append(f"{table}: unexpected freshness result ({found[table].status})")
    for r in report.disagreements():
        problems.append(f"{r.table}: dbt said {r.status} but thresholds imply {r.recomputed_status}")
    return problems


def results_at_or_above(results: Iterable[FreshnessResult], level: str) -> list[FreshnessResult]:
    floor = SEVERITY_ORDER.index(level)
    return [r for r in results if SEVERITY_ORDER.index(r.status) >= floor]

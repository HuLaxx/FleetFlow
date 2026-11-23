"""Minimal Prometheus text exposition (format 0.0.4) without a client library.

Pipelines here are batch jobs, so instead of a long-running HTTP endpoint the
metrics are written to ``*.prom`` files that node_exporter's textfile collector
serves (see ``monitoring/docker-compose.yml``). Files are written atomically so
a scrape never sees a half-written file.
"""

from __future__ import annotations

import math
import os
import re
import tempfile
from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path

from .runs import PipelineRun, latest_runs

_NAME_RE = re.compile(r"^[a-zA-Z_:][a-zA-Z0-9_:]*$")
_LABEL_RE = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*$")


def _escape_label(value: str) -> str:
    return value.replace("\\", "\\\\").replace("\n", "\\n").replace('"', '\\"')


def _escape_help(value: str) -> str:
    return value.replace("\\", "\\\\").replace("\n", "\\n")


def _format_value(value: float) -> str:
    if math.isnan(value):
        return "NaN"
    if math.isinf(value):
        return "+Inf" if value > 0 else "-Inf"
    if float(value).is_integer() and abs(value) < 1e15:
        return str(int(value))
    return repr(float(value))


@dataclass
class MetricFamily:
    name: str
    help: str
    type: str = "gauge"
    samples: list[tuple[dict[str, str], float]] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not _NAME_RE.match(self.name):
            raise ValueError(f"invalid metric name {self.name!r}")
        if self.type not in ("gauge", "counter", "untyped"):
            raise ValueError(f"unsupported metric type {self.type!r}")
        if self.type == "counter" and not self.name.endswith("_total"):
            raise ValueError("counter names must end with _total")

    def add(self, labels: dict[str, str], value: float) -> None:
        for key in labels:
            if not _LABEL_RE.match(key) or key.startswith("__"):
                raise ValueError(f"invalid label name {key!r}")
        self.samples.append((dict(labels), float(value)))

    def render(self) -> str:
        lines = [f"# HELP {self.name} {_escape_help(self.help)}", f"# TYPE {self.name} {self.type}"]
        for labels, value in self.samples:
            if labels:
                body = ",".join(f'{k}="{_escape_label(str(v))}"' for k, v in sorted(labels.items()))
                lines.append(f"{self.name}{{{body}}} {_format_value(value)}")
            else:
                lines.append(f"{self.name} {_format_value(value)}")
        return "\n".join(lines)


def render(families: Iterable[MetricFamily]) -> str:
    seen: set[str] = set()
    parts = []
    for fam in families:
        if fam.name in seen:
            raise ValueError(f"duplicate metric family {fam.name}")
        seen.add(fam.name)
        parts.append(fam.render())
    return "\n".join(parts) + "\n"


def write_textfile(path: str | os.PathLike[str], text: str) -> Path:
    """Atomically replace ``path`` (temp file in the same dir + rename)."""
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=f".{target.name}.", dir=target.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(text)
            fh.flush()
            os.fsync(fh.fileno())
        os.chmod(tmp, 0o644)
        os.replace(tmp, target)
    except BaseException:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise
    return target


def run_metric_families(runs: Iterable[PipelineRun]) -> list[MetricFamily]:
    runs = list(runs)
    last_success = MetricFamily(
        "fleetflow_pipeline_last_run_success",
        "1 if the most recent finished run of this pipeline task succeeded, else 0.",
    )
    last_duration = MetricFamily(
        "fleetflow_pipeline_last_run_duration_seconds", "Wall-clock duration of the most recent finished run."
    )
    last_ts = MetricFamily("fleetflow_pipeline_last_run_timestamp_seconds", "Unix time the most recent run finished.")
    last_ok_ts = MetricFamily(
        "fleetflow_pipeline_last_success_timestamp_seconds", "Unix time of the most recent successful run."
    )
    rows_out = MetricFamily(
        "fleetflow_pipeline_last_run_rows_out", "Rows written by the most recent finished run (if reported)."
    )
    interval = MetricFamily(
        "fleetflow_pipeline_expected_interval_seconds",
        "Declared schedule interval; alerting uses it to detect missing successes.",
    )
    totals = MetricFamily(
        "fleetflow_pipeline_runs_total", "Finished runs recorded in the run store, by status.", "counter"
    )

    counts: dict[tuple[str, str, str], int] = {}
    newest_success: dict[tuple[str, str], PipelineRun] = {}
    for run in runs:
        if run.finished_at is None:
            continue
        key = (run.pipeline, run.task)
        counts[key + (run.status,)] = counts.get(key + (run.status,), 0) + 1
        if run.status == "success":
            cur = newest_success.get(key)
            if cur is None or run.finished_at >= cur.finished_at:  # type: ignore[operator]
                newest_success[key] = run

    for (pipeline, task), run in sorted(latest_runs(runs).items()):
        labels = {"pipeline": pipeline, "task": task}
        last_success.add(labels, 1 if run.status == "success" else 0)
        last_duration.add(labels, run.duration_seconds or 0.0)
        last_ts.add(labels, run.finished_at.timestamp())  # type: ignore[union-attr]
        if run.rows_out is not None:
            rows_out.add(labels, run.rows_out)
        if run.expected_interval_seconds:
            interval.add(labels, run.expected_interval_seconds)
    for (pipeline, task), run in sorted(newest_success.items()):
        last_ok_ts.add({"pipeline": pipeline, "task": task}, run.finished_at.timestamp())  # type: ignore[union-attr]
    for (pipeline, task, status), n in sorted(counts.items()):
        totals.add({"pipeline": pipeline, "task": task, "status": status}, n)

    return [f for f in (last_success, last_duration, last_ts, last_ok_ts, rows_out, interval, totals) if f.samples]

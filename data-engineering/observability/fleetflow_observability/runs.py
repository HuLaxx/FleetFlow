"""Pipeline run records: what ran, when, for how long, and whether it worked.

A run is recorded once when it finishes (success or failure). Two stores are
provided:

* :class:`JsonlRunStore` - append-only JSON lines file. No dependencies; good
  for CI, cron jobs and the node_exporter textfile workflow.
* :class:`SqlRunStore` - any DB-API 2.0 connection (``sqlite3`` locally,
  ``psycopg`` against the FleetFlow PostgreSQL database). Upserts on ``run_id``.

:func:`track_run` is the context manager pipelines use; it records the run and
sends a failure alert without swallowing the original exception.
"""

from __future__ import annotations

import json
import os
import uuid
from collections.abc import Iterable, Iterator
from contextlib import contextmanager
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Any, Protocol

if TYPE_CHECKING:  # pragma: no cover
    from .alerts import AlertDispatcher

STATUSES = ("success", "failed")


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def parse_ts(value: str | datetime | None) -> datetime | None:
    """Parse an ISO-8601 timestamp; naive values are treated as UTC."""
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        dt = value
    else:
        text = value.strip()
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        dt = datetime.fromisoformat(text)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


@dataclass
class PipelineRun:
    pipeline: str
    task: str
    started_at: datetime
    finished_at: datetime | None = None
    status: str = "running"
    rows_in: int | None = None
    rows_out: int | None = None
    error_type: str | None = None
    error_message: str | None = None
    attempt: int = 1
    expected_interval_seconds: float | None = None
    run_id: str = field(default_factory=lambda: uuid.uuid4().hex)

    def __post_init__(self) -> None:
        if not self.pipeline or not self.task:
            raise ValueError("pipeline and task are required")
        self.started_at = parse_ts(self.started_at)  # type: ignore[assignment]
        self.finished_at = parse_ts(self.finished_at)
        if self.status not in STATUSES + ("running",):
            raise ValueError(f"unknown status {self.status!r}")
        for name in ("rows_in", "rows_out"):
            value = getattr(self, name)
            if value is not None and int(value) < 0:
                raise ValueError(f"{name} must be >= 0")
        if self.finished_at and self.finished_at < self.started_at:
            raise ValueError("finished_at is before started_at")

    @property
    def duration_seconds(self) -> float | None:
        if self.finished_at is None:
            return None
        return (self.finished_at - self.started_at).total_seconds()

    def finish(self, status: str, finished_at: datetime | None = None) -> PipelineRun:
        if status not in STATUSES:
            raise ValueError(f"unknown status {status!r}")
        self.status = status
        self.finished_at = finished_at or utcnow()
        if self.finished_at < self.started_at:
            raise ValueError("finished_at is before started_at")
        return self

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["started_at"] = self.started_at.isoformat()
        data["finished_at"] = self.finished_at.isoformat() if self.finished_at else None
        data["duration_seconds"] = self.duration_seconds
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> PipelineRun:
        known = {k: v for k, v in data.items() if k in cls.__dataclass_fields__}
        return cls(**known)


class RunStore(Protocol):
    def record(self, run: PipelineRun) -> None: ...

    def runs(self) -> list[PipelineRun]: ...


class JsonlRunStore:
    """Append-only JSON lines store. The last record for a ``run_id`` wins."""

    def __init__(self, path: str | os.PathLike[str]):
        self.path = Path(path)

    def record(self, run: PipelineRun) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        line = json.dumps(run.to_dict(), sort_keys=True)
        with self.path.open("a", encoding="utf-8") as fh:
            fh.write(line + "\n")
            fh.flush()
            os.fsync(fh.fileno())

    def runs(self) -> list[PipelineRun]:
        if not self.path.exists():
            return []
        by_id: dict[str, PipelineRun] = {}
        with self.path.open(encoding="utf-8") as fh:
            for lineno, line in enumerate(fh, start=1):
                line = line.strip()
                if not line:
                    continue
                try:
                    run = PipelineRun.from_dict(json.loads(line))
                except (ValueError, TypeError) as exc:
                    raise ValueError(f"{self.path}:{lineno}: invalid run record: {exc}") from exc
                by_id[run.run_id] = run
        return list(by_id.values())


_COLUMNS = (
    "run_id",
    "pipeline",
    "task",
    "status",
    "started_at",
    "finished_at",
    "duration_seconds",
    "rows_in",
    "rows_out",
    "error_type",
    "error_message",
    "attempt",
    "expected_interval_seconds",
)


class SqlRunStore:
    """Store runs in ``<table>`` through a DB-API 2.0 connection.

    ``paramstyle`` is ``"qmark"`` for sqlite3 and ``"format"`` for psycopg.
    Timestamps are stored as ISO-8601 text in UTC so the same DDL works on
    both engines; analysts can cast to ``timestamptz`` in PostgreSQL.
    """

    def __init__(self, connection: Any, table: str = "ops_pipeline_runs", paramstyle: str = "qmark"):
        if not table.replace("_", "").replace(".", "").isalnum():
            raise ValueError(f"unsafe table name {table!r}")
        if paramstyle not in ("qmark", "format"):
            raise ValueError("paramstyle must be 'qmark' or 'format'")
        self.conn = connection
        self.table = table
        self.ph = "?" if paramstyle == "qmark" else "%s"
        self._ensure_table()

    def _ensure_table(self) -> None:
        cur = self.conn.cursor()
        cur.execute(f"""
            CREATE TABLE IF NOT EXISTS {self.table} (
                run_id VARCHAR(255) PRIMARY KEY,
                pipeline VARCHAR(200) NOT NULL,
                task VARCHAR(200) NOT NULL,
                status VARCHAR(20) NOT NULL CHECK (status IN ('running', 'success', 'failed')),
                started_at VARCHAR(40) NOT NULL,
                finished_at VARCHAR(40),
                duration_seconds DOUBLE PRECISION,
                rows_in BIGINT,
                rows_out BIGINT,
                error_type VARCHAR(200),
                error_message TEXT,
                attempt INTEGER NOT NULL DEFAULT 1,
                expected_interval_seconds DOUBLE PRECISION
            )
            """)
        self.conn.commit()

    def record(self, run: PipelineRun) -> None:
        data = run.to_dict()
        values = [data[c] for c in _COLUMNS]
        cols = ", ".join(_COLUMNS)
        placeholders = ", ".join([self.ph] * len(_COLUMNS))
        updates = ", ".join(f"{c} = excluded.{c}" for c in _COLUMNS if c != "run_id")
        cur = self.conn.cursor()
        cur.execute(
            f"INSERT INTO {self.table} ({cols}) VALUES ({placeholders}) "
            f"ON CONFLICT (run_id) DO UPDATE SET {updates}",
            values,
        )
        self.conn.commit()

    def runs(self) -> list[PipelineRun]:
        cur = self.conn.cursor()
        cur.execute(f"SELECT {', '.join(_COLUMNS)} FROM {self.table}")
        out = []
        for row in cur.fetchall():
            data = dict(zip(_COLUMNS, row, strict=True))
            data.pop("duration_seconds")
            out.append(PipelineRun.from_dict(data))
        return out


def latest_runs(runs: Iterable[PipelineRun]) -> dict[tuple[str, str], PipelineRun]:
    """Most recent finished run per (pipeline, task), ordered by finish time."""
    latest: dict[tuple[str, str], PipelineRun] = {}
    for run in runs:
        if run.finished_at is None:
            continue
        key = (run.pipeline, run.task)
        current = latest.get(key)
        if current is None or run.finished_at >= current.finished_at:  # type: ignore[operator]
            latest[key] = run
    return latest


@contextmanager
def track_run(
    pipeline: str,
    task: str,
    store: RunStore,
    dispatcher: AlertDispatcher | None = None,
    expected_interval_seconds: float | None = None,
    attempt: int = 1,
    clock: Any = None,
) -> Iterator[PipelineRun]:
    """Record a pipeline step. On exception: record ``failed``, alert, re-raise."""
    now = clock or utcnow
    run = PipelineRun(
        pipeline=pipeline,
        task=task,
        started_at=now(),
        attempt=attempt,
        expected_interval_seconds=expected_interval_seconds,
    )
    try:
        yield run
    except BaseException as exc:
        run.error_type = type(exc).__name__
        run.error_message = str(exc)[:2000]
        _finish(run, "failed", now)
        store.record(run)
        if dispatcher is not None:
            from .alerts import alert_for_run

            dispatcher.dispatch([alert_for_run(run)])
        raise
    else:
        _finish(run, "success", now)
        store.record(run)


def _finish(run: PipelineRun, status: str, now: Any) -> None:
    finished = now()
    # Wall clocks can step backwards; never record a negative duration.
    finished = max(finished, run.started_at)
    run.finish(status, finished)

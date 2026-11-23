"""Failure and staleness alerts with delivery that never takes a pipeline down.

* :class:`WebhookSink` posts Slack-compatible JSON (``{"text": ...}`` plus a
  structured ``alert`` object) to a URL taken from the environment, retrying
  transient failures with backoff. 4xx responses are not retried.
* :class:`LogSink` is the default when no webhook is configured.
* :class:`Deduplicator` suppresses repeats of the same ``dedup_key`` within a
  window so an hourly check does not page every hour for the same stale table.

No URL or token is stored in the repository: set ``FLEETFLOW_ALERT_WEBHOOK_URL``.
"""

from __future__ import annotations

import json
import logging
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass, field
from datetime import timedelta
from pathlib import Path
from typing import Any, Protocol

from .freshness import FreshnessResult, results_at_or_above
from .runs import PipelineRun

log = logging.getLogger("fleetflow.observability.alerts")

SEVERITIES = ("info", "warning", "critical")
WEBHOOK_ENV = "FLEETFLOW_ALERT_WEBHOOK_URL"


@dataclass(frozen=True)
class Alert:
    severity: str
    title: str
    summary: str
    dedup_key: str
    labels: Mapping[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.severity not in SEVERITIES:
            raise ValueError(f"unknown severity {self.severity!r}")

    def to_payload(self) -> dict[str, Any]:
        return {
            "text": f"[{self.severity.upper()}] {self.title}: {self.summary}",
            "alert": {
                "severity": self.severity,
                "title": self.title,
                "summary": self.summary,
                "dedup_key": self.dedup_key,
                "labels": dict(self.labels),
            },
        }


class AlertSink(Protocol):
    name: str

    def send(self, alert: Alert) -> bool: ...


class LogSink:
    name = "log"

    def __init__(self, logger: logging.Logger | None = None):
        self.logger = logger or log

    def send(self, alert: Alert) -> bool:
        level = logging.ERROR if alert.severity == "critical" else logging.WARNING
        self.logger.log(level, "ALERT %s", json.dumps(alert.to_payload(), sort_keys=True))
        return True


class WebhookSink:
    name = "webhook"

    def __init__(
        self,
        url: str,
        timeout: float = 5.0,
        retries: int = 3,
        backoff_seconds: float = 0.5,
        sleep: Callable[[float], None] = time.sleep,
    ):
        parsed = urllib.parse.urlparse(url)
        if parsed.scheme not in ("http", "https") or not parsed.netloc:
            raise ValueError("alert webhook URL must be an absolute http(s) URL")
        self.url = url
        self.timeout = timeout
        self.retries = max(1, retries)
        self.backoff_seconds = backoff_seconds
        self.sleep = sleep
        self.attempts = 0

    def send(self, alert: Alert) -> bool:
        body = json.dumps(alert.to_payload()).encode("utf-8")
        for attempt in range(1, self.retries + 1):
            self.attempts += 1
            # Scheme restricted to http(s) in __init__.
            req = urllib.request.Request(  # noqa: S310
                self.url, data=body, method="POST", headers={"Content-Type": "application/json"}
            )
            try:
                with urllib.request.urlopen(req, timeout=self.timeout) as resp:  # noqa: S310
                    if 200 <= resp.status < 300:
                        return True
            except urllib.error.HTTPError as exc:
                if 400 <= exc.code < 500 and exc.code != 429:
                    log.error("alert webhook rejected %s with HTTP %s; not retrying", alert.dedup_key, exc.code)
                    return False
                log.warning("alert webhook HTTP %s (attempt %d/%d)", exc.code, attempt, self.retries)
            except (urllib.error.URLError, OSError) as exc:
                log.warning("alert webhook unreachable: %s (attempt %d/%d)", exc, attempt, self.retries)
            if attempt < self.retries:
                self.sleep(self.backoff_seconds * (2 ** (attempt - 1)))
        return False


class Deduplicator:
    """Remembers when each ``dedup_key`` was last sent, in a small JSON file."""

    def __init__(self, state_path: str | os.PathLike[str], window: timedelta, clock: Callable[[], float] = time.time):
        self.path = Path(state_path)
        self.window = window.total_seconds()
        self.clock = clock

    def _load(self) -> dict[str, float]:
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            return {str(k): float(v) for k, v in data.items()}
        except FileNotFoundError:
            return {}
        except (ValueError, AttributeError):
            log.warning("alert dedup state %s is corrupt; starting fresh", self.path)
            return {}

    def should_send(self, key: str) -> bool:
        last = self._load().get(key)
        return last is None or (self.clock() - last) >= self.window

    def mark_sent(self, key: str) -> None:
        state = self._load()
        now = self.clock()
        state = {k: v for k, v in state.items() if now - v < self.window}
        state[key] = now
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(self.path.suffix + ".tmp")
        tmp.write_text(json.dumps(state, sort_keys=True), encoding="utf-8")
        os.replace(tmp, self.path)


@dataclass
class DispatchReport:
    sent: list[str] = field(default_factory=list)
    suppressed: list[str] = field(default_factory=list)
    failed: list[str] = field(default_factory=list)


class AlertDispatcher:
    def __init__(self, sinks: Iterable[AlertSink], dedup: Deduplicator | None = None):
        self.sinks = list(sinks)
        if not self.sinks:
            raise ValueError("at least one alert sink is required")
        self.dedup = dedup

    def dispatch(self, alerts: Iterable[Alert]) -> DispatchReport:
        report = DispatchReport()
        for alert in alerts:
            if self.dedup and not self.dedup.should_send(alert.dedup_key):
                report.suppressed.append(alert.dedup_key)
                continue
            delivered = False
            for sink in self.sinks:
                try:
                    delivered = sink.send(alert) or delivered
                except Exception:  # a broken sink must never break the pipeline
                    log.exception("alert sink %s raised", getattr(sink, "name", sink))
            if delivered:
                report.sent.append(alert.dedup_key)
                if self.dedup:
                    self.dedup.mark_sent(alert.dedup_key)
            else:
                report.failed.append(alert.dedup_key)
        return report


def dispatcher_from_env(env: Mapping[str, str] | None = None) -> AlertDispatcher:
    """Webhook + log when ``FLEETFLOW_ALERT_WEBHOOK_URL`` is set, otherwise log only."""
    env = os.environ if env is None else env
    sinks: list[AlertSink] = [LogSink()]
    url = env.get(WEBHOOK_ENV, "").strip()
    if url:
        sinks.insert(0, WebhookSink(url))
    dedup = None
    state = env.get("FLEETFLOW_ALERT_DEDUP_STATE", "").strip()
    if state:
        minutes = float(env.get("FLEETFLOW_ALERT_DEDUP_MINUTES", "60"))
        dedup = Deduplicator(state, timedelta(minutes=minutes))
    return AlertDispatcher(sinks, dedup)


def alert_for_run(run: PipelineRun) -> Alert:
    if run.status != "failed":
        raise ValueError("only failed runs produce alerts")
    duration = run.duration_seconds
    summary = (
        f"{run.error_type or 'Error'}: {run.error_message or 'no message'} "
        f"(attempt {run.attempt}, ran {duration:.1f}s)"
        if duration is not None
        else f"{run.error_type or 'Error'}: {run.error_message or 'no message'}"
    )
    return Alert(
        severity="critical",
        title=f"Pipeline failed: {run.pipeline}.{run.task}",
        summary=summary,
        dedup_key=f"run-failed:{run.pipeline}:{run.task}",
        labels={"pipeline": run.pipeline, "task": run.task, "run_id": run.run_id},
    )


def alerts_for_freshness(results: Iterable[FreshnessResult], min_status: str = "warn") -> list[Alert]:
    alerts = []
    for r in results_at_or_above(results, min_status):
        if r.status == "runtime error":
            severity, what = "critical", f"freshness check could not run: {r.error or 'unknown error'}"
        else:
            severity = "critical" if r.status == "error" else "warning"
            limit = r.error_after_seconds if r.status == "error" else r.warn_after_seconds
            what = (
                f"last load {timedelta(seconds=round(r.age_seconds or 0))} ago "
                f"exceeds {r.status} threshold {timedelta(seconds=round(limit or 0))}"
            )
        alerts.append(
            Alert(
                severity=severity,
                title=f"Stale source {r.name} ({r.status})",
                summary=what,
                dedup_key=f"freshness:{r.name}:{r.status}",
                labels={"source": r.source, "table": r.table, "status": r.status},
            )
        )
    return alerts

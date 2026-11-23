"""FleetFlow pipeline observability: run metrics, source freshness and alerts.

Standard library only, so it can run inside Airflow workers, CI steps and cron
jobs without adding dependencies. See ``data-engineering/observability/README.md``.
"""

from .alerts import Alert, AlertDispatcher, LogSink, WebhookSink, alert_for_run, alerts_for_freshness
from .freshness import FreshnessReport, FreshnessResult, evaluate, load_sources_json, parse_sources_json
from .metrics import MetricFamily, render, run_metric_families, write_textfile
from .runs import JsonlRunStore, PipelineRun, SqlRunStore, track_run

__all__ = [
    "Alert",
    "AlertDispatcher",
    "FreshnessReport",
    "FreshnessResult",
    "JsonlRunStore",
    "LogSink",
    "MetricFamily",
    "PipelineRun",
    "SqlRunStore",
    "WebhookSink",
    "alert_for_run",
    "alerts_for_freshness",
    "evaluate",
    "load_sources_json",
    "parse_sources_json",
    "render",
    "run_metric_families",
    "track_run",
    "write_textfile",
]

__version__ = "0.1.0"

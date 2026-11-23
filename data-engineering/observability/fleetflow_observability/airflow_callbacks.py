"""Airflow task callbacks that record runs and alert on failure.

Airflow is *not* imported: callbacks only read the ``context`` mapping Airflow
passes in, so they are unit-tested with plain objects and add no dependency to
the DAG parser. Configure with environment variables on the Airflow workers:

* ``FLEETFLOW_RUN_STORE_PATH`` - JSON lines run store (default: no recording)
* ``FLEETFLOW_ALERT_WEBHOOK_URL`` - optional webhook; otherwise alerts are logged
"""

from __future__ import annotations

import logging
import os
from collections.abc import Mapping
from dataclasses import replace
from typing import Any

from .alerts import AlertDispatcher, alert_for_run, dispatcher_from_env
from .runs import JsonlRunStore, PipelineRun, RunStore, utcnow

log = logging.getLogger("fleetflow.observability.airflow")

STORE_ENV = "FLEETFLOW_RUN_STORE_PATH"


def _get(obj: Any, name: str, default: Any = None) -> Any:
    if obj is None:
        return default
    if isinstance(obj, Mapping):
        return obj.get(name, default)
    return getattr(obj, name, default)


_PRESETS = {"@hourly": 3600, "@daily": 86400, "@midnight": 86400, "@weekly": 604800}


def schedule_interval_seconds(schedule: Any) -> float | None:
    """Nominal interval for a timedelta, an Airflow preset or a simple cron.

    Only unambiguous crons are mapped: ``M * * * *`` (hourly), ``M H * * *``
    (daily) and ``M H * * D`` (weekly). Anything else returns ``None`` so the
    missed-schedule alert is simply not armed rather than armed wrongly.
    """
    if hasattr(schedule, "total_seconds"):
        return schedule.total_seconds()
    if not isinstance(schedule, str):
        return None
    text = schedule.strip()
    if text in _PRESETS:
        return float(_PRESETS[text])
    fields = text.split()
    if len(fields) != 5 or not fields[0].isdigit():
        return None
    hour, dom, month, dow = fields[1:]
    if (hour, dom, month, dow) == ("*", "*", "*", "*"):
        return 3600.0
    if hour.isdigit() and (dom, month) == ("*", "*"):
        if dow == "*":
            return 86400.0
        if dow.isdigit():
            return 604800.0
    return None


def run_from_context(context: Mapping[str, Any], status: str) -> PipelineRun:
    ti = context.get("task_instance") or context.get("ti")
    dag = context.get("dag")
    dag_id = _get(dag, "dag_id") or _get(ti, "dag_id") or "unknown_dag"
    task_id = _get(ti, "task_id") or _get(context.get("task"), "task_id") or "unknown_task"
    started = _get(ti, "start_date") or utcnow()
    finished = _get(ti, "end_date") or utcnow()
    finished = max(finished, started)
    run = PipelineRun(
        pipeline=str(dag_id),
        task=str(task_id),
        started_at=started,
        attempt=int(_get(ti, "try_number", 1) or 1),
        run_id=f"{dag_id}:{task_id}:{_get(context.get('dag_run'), 'run_id', 'manual')}:{_get(ti, 'try_number', 1)}",
    )
    run.expected_interval_seconds = schedule_interval_seconds(_get(dag, "schedule_interval"))
    exc = context.get("exception")
    if status == "failed":
        run.error_type = type(exc).__name__ if exc is not None else "AirflowTaskFailure"
        run.error_message = str(exc)[:2000] if exc is not None else "task failed without an exception"
    run.finish(status, finished)
    return run


def _store_from_env() -> RunStore | None:
    path = os.environ.get(STORE_ENV, "").strip()
    return JsonlRunStore(path) if path else None


def on_failure_callback(
    context: Mapping[str, Any],
    store: RunStore | None = None,
    dispatcher: AlertDispatcher | None = None,
) -> None:
    run = run_from_context(context, "failed")
    store = store if store is not None else _store_from_env()
    try:
        if store is not None:
            store.record(run)
    except Exception:  # never mask the task failure with a monitoring failure
        log.exception("could not record failed run %s", run.run_id)
    alert = alert_for_run(run)
    log_url = _get(context.get("task_instance") or context.get("ti"), "log_url")
    if log_url:
        alert = replace(alert, summary=f"{alert.summary} - logs: {log_url}")
    (dispatcher or dispatcher_from_env()).dispatch([alert])


def on_success_callback(context: Mapping[str, Any], store: RunStore | None = None) -> None:
    store = store if store is not None else _store_from_env()
    if store is None:
        return
    try:
        store.record(run_from_context(context, "success"))
    except Exception:
        log.exception("could not record successful run")

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest

from fleetflow_observability.airflow_callbacks import (
    on_failure_callback,
    on_success_callback,
    run_from_context,
    schedule_interval_seconds,
)
from fleetflow_observability.alerts import AlertDispatcher
from fleetflow_observability.runs import JsonlRunStore

T0 = datetime(2026, 11, 23, 2, 0, tzinfo=timezone.utc)


class RecordingSink:
    name = "recording"

    def __init__(self):
        self.alerts = []

    def send(self, alert):
        self.alerts.append(alert)
        return True


def context(exception=None, end=T0 + timedelta(minutes=3)):
    """Shape of the Airflow 2.x callback context (only the keys we read)."""
    return {
        "dag": SimpleNamespace(dag_id="fleetflow_daily_optimization", schedule_interval=timedelta(days=1)),
        "task_instance": SimpleNamespace(
            task_id="optimize_routes",
            dag_id="fleetflow_daily_optimization",
            try_number=2,
            start_date=T0,
            end_date=end,
            log_url="http://airflow.local/log?task_id=optimize_routes",
        ),
        "dag_run": SimpleNamespace(run_id="scheduled__2026-11-23T02:00:00+00:00"),
        "exception": exception,
    }


def test_run_from_context():
    run = run_from_context(context(ValueError("no vehicles")), "failed")
    assert (run.pipeline, run.task, run.attempt) == ("fleetflow_daily_optimization", "optimize_routes", 2)
    assert run.duration_seconds == 180
    assert run.expected_interval_seconds == 86400
    assert run.error_type == "ValueError" and run.error_message == "no vehicles"
    assert run.run_id.endswith(":2")


def test_context_without_end_date_or_exception():
    run = run_from_context({"ti": {"task_id": "t", "dag_id": "d", "start_date": T0}}, "failed")
    assert run.pipeline == "d" and run.error_type == "AirflowTaskFailure"


def test_failure_callback_records_and_alerts_with_log_link(tmp_path):
    store = JsonlRunStore(tmp_path / "runs.jsonl")
    sink = RecordingSink()
    on_failure_callback(context(TimeoutError("OR-Tools exceeded 30s")), store=store, dispatcher=AlertDispatcher([sink]))
    [run] = store.runs()
    assert run.status == "failed"
    [alert] = sink.alerts
    assert "OR-Tools exceeded 30s" in alert.summary
    assert alert.summary.endswith("logs: http://airflow.local/log?task_id=optimize_routes")


def test_failure_callback_alerts_even_if_store_breaks():
    class BrokenStore:
        def record(self, run):
            raise OSError("disk full")

    sink = RecordingSink()
    on_failure_callback(context(), store=BrokenStore(), dispatcher=AlertDispatcher([sink]))
    assert len(sink.alerts) == 1


def test_success_callback_uses_env_store(tmp_path, monkeypatch):
    monkeypatch.setenv("FLEETFLOW_RUN_STORE_PATH", str(tmp_path / "env-runs.jsonl"))
    on_success_callback(context())
    [run] = JsonlRunStore(tmp_path / "env-runs.jsonl").runs()
    assert run.status == "success" and run.error_type is None


def test_success_callback_without_store_is_noop(monkeypatch):
    monkeypatch.delenv("FLEETFLOW_RUN_STORE_PATH", raising=False)
    on_success_callback(context())  # must not raise


@pytest.mark.parametrize(
    "schedule,expected",
    [
        (timedelta(minutes=30), 1800),
        ("@hourly", 3600),
        ("@daily", 86400),
        ("0 * * * *", 3600),  # hourly_forecast.py
        ("0 18 * * *", 86400),  # daily_optimization.py
        ("30 6 * * 1", 604800),
        ("*/5 * * * *", None),
        ("0 9-17 * * *", None),
        ("0 0 1 * *", None),
        (None, None),
        ("not a cron", None),
    ],
)
def test_schedule_interval_seconds(schedule, expected):
    assert schedule_interval_seconds(schedule) == expected

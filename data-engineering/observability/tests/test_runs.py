import os
import sqlite3
from datetime import datetime, timedelta, timezone

import pytest

from fleetflow_observability.alerts import AlertDispatcher
from fleetflow_observability.runs import JsonlRunStore, PipelineRun, SqlRunStore, latest_runs, parse_ts, track_run

T0 = datetime(2026, 11, 23, 9, 0, tzinfo=timezone.utc)


class RecordingSink:
    name = "recording"

    def __init__(self):
        self.alerts = []

    def send(self, alert):
        self.alerts.append(alert)
        return True


class Clock:
    def __init__(self, *times):
        self.times = list(times)

    def __call__(self):
        return self.times.pop(0)


def test_parse_ts_normalises_to_utc():
    assert parse_ts("2026-11-23T09:00:00Z") == T0
    assert parse_ts("2026-11-23T09:00:00") == T0
    assert parse_ts("2026-11-23T10:00:00+01:00") == T0
    assert parse_ts(None) is None and parse_ts("") is None


@pytest.mark.parametrize(
    "kwargs",
    [
        {"pipeline": "", "task": "t"},
        {"pipeline": "p", "task": "t", "status": "exploded"},
        {"pipeline": "p", "task": "t", "rows_out": -1},
        {"pipeline": "p", "task": "t", "finished_at": T0 - timedelta(seconds=1)},
    ],
)
def test_run_validation(kwargs):
    with pytest.raises(ValueError):
        PipelineRun(started_at=T0, **kwargs)


def test_finish_and_duration():
    r = PipelineRun(pipeline="p", task="t", started_at=T0)
    assert r.duration_seconds is None
    r.finish("success", T0 + timedelta(seconds=90))
    assert r.duration_seconds == 90
    with pytest.raises(ValueError):
        r.finish("running", T0)
    with pytest.raises(ValueError):
        r.finish("failed", T0 - timedelta(seconds=1))


def test_jsonl_roundtrip_last_record_wins(tmp_path):
    store = JsonlRunStore(tmp_path / "runs" / "runs.jsonl")
    assert store.runs() == []
    r = PipelineRun(pipeline="p", task="t", started_at=T0, rows_in=10).finish("failed", T0 + timedelta(seconds=1))
    store.record(r)
    r.status = "success"
    store.record(r)
    other = PipelineRun(pipeline="p", task="u", started_at=T0).finish("success", T0 + timedelta(seconds=2))
    store.record(other)
    runs = {x.run_id: x for x in store.runs()}
    assert len(runs) == 2
    assert runs[r.run_id].status == "success" and runs[r.run_id].rows_in == 10
    assert runs[r.run_id].started_at == T0


def test_jsonl_corrupt_line_reports_location(tmp_path):
    path = tmp_path / "runs.jsonl"
    path.write_text('{"pipeline": "p", "task": "t", "started_at": "2026-11-23T09:00:00Z"}\n\nnot json\n')
    with pytest.raises(ValueError, match="runs.jsonl:3"):
        JsonlRunStore(path).runs()


def _exercise_sql_store(store):
    r = PipelineRun(pipeline="p", task="t", started_at=T0, rows_out=5).finish("failed", T0 + timedelta(seconds=3))
    store.record(r)
    r.status = "success"
    r.error_message = None
    store.record(r)  # upsert, not duplicate
    runs = store.runs()
    assert len(runs) == 1
    assert runs[0].status == "success" and runs[0].rows_out == 5 and runs[0].duration_seconds == 3


def test_sqlite_store_upserts():
    conn = sqlite3.connect(":memory:")
    _exercise_sql_store(SqlRunStore(conn))
    # the CHECK constraint guards the column even for direct writes
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO ops_pipeline_runs (run_id, pipeline, task, status, started_at) VALUES ('x','p','t','bad','')"
        )


def test_sql_store_rejects_unsafe_identifiers():
    with pytest.raises(ValueError):
        SqlRunStore(sqlite3.connect(":memory:"), table="runs; DROP TABLE x")
    with pytest.raises(ValueError):
        SqlRunStore(sqlite3.connect(":memory:"), paramstyle="named")


@pytest.mark.skipif(not os.environ.get("FLEETFLOW_TEST_POSTGRES_DSN"), reason="PostgreSQL not configured")
def test_postgres_store_upserts():
    psycopg = pytest.importorskip("psycopg")
    with psycopg.connect(os.environ["FLEETFLOW_TEST_POSTGRES_DSN"]) as conn:
        conn.execute("DROP TABLE IF EXISTS ops_pipeline_runs_test")
        conn.commit()
        _exercise_sql_store(SqlRunStore(conn, table="ops_pipeline_runs_test", paramstyle="format"))


def test_latest_runs_uses_finish_time():
    a = PipelineRun(pipeline="p", task="t", started_at=T0).finish("success", T0 + timedelta(seconds=50))
    b = PipelineRun(pipeline="p", task="t", started_at=T0 + timedelta(seconds=10)).finish(
        "failed", T0 + timedelta(seconds=20)
    )
    running = PipelineRun(pipeline="p", task="t", started_at=T0 + timedelta(seconds=60))
    assert latest_runs([b, a, running])[("p", "t")] is a


def test_track_run_success(tmp_path):
    store = JsonlRunStore(tmp_path / "r.jsonl")
    with track_run("p", "t", store, clock=Clock(T0, T0 + timedelta(seconds=4)), expected_interval_seconds=3600) as r:
        r.rows_out = 7
    [saved] = store.runs()
    assert (saved.status, saved.rows_out, saved.duration_seconds, saved.expected_interval_seconds) == (
        "success",
        7,
        4,
        3600,
    )


def test_track_run_failure_records_alerts_and_reraises(tmp_path):
    store = JsonlRunStore(tmp_path / "r.jsonl")
    sink = RecordingSink()
    with pytest.raises(RuntimeError, match="solver timed out"):
        with track_run("daily_optimization", "solve", store, AlertDispatcher([sink]), clock=Clock(T0, T0)):
            raise RuntimeError("solver timed out")
    [saved] = store.runs()
    assert saved.status == "failed" and saved.error_type == "RuntimeError"
    [alert] = sink.alerts
    assert alert.severity == "critical"
    assert alert.title == "Pipeline failed: daily_optimization.solve"
    assert "solver timed out" in alert.summary


def test_track_run_clamps_backwards_clock(tmp_path):
    store = JsonlRunStore(tmp_path / "r.jsonl")
    with track_run("p", "t", store, clock=Clock(T0, T0 - timedelta(seconds=5))):
        pass
    assert store.runs()[0].duration_seconds == 0

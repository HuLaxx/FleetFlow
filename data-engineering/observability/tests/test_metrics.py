import os
import re
from datetime import datetime, timedelta, timezone

import pytest

from fleetflow_observability.metrics import MetricFamily, render, run_metric_families, write_textfile
from fleetflow_observability.runs import PipelineRun

T0 = datetime(2026, 11, 23, 9, 0, tzinfo=timezone.utc)

SAMPLE_RE = re.compile(
    r'^[a-zA-Z_:][a-zA-Z0-9_:]*(\{([a-zA-Z_][a-zA-Z0-9_]*="([^"\\\n]|\\["\\n])*",?)*\})? '
    r"(-?[0-9.eE+-]+|NaN|[+-]Inf)$"
)


def assert_valid_exposition(text):
    """Line-level check of Prometheus text format 0.0.4 (promtool also checks this in CI)."""
    assert text.endswith("\n")
    typed = set()
    for line in text.splitlines():
        if line.startswith("# HELP "):
            continue
        if line.startswith("# TYPE "):
            _, _, name, kind = line.split(" ")
            assert name not in typed, f"duplicate TYPE for {name}"
            assert kind in ("gauge", "counter", "untyped")
            typed.add(name)
            continue
        assert SAMPLE_RE.match(line), f"invalid sample line: {line!r}"
        assert line.split("{")[0].split(" ")[0] in typed


def run(pipeline, task, status, minutes, duration=30, **kw):
    start = T0 + timedelta(minutes=minutes)
    r = PipelineRun(pipeline=pipeline, task=task, started_at=start, **kw)
    return r.finish(status, start + timedelta(seconds=duration))


def test_label_escaping_and_value_formatting():
    fam = MetricFamily("x_metric", "help with \\ and\nnewline")
    fam.add({"b": 'quote " back \\ nl \n', "a": "1"}, 1.5)
    fam.add({}, 3.0)
    fam.add({}, float("inf"))
    fam.add({}, float("nan"))
    text = render([fam])
    assert "# HELP x_metric help with \\\\ and\\nnewline" in text
    assert 'x_metric{a="1",b="quote \\" back \\\\ nl \\n"} 1.5' in text
    assert "x_metric 3\n" in text and "x_metric +Inf" in text and "x_metric NaN" in text
    assert_valid_exposition(text)


@pytest.mark.parametrize(
    "factory",
    [
        lambda: MetricFamily("1bad", "h"),
        lambda: MetricFamily("ok", "h", "histogram"),
        lambda: MetricFamily("runs", "h", "counter"),
        lambda: MetricFamily("ok", "h").add({"__name__": "x"}, 1),
        lambda: MetricFamily("ok", "h").add({"bad-label": "x"}, 1),
        lambda: render([MetricFamily("dup", "h"), MetricFamily("dup", "h")]),
    ],
)
def test_invalid_metrics_rejected(factory):
    with pytest.raises(ValueError):
        factory()


def test_write_textfile_is_atomic_and_readable(tmp_path):
    target = tmp_path / "textfile" / "fleetflow.prom"
    write_textfile(target, "a 1\n")
    write_textfile(target, "a 2\n")
    assert target.read_text() == "a 2\n"
    assert oct(os.stat(target).st_mode)[-3:] == "644"
    assert [p.name for p in target.parent.iterdir()] == ["fleetflow.prom"]  # no temp files left


def test_run_metric_families_latest_and_totals():
    runs = [
        run("daily_optimization", "solve", "success", 0, duration=40, rows_out=120, expected_interval_seconds=86400),
        run("daily_optimization", "solve", "failed", 60, duration=5, expected_interval_seconds=86400),
        run("daily_optimization", "extract", "success", 10, duration=12, rows_out=300),
        run("hourly_forecast", "predict", "success", 20, duration=8),
    ]
    text = render(run_metric_families(runs))
    assert_valid_exposition(text)
    solve = 'pipeline="daily_optimization",task="solve"'
    assert f"fleetflow_pipeline_last_run_success{{{solve}}} 0" in text
    assert f"fleetflow_pipeline_last_run_duration_seconds{{{solve}}} 5" in text
    # last success is the earlier run, not the failed one
    ok_ts = int((T0 + timedelta(seconds=40)).timestamp())
    assert f"fleetflow_pipeline_last_success_timestamp_seconds{{{solve}}} {ok_ts}" in text
    assert f"fleetflow_pipeline_expected_interval_seconds{{{solve}}} 86400" in text
    # labels are rendered in sorted order
    assert 'fleetflow_pipeline_runs_total{pipeline="daily_optimization",status="failed",task="solve"} 1' in text
    assert 'fleetflow_pipeline_runs_total{pipeline="daily_optimization",status="success",task="solve"} 1' in text
    assert 'fleetflow_pipeline_last_run_rows_out{pipeline="daily_optimization",task="extract"} 300' in text
    # failed latest run reports no rows_out sample for solve
    assert f"fleetflow_pipeline_last_run_rows_out{{{solve}}}" not in text


def test_running_runs_are_ignored_and_empty_families_dropped():
    unfinished = PipelineRun(pipeline="p", task="t", started_at=T0)
    assert run_metric_families([unfinished]) == []
    assert render([]) == "\n"

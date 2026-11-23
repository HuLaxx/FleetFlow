import json
import subprocess
import sys
from pathlib import Path

import pytest

from fleetflow_observability.cli import main
from fleetflow_observability.runs import JsonlRunStore

ROOT = Path(__file__).resolve().parents[1]
EXPECTED = {"orders": "pass", "drivers": "warn", "route_stops": "error", "routes": "runtime error"}


def test_freshness_gate_and_outputs(sources_json_path, tmp_path, capsys):
    prom, md = tmp_path / "f.prom", tmp_path / "f.md"
    code = main(
        ["freshness", "--sources-json", str(sources_json_path), "--metrics-out", str(prom), "--summary-md", str(md)]
    )
    assert code == 1  # error-level source present, default --fail-on error
    assert "fleetflow_source_freshness_status_code" in prom.read_text()
    assert "raw.route_stops" in md.read_text()
    out = capsys.readouterr().out
    summary = json.loads(out.strip().splitlines()[-1])
    assert summary["worst"] == "runtime error" and summary["disagreements"] == []


def test_freshness_fail_on_levels(sources_json_path):
    assert main(["freshness", "--sources-json", str(sources_json_path), "--fail-on", "never"]) == 0
    assert main(["freshness", "--sources-json", str(sources_json_path), "--fail-on", "warn"]) == 1


def test_freshness_expectations(sources_json_path, tmp_path):
    good, bad = tmp_path / "good.json", tmp_path / "bad.json"
    good.write_text(json.dumps(EXPECTED))
    bad.write_text(json.dumps({**EXPECTED, "orders": "error"}))
    assert (
        main(["freshness", "--sources-json", str(sources_json_path), "--expect", str(good), "--fail-on", "never"]) == 0
    )
    assert main(["freshness", "--sources-json", str(sources_json_path), "--expect", str(bad)]) == 2


def test_freshness_bad_input(tmp_path):
    missing = tmp_path / "nope.json"
    assert main(["freshness", "--sources-json", str(missing)]) == 2
    broken = tmp_path / "broken.json"
    broken.write_text('{"results": "x"}')
    assert main(["freshness", "--sources-json", str(broken)]) == 2


def test_freshness_alerts_to_webhook(sources_json_path, webhook_receiver, monkeypatch, capsys):
    with webhook_receiver() as rx:
        monkeypatch.setenv("FLEETFLOW_ALERT_WEBHOOK_URL", rx.url)
        main(["freshness", "--sources-json", str(sources_json_path), "--alert", "--alert-min-status", "error"])
    tables = sorted(r["json"]["alert"]["labels"]["table"] for r in rx.requests)
    assert tables == ["route_stops", "routes"]


def test_track_records_success_and_failure(tmp_path, webhook_receiver, monkeypatch):
    store, prom = tmp_path / "runs.jsonl", tmp_path / "runs.prom"
    base = ["track", "--store", str(store), "--metrics-out", str(prom), "--pipeline", "dbt", "--task", "freshness"]
    assert main([*base, "--expected-interval-seconds", "3600", "--", sys.executable, "-c", "pass"]) == 0
    with webhook_receiver() as rx:
        monkeypatch.setenv("FLEETFLOW_ALERT_WEBHOOK_URL", rx.url)
        assert main([*base, "--alert", "--", sys.executable, "-c", "raise SystemExit(3)"]) == 3
    runs = sorted(JsonlRunStore(store).runs(), key=lambda r: r.finished_at)
    assert [r.status for r in runs] == ["success", "failed"]
    assert "exited with code 3" in runs[1].error_message
    assert 'fleetflow_pipeline_last_run_success{pipeline="dbt",task="freshness"} 0' in prom.read_text()
    assert rx.requests[0]["json"]["alert"]["title"] == "Pipeline failed: dbt.freshness"


def test_track_missing_command(tmp_path):
    assert main(["track", "--store", str(tmp_path / "r"), "--pipeline", "p", "--task", "t", "--"]) == 2
    assert (
        main(["track", "--store", str(tmp_path / "r"), "--pipeline", "p", "--task", "t", "--", "/no/such/bin"]) == 127
    )


def test_record_run_and_run_metrics(tmp_path, capsys):
    store = tmp_path / "runs.jsonl"
    args = ["record-run", "--store", str(store), "--pipeline", "p", "--task", "t"]
    assert (
        main(
            [
                *args,
                "--status",
                "success",
                "--started-at",
                "2026-11-23T09:00:00Z",
                "--finished-at",
                "2026-11-23T09:00:30Z",
                "--rows-out",
                "42",
            ]
        )
        == 0
    )
    assert (
        main(
            [
                *args,
                "--status",
                "failed",
                "--started-at",
                "2026-11-23T10:00:00Z",
                "--finished-at",
                "2026-11-23T09:00:00Z",
            ]
        )
        == 2
    )
    capsys.readouterr()
    assert main(["run-metrics", "--store", str(store)]) == 0
    out = capsys.readouterr().out
    assert 'fleetflow_pipeline_last_run_rows_out{pipeline="p",task="t"} 42' in out
    store.write_text("garbage\n")
    assert main(["run-metrics", "--store", str(store)]) == 2


@pytest.mark.parametrize("argv", [["--help"], ["freshness", "--help"]])
def test_module_entry_point(argv):
    proc = subprocess.run(
        [sys.executable, "-m", "fleetflow_observability", *argv], cwd=ROOT, capture_output=True, text=True, check=False
    )
    assert proc.returncode == 0 and "usage" in proc.stdout

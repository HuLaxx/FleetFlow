"""Command line entry point: ``python -m fleetflow_observability <command>``.

Commands
--------
freshness    Parse dbt ``sources.json``; write metrics/summary; alert; gate.
track        Run a command, record it as a pipeline run, alert if it fails.
record-run   Append a run record (for steps that time themselves).
run-metrics  Render run-store metrics for the node_exporter textfile collector.

Exit codes: 0 ok, 1 freshness gate breached, 2 bad input or expectation
mismatch; ``track`` returns the wrapped command's own exit code.
"""

from __future__ import annotations

import argparse
import json
import logging
import subprocess
import sys
from collections.abc import Sequence
from datetime import datetime, timezone
from pathlib import Path

from .alerts import alert_for_run, alerts_for_freshness, dispatcher_from_env
from .freshness import (
    SEVERITY_ORDER,
    check_expectations,
    freshness_metric_families,
    load_sources_json,
    markdown_summary,
    results_at_or_above,
)
from .metrics import render, run_metric_families, write_textfile
from .runs import JsonlRunStore, PipelineRun, parse_ts, utcnow


def _cmd_freshness(args: argparse.Namespace) -> int:
    try:
        report = load_sources_json(args.sources_json)
    except (OSError, ValueError) as exc:
        print(f"error: cannot read {args.sources_json}: {exc}", file=sys.stderr)
        return 2
    if args.metrics_out:
        write_textfile(args.metrics_out, render(freshness_metric_families(report)))
    summary = markdown_summary(report)
    if args.summary_md:
        Path(args.summary_md).write_text(summary + "\n", encoding="utf-8")
    print(summary)

    alerts_report = None
    if args.alert:
        alerts_report = dispatcher_from_env().dispatch(alerts_for_freshness(report.results, args.alert_min_status))

    print(
        json.dumps(
            {
                "worst": report.worst(),
                "counts": report.counts(),
                "disagreements": [r.name for r in report.disagreements()],
                "alerts": None if alerts_report is None else alerts_report.__dict__,
            },
            sort_keys=True,
        )
    )

    problems = [f"{r.name}: dbt={r.status} recomputed={r.recomputed_status}" for r in report.disagreements()]
    if args.expect:
        expected = json.loads(Path(args.expect).read_text(encoding="utf-8"))
        problems = check_expectations(report, expected)
    if problems:
        for p in problems:
            print(f"MISMATCH {p}", file=sys.stderr)
        return 2
    if args.fail_on != "never" and results_at_or_above(report.results, args.fail_on):
        print(f"freshness gate: at least one source is {args.fail_on} or worse", file=sys.stderr)
        return 1
    return 0


def _record(args: argparse.Namespace, run: PipelineRun) -> None:
    store = JsonlRunStore(args.store)
    store.record(run)
    if getattr(args, "metrics_out", None):
        write_textfile(args.metrics_out, render(run_metric_families(store.runs())))


def _cmd_track(args: argparse.Namespace) -> int:
    command = list(args.command)
    if command and command[0] == "--":
        command = command[1:]
    if not command:
        print("error: track needs a command after --", file=sys.stderr)
        return 2
    run = PipelineRun(
        pipeline=args.pipeline,
        task=args.task,
        started_at=utcnow(),
        expected_interval_seconds=args.expected_interval_seconds,
    )
    try:
        code = subprocess.call(command)
    except OSError as exc:
        print(f"error: cannot start {command[0]}: {exc}", file=sys.stderr)
        code = 127
    if code == 0:
        run.finish("success")
    else:
        run.error_type = "NonZeroExit"
        run.error_message = f"`{' '.join(command)}` exited with code {code}"
        run.finish("failed")
    _record(args, run)
    if run.status == "failed" and args.alert:
        dispatcher_from_env().dispatch([alert_for_run(run)])
    print(json.dumps({"run_id": run.run_id, "status": run.status, "duration_seconds": run.duration_seconds}))
    return code


def _cmd_record_run(args: argparse.Namespace) -> int:
    finished = args.finished_at or datetime.now(timezone.utc).isoformat()
    try:
        run = PipelineRun(
            pipeline=args.pipeline,
            task=args.task,
            started_at=args.started_at,
            rows_in=args.rows_in,
            rows_out=args.rows_out,
            error_message=args.error_message,
            error_type="ReportedFailure" if args.status == "failed" else None,
            expected_interval_seconds=args.expected_interval_seconds,
        )
        run.finish(args.status, parse_ts(finished))
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    _record(args, run)
    print(json.dumps(run.to_dict(), sort_keys=True))
    return 0


def _cmd_run_metrics(args: argparse.Namespace) -> int:
    try:
        runs = JsonlRunStore(args.store).runs()
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    text = render(run_metric_families(runs))
    if args.metrics_out:
        write_textfile(args.metrics_out, text)
    else:
        sys.stdout.write(text)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="fleetflow_observability", description=__doc__.split("\n")[0])
    sub = parser.add_subparsers(dest="cmd", required=True)

    f = sub.add_parser("freshness", help="evaluate dbt source freshness results")
    f.add_argument("--sources-json", required=True)
    f.add_argument("--metrics-out")
    f.add_argument("--summary-md")
    f.add_argument("--expect", help='JSON {"table": "pass|warn|error"} the results must match exactly')
    f.add_argument("--fail-on", choices=("never",) + SEVERITY_ORDER[1:], default="error")
    f.add_argument("--alert", action="store_true", help="dispatch alerts (webhook from env, else log)")
    f.add_argument("--alert-min-status", choices=SEVERITY_ORDER[1:], default="warn")
    f.set_defaults(func=_cmd_freshness)

    t = sub.add_parser("track", help="run a command and record it as a pipeline run")
    t.add_argument("--store", required=True)
    t.add_argument("--pipeline", required=True)
    t.add_argument("--task", required=True)
    t.add_argument("--expected-interval-seconds", type=float)
    t.add_argument("--metrics-out")
    t.add_argument("--alert", action="store_true")
    t.add_argument("command", nargs=argparse.REMAINDER)
    t.set_defaults(func=_cmd_track)

    r = sub.add_parser("record-run", help="append a finished run")
    r.add_argument("--store", required=True)
    r.add_argument("--pipeline", required=True)
    r.add_argument("--task", required=True)
    r.add_argument("--status", choices=("success", "failed"), required=True)
    r.add_argument("--started-at", required=True)
    r.add_argument("--finished-at")
    r.add_argument("--rows-in", type=int)
    r.add_argument("--rows-out", type=int)
    r.add_argument("--error-message")
    r.add_argument("--expected-interval-seconds", type=float)
    r.add_argument("--metrics-out")
    r.set_defaults(func=_cmd_record_run)

    m = sub.add_parser("run-metrics", help="render run-store metrics")
    m.add_argument("--store", required=True)
    m.add_argument("--metrics-out")
    m.set_defaults(func=_cmd_run_metrics)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")
    args = build_parser().parse_args(argv)
    return args.func(args)

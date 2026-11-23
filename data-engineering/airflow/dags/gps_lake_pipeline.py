"""Opt-in local GPS lakehouse DAG: replay -> reconcile -> load -> dbt.

This DAG has NO automatic schedule and never approves dispatch routes or
provisions infrastructure. It is for a reviewer-operated, isolated local
analytics environment using an explicitly supplied fixture path.
"""

from __future__ import annotations

import asyncio
import os
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path

from airflow.decorators import dag, task


@dag(
    dag_id="fleetflow_gps_analytics_replay",
    description="Explicit local GPS Parquet replay, reconciliation and dbt",
    schedule=None,
    start_date=datetime(2026, 1, 1, tzinfo=timezone.utc),  # noqa: UP017 - Airflow 2.8.2 image runs Python 3.8
    catchup=False,
    max_active_runs=1,
    default_args={"owner": "fleetflow", "retries": 1,
                  "retry_delay": timedelta(seconds=30)},
    tags=["fleetflow", "p2", "local-only", "gps", "dbt"],
)
def gps_analytics_replay():
    @task(execution_timeout=timedelta(minutes=5))
    def replay_snapshot(**context) -> dict[str, str]:
        from src.lakehouse.replay import replay

        conf = context["dag_run"].conf or {}
        source_value = conf.get("source_path")
        approved_root = os.environ.get("FLEETFLOW_ANALYTICS_INPUT_DIR")
        output_root = os.environ.get("FLEETFLOW_ANALYTICS_OUTPUT_DIR")
        if not isinstance(source_value, str) or not approved_root or not output_root:
            raise ValueError("Explicit source_path and approved input/output root required")

        source = Path(source_value).resolve()
        allowed = Path(approved_root).resolve()
        if not source.is_file() or not source.is_relative_to(allowed):
            raise ValueError("Source must be a real file within the approved input directory")
        dest = Path(output_root).resolve()
        if source == dest or dest.is_relative_to(allowed):
            raise ValueError("Output must not overwrite the approved raw input directory")
        run_dir, manifest = replay(source, dest)
        return {"run_dir": str(run_dir), "run_key": manifest["run_key"]}

    @task(execution_timeout=timedelta(minutes=5))
    def reconcile_snapshot(snapshot: dict[str, str]) -> dict[str, str]:
        from src.lakehouse.reconcile import reconcile

        evidence = reconcile(Path(snapshot["run_dir"]))
        if evidence["run_key"] != snapshot["run_key"]:
            raise ValueError("Replay reconciliation produced a mismatched run key")
        return snapshot

    @task(execution_timeout=timedelta(minutes=5))
    def import_analytics(snapshot: dict[str, str]) -> dict[str, str]:
        from src.lakehouse.load_postgres import load

        database_url = os.environ.get("DATABASE_URL")
        if not database_url:
            raise ValueError("Isolated DATABASE_URL is required")
        result = asyncio.run(load(Path(snapshot["run_dir"]), database_url))
        if result["run_key"] != snapshot["run_key"]:
            raise ValueError("Database load returned a mismatched run key")
        return snapshot

    @task(execution_timeout=timedelta(minutes=10))
    def build_dbt_mart(snapshot: dict[str, str]) -> str:
        # A short, safe argv list: no shell interpolation or user-supplied SQL.
        directory = Path(__file__).resolve().parents[2] / "dbt"
        result = subprocess.run(
            [
                "dbt", "build",
                "--project-dir", str(directory),
                "--profiles-dir", str(directory),
                "--select", "+fct_gps_hourly",
            ],
            check=True,
            timeout=600,
            capture_output=True,
            text=True,
            env=os.environ.copy(),
        )
        if not result.stdout:
            raise RuntimeError("dbt did not provide an execution summary")
        return snapshot["run_key"]

    build_dbt_mart(import_analytics(reconcile_snapshot(replay_snapshot())))


gps_analytics_replay()

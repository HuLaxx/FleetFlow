"""FleetFlow manual hourly-demand evaluation, not a deployed forecast service.

No scheduled fabricated default demand=5, confidence=0.8, or invented driver
positioning recommendation. Operator explicitly supplies an audited hourly CSV
and artifact directory, using code mounted into the Airflow container.
"""

import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from airflow import DAG
from airflow.operators.python import PythonOperator


def evaluate_historical_demand(**context):
    """One-off chronological benchmark; never sends dispatch instructions."""
    source = os.environ.get("FLEETFLOW_HOURLY_COUNTS_CSV")
    output_dir = os.environ.get("FLEETFLOW_EVALUATION_ARTIFACT_DIR")
    script = os.environ.get(
        "FLEETFLOW_FORECAST_BASELINE_SCRIPT",
        "/opt/fleetflow/backend/src/analytics/forecast_baselines.py",
    )
    if not source or not output_dir:
        raise RuntimeError("Set explicit hourly-counts CSV and evaluation artifact directory")
    if not Path(source).is_file() or not Path(script).is_file():
        raise FileNotFoundError("Expected mounted CSV and forecast baseline implementation")
    target = Path(output_dir) / "manual-hourly-demand-baselines.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [sys.executable, script, "--input", source, "--output", str(target)],
        check=True,
        timeout=120,
    )
    return {"mode": "manual_evaluation_only", "result_artifact": str(target)}


with DAG(
    dag_id="hourly_demand_forecast",
    description="Manual chronological evaluation of supplied hourly observations only",
    start_date=datetime(2026, 1, 1, tzinfo=timezone.utc),
    schedule_interval=None,
    catchup=False,
    max_active_runs=1,
    tags=["fleetflow", "manual", "forecast-baseline"],
) as dag:
    PythonOperator(task_id="evaluate_historical_demand", python_callable=evaluate_historical_demand)

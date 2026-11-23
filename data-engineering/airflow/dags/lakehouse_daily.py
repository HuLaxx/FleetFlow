"""FleetFlow lakehouse - daily batch DAG.

bronze (landed CSV) -> quality gate -> Spark silver (partition overwrite) -> dbt gold -> dbt tests

* One run processes its logical date (``{{ ds }}``), so ``airflow dags backfill`` re-processes
  history day by day. Every task is idempotent: the quality gate rewrites its outputs, Spark
  overwrites only that date's partition, and the dbt fact is incremental with a unique key.
* A failed quality gate stops the run before anything reaches the warehouse.
* ``max_active_runs=1`` keeps backfills ordered so incremental dbt merges stay consistent.
"""
from __future__ import annotations

import os
from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.bash import BashOperator

REPO = os.environ.get("FLEETFLOW_REPO", "/opt/fleetflow")
LAKE = os.environ.get("FLEETFLOW_LAKE_ROOT", f"{REPO}/data/lakehouse")
ENV = {"PYTHONPATH": f"{REPO}/data-engineering", "PATH": os.environ.get("PATH", "")}

default_args = {
    "owner": "data-engineering",
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
    "retry_exponential_backoff": True,
    "execution_timeout": timedelta(hours=1),
}

with DAG(
    dag_id="fleetflow_lakehouse_daily",
    description="Bronze -> quality gate -> Spark silver -> dbt gold for one delivery date",
    start_date=datetime(2026, 1, 1),
    schedule="0 2 * * *",          # 02:00 UTC, after the previous day's deliveries have landed
    catchup=True,
    max_active_runs=1,
    default_args=default_args,
    tags=["fleetflow", "lakehouse", "spark", "dbt"],
) as dag:
    quality_gate = BashOperator(
        task_id="quality_gate",
        bash_command=f"python -m lakehouse.quality --root {LAKE} --min-pass-rate 0.95",
        env=ENV,
    )

    spark_silver = BashOperator(
        task_id="spark_silver",
        bash_command=(f"python -m lakehouse.spark_job --root {LAKE} "
                      "--start-date {{ ds }} --end-date {{ ds }}"),
        env=ENV,
    )

    dbt_build = BashOperator(
        task_id="dbt_build_gold",
        bash_command=(f"cd {REPO}/data-engineering/dbt_warehouse && "
                      "dbt build --profiles-dir . --target ${DBT_TARGET:-duckdb}"),
        env={**ENV, "DBT_TARGET": os.environ.get("DBT_TARGET", "duckdb")},
    )

    quality_gate >> spark_silver >> dbt_build

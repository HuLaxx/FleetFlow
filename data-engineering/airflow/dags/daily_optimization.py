"""FleetFlow manual dispatch readiness DAG (read-only, no route assignment).

This DAG intentionally does NOT call the optimization write API, insert rows,
auto-approve routes, or contain hard-coded depot coordinates. Dispatchers use
the authenticated FastAPI plan/approve workflow separately. Schedule remains
off until role-appropriate operational review and real Airflow deployment.
"""

import os
from datetime import date, datetime, timezone

from airflow import DAG
from airflow.operators.python import PythonOperator
from sqlalchemy import create_engine, text


def inspect_dispatch_readiness(**context):
    """Return only aggregate counts from an explicitly configured read-only DB."""
    dag_run = context.get("dag_run")
    conf = getattr(dag_run, "conf", None) or {}
    route_day = conf.get("route_date")
    if not isinstance(route_day, str):
        raise ValueError("Manual DAG requires explicit route_date in YYYY-MM-DD")
    requested = date.fromisoformat(route_day)
    url = os.environ.get("FLEETFLOW_ANALYTICS_DATABASE_URL", "")
    if not url.startswith(("postgresql://", "postgresql+psycopg2://")):
        raise RuntimeError("A sync PostgreSQL analytics URL is required")

    engine = create_engine(url, pool_pre_ping=True)
    try:
        with engine.connect() as connection:
            with connection.begin():
                connection.exec_driver_sql("SET TRANSACTION READ ONLY")
                pending = connection.scalar(
                    text(
                        "SELECT COUNT(*) FROM orders "
                        "WHERE delivery_date = :day AND status = 'pending'"
                    ),
                    {"day": requested},
                )
                available = connection.scalar(
                    text(
                        "SELECT COUNT(*) FROM vehicles v JOIN drivers d "
                        "ON d.id=v.current_driver_id "
                        "WHERE v.status='available' AND d.status='available'"
                    )
                )
                planned = connection.scalar(
                    text(
                        "SELECT COUNT(*) FROM routes "
                        "WHERE route_date=:day AND status='planned'"
                    ),
                    {"day": requested},
                )
                approved = connection.scalar(
                    text(
                        "SELECT COUNT(*) FROM routes "
                        "WHERE route_date=:day AND status='approved'"
                    ),
                    {"day": requested},
                )
    finally:
        engine.dispose()

    # No customer names, addresses, GPS points or credentials in output.
    return {
        "route_date": requested.isoformat(),
        "pending_orders": pending,
        "available_driver_vehicles": available,
        "planned_unapproved_routes": planned,
        "dispatcher_approved_routes": approved,
        "mode": "read_only_manual_review",
    }


with DAG(
    dag_id="daily_route_optimization",
    description="Manual read-only dispatch readiness; route plan/approve stays in authenticated API",
    start_date=datetime(2026, 1, 1, tzinfo=timezone.utc),
    schedule_interval=None,
    catchup=False,
    max_active_runs=1,
    tags=["fleetflow", "read-only", "manual", "dispatch"],
) as dag:
    PythonOperator(task_id="inspect_dispatch_readiness", python_callable=inspect_dispatch_readiness)

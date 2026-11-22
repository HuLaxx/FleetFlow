"""Load reconciled native-route GPS events into disposable PostGIS only."""

import argparse
import asyncio
import json
import os
from pathlib import Path
from uuid import UUID

import asyncpg
import pyarrow.parquet as pq
from sqlalchemy.engine import make_url

from src.lakehouse.reconcile import reconcile


def read_clean_rows(run_dir: Path) -> list[dict]:
    """Read exact Parquet files without Hive partition discovery.

    Clean Parquet already includes event_date as a physical string column,
    while parent directories use event_date=... partition labels. PyArrow's
    dataset reader infers a second dictionary-typed event_date column and
    can fail merging these incompatible representations. ParquetFile reads
    each verified file's physical schema only.
    """
    paths = sorted((run_dir / "clean").rglob("*.parquet"))
    return [row for path in paths for row in pq.ParquetFile(path).read().to_pylist()]


async def load(run_dir: Path, database_url: str) -> dict[str, int]:
    verified = reconcile(run_dir)
    url = make_url(database_url)
    if (
        url.drivername not in {"postgresql", "postgresql+asyncpg"}
        or url.database != "fleetflow_test"
        or url.host not in {"localhost", "127.0.0.1"}
    ):
        raise ValueError("Only isolated local fleetflow_test may be modified")
    rows = read_clean_rows(run_dir)
    if len(rows) != verified["accepted"]:
        raise ValueError("Reconciled clean-event count mismatch")
    conn = await asyncpg.connect(
        user=url.username,
        password=url.password,
        host=url.host,
        port=url.port or 5432,
        database=url.database,
    )
    inserted = reused = 0
    try:
        async with conn.transaction():
            for row in rows:
                if not row.get("route_id"):
                    raise ValueError("Native route identity required for route mart")
                key = (verified["run_key"], UUID(row["event_id"]))
                values = (
                    *key,
                    UUID(row["route_id"]),
                    UUID(row["driver_id"]),
                    UUID(row["vehicle_id"]),
                    row["event_time"],
                    row["latitude"],
                    row["longitude"],
                )
                result = await conn.fetchrow(
                    """INSERT INTO public.gps_route_events
                    (run_key,event_id,route_id,driver_id,vehicle_id,event_time,latitude,longitude)
                    VALUES ($1,$2,$3,$4,$5,$6,$7,$8)
                    ON CONFLICT (run_key,event_id) DO NOTHING RETURNING event_id""",
                    *values,
                )
                if result:
                    inserted += 1
                else:
                    existing = await conn.fetchrow(
                        """SELECT route_id,driver_id,vehicle_id,event_time,latitude,longitude
                        FROM public.gps_route_events
                        WHERE run_key=$1 AND event_id=$2 FOR UPDATE""",
                        *key,
                    )
                    if existing is None or tuple(existing) != values[2:]:
                        raise ValueError("Conflicting immutable route GPS event")
                    reused += 1
    finally:
        await conn.close()
    return {"inserted": inserted, "reused": reused}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("run_dir", type=Path)
    args = parser.parse_args()
    if not os.getenv("DATABASE_URL"):
        parser.error("DATABASE_URL required")
    print(json.dumps(asyncio.run(load(args.run_dir, os.environ["DATABASE_URL"]))))


if __name__ == "__main__":
    main()

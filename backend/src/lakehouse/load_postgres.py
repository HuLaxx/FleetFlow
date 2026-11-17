"""Load independently reconciled GPS Parquet hours into a local dbt source.

Local-only, content-addressed and transactionally idempotent. Refuses to
overwrite a previously loaded (run, vehicle, hour) with different facts.
Requires reviewed SQL schema data-engineering/sql/01_gps_hourly_curated.sql.
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import UUID

import asyncpg
import pyarrow.parquet as pq
from sqlalchemy.engine import make_url

from src.lakehouse.reconcile import reconcile


def _digest(row: dict[str, Any]) -> str:
    values = {
        key: value.isoformat() if isinstance(value, datetime) else value
        for key, value in row.items()
    }
    return hashlib.sha256(
        json.dumps(values, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    ).hexdigest()


async def load(run_dir: Path, database_url: str) -> dict[str, int | str]:
    """Verify all raw/clean/curated artifacts before any database mutation."""
    results = reconcile(run_dir)
    url = make_url(database_url)
    if (
        url.drivername not in {"postgresql+asyncpg", "postgresql"}
        or url.database != "fleetflow_test"
        or url.host not in {"localhost", "127.0.0.1"}
    ):
        raise ValueError("Only local isolated fleetflow_test may be modified")

    manifest = json.loads((Path(run_dir) / "manifest.json").read_text(encoding="utf-8"))
    mart = Path(run_dir) / "curated/hourly_vehicle_telemetry.parquet"
    rows = pq.ParquetFile(mart).read().to_pylist()
    conn = await asyncpg.connect(
        user=url.username, password=url.password, host=url.host,
        port=url.port or 5432, database=url.database,
    )
    inserted = 0
    reused = 0
    try:
        async with conn.transaction():
            for row in rows:
                fingerprint = _digest(row)
                key = (results["run_key"], UUID(row["vehicle_id"]), row["hour_utc"])
                created = await conn.fetchval(
                    """
                    INSERT INTO public.gps_hourly_curated (
                        run_key, source_sha256, vehicle_id, hour_utc,
                        event_count, late_event_count, avg_speed_kmh,
                        last_event_time, last_latitude, last_longitude, row_sha256
                    ) VALUES (
                        $1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11
                    ) ON CONFLICT (run_key,vehicle_id,hour_utc)
                    DO NOTHING RETURNING row_sha256
                    """,
                    results["run_key"], manifest["source_sha256"], key[1], key[2],
                    row["event_count"], row["late_event_count"], row["avg_speed_kmh"],
                    row["last_event_time"], row["last_latitude"], row["last_longitude"],
                    fingerprint,
                )
                if created is not None:
                    inserted += 1
                    continue
                existing = await conn.fetchval(
                    """
                    SELECT row_sha256 FROM public.gps_hourly_curated
                    WHERE run_key = $1 AND vehicle_id = $2 AND hour_utc = $3
                    FOR UPDATE
                    """,
                    *key,
                )
                if existing != fingerprint:
                    raise ValueError("Immutable lake run conflicts with PostgreSQL facts")
                reused += 1
    finally:
        await conn.close()
    return {
        "run_key": str(results["run_key"]),
        "validated_clean_events": int(results["accepted"]),
        "inserted_vehicle_hours": inserted,
        "idempotent_existing_vehicle_hours": reused,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Load verified local GPS Parquet to dbt source")
    parser.add_argument("run_dir", type=Path)
    args = parser.parse_args()
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        parser.error("DATABASE_URL is required")
    print(json.dumps(asyncio.run(load(args.run_dir, database_url)), sort_keys=True))


if __name__ == "__main__":
    main()

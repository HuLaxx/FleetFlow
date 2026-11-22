"""Regression: physical event_date and Hive directory must not collide."""
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

from src.lakehouse.load_route_events import read_clean_rows


def test_partitioned_clean_parquet_reads_physical_event_date(tmp_path: Path):
    parent = tmp_path / "clean" / "event_date=2026-11-22"
    parent.mkdir(parents=True)
    path = parent / "telemetry.parquet"
    pq.write_table(
        pa.table({
            "event_date": pa.array(["2026-11-22"], type=pa.string()),
            "event_id": pa.array(["synthetic-id"], type=pa.string()),
        }),
        path,
    )
    assert read_clean_rows(tmp_path) == [
        {"event_date": "2026-11-22", "event_id": "synthetic-id"}
    ]

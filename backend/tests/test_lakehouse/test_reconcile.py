"""Adversarial GPS lake reconciliation: tests detect forged/consistent manifests too."""

import json
from datetime import timedelta

import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from src.lakehouse.reconcile import ReconciliationError, reconcile
from src.lakehouse.replay import replay, sha256_file
from tests.test_lakehouse.test_replay import event, write_events


def fixture_run(tmp_path):
    source = tmp_path / "events.jsonl"
    one = event("11111111-1111-4111-8111-111111111111", "2026-11-12T10:00:00Z", speed=10)
    two = event("22222222-2222-4222-8222-222222222222", "2026-11-12T10:20:00Z", speed=20)
    late = event("33333333-3333-4333-8333-333333333333", "2026-11-12T09:20:00Z")
    conflict = dict(one, speed_kmh=100)
    write_events(source, [one, two, late, two, conflict])
    return replay(source, tmp_path / "lake")


def _forge_checksum(run_dir, relative):
    manifest_path = run_dir / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["artifact_sha256"][relative] = sha256_file(run_dir / relative)
    manifest_path.write_text(json.dumps(manifest, sort_keys=True), encoding="utf-8")


def test_reconciliation_is_deterministic_and_counts_late_duplicate_and_quarantine(tmp_path):
    run_dir, _ = fixture_run(tmp_path)
    first = reconcile(run_dir)
    assert first == reconcile(run_dir)
    assert first == {
        "status": "reconciled",
        "contract": "fleetflow.gps.v1",
        "run_key": run_dir.name,
        "accepted": 3,
        "duplicates": 1,
        "late": 1,
        "quarantined": 1,
        "clean_partitions": 1,
        "curated_vehicle_hours": 2,
        "verified_artifacts": 4,
    }


def test_reconciles_empty_input_with_explicit_empty_partition(tmp_path):
    source = tmp_path / "empty.jsonl"
    source.write_text("", encoding="utf-8")
    run_dir, _ = replay(source, tmp_path / "lake")
    data = reconcile(run_dir)
    assert data["accepted"] == 0
    assert data["curated_vehicle_hours"] == 0
    assert data["clean_partitions"] == 1


def test_unlisted_or_tampered_file_fails_before_analytics(tmp_path):
    run_dir, _ = fixture_run(tmp_path)
    relative = "curated/hourly_vehicle_telemetry.parquet"
    path = run_dir / relative
    path.write_bytes(b"not parquet")
    with pytest.raises(ReconciliationError, match="tampered"):
        reconcile(run_dir)


@pytest.mark.parametrize(
    "field,change,error",
    [
        ("event_count", 100, "event count"),
        ("late_event_count", 100, "late count"),
        ("avg_speed_kmh", 999.0, "avg_speed_kmh"),
        ("last_latitude", 0.0, "last_latitude"),
    ],
)
def test_corrupt_curated_facts_rejected_even_with_matching_manifest_hash(
    tmp_path, field, change, error
):
    run_dir, _ = fixture_run(tmp_path)
    relative = "curated/hourly_vehicle_telemetry.parquet"
    path = run_dir / relative
    table = pq.ParquetFile(path).read()
    column = table.schema.get_field_index(field)
    new_values = [change, *table.column(column).to_pylist()[1:]]
    table = table.set_column(
        column, table.schema.field(column), pa.array(new_values, type=table.schema.field(column).type)
    )
    pq.write_table(table, path)
    _forge_checksum(run_dir, relative)
    with pytest.raises(ReconciliationError, match=error):
        reconcile(run_dir)


def test_duplicate_id_in_clean_detected_even_if_manifest_updated(tmp_path):
    run_dir, _ = fixture_run(tmp_path)
    relative = "clean/event_date=2026-11-12/telemetry.parquet"
    path = run_dir / relative
    table = pq.ParquetFile(path).read()
    ids = table.column("event_id").to_pylist()
    ids[1] = ids[0]
    table = table.set_column(
        table.schema.get_field_index("event_id"), "event_id", pa.array(ids, type=pa.string())
    )
    pq.write_table(table, path)
    _forge_checksum(run_dir, relative)
    with pytest.raises(ReconciliationError, match="Duplicate IDs"):
        reconcile(run_dir)


def test_partition_day_mismatch_is_detected_even_if_checksum_updated(tmp_path):
    run_dir, _ = fixture_run(tmp_path)
    relative = "clean/event_date=2026-11-12/telemetry.parquet"
    path = run_dir / relative
    table = pq.ParquetFile(path).read()
    table = table.set_column(
        table.schema.get_field_index("event_date"), "event_date",
        pa.array(["2026-11-13"] * table.num_rows, type=pa.string())
    )
    pq.write_table(table, path)
    _forge_checksum(run_dir, relative)
    with pytest.raises(ReconciliationError, match="Event date"):
        reconcile(run_dir)


def test_reconciliation_refuses_manifest_path_traversal(tmp_path):
    run_dir, _ = fixture_run(tmp_path)
    path = run_dir / "manifest.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    data["artifacts"].append("../outside.parquet")
    data["artifact_sha256"]["../outside.parquet"] = "bad"
    path.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(ReconciliationError, match="Unsafe artifact path"):
        reconcile(run_dir)


def test_empty_run_cannot_claim_nonzero_accepted_count(tmp_path):
    source = tmp_path / "empty.jsonl"
    source.write_text("", encoding="utf-8")
    run_dir, _ = replay(source, tmp_path / "lake")
    manifest_file = run_dir / "manifest.json"
    manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
    manifest["counts"]["accepted"] = 1
    manifest_file.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(ReconciliationError, match="row count"):
        reconcile(run_dir)

"""Persisted Parquet data quality must reconcile even with forged checksums."""

import json
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from src.lakehouse.quality import audit_run
from src.lakehouse.replay import replay, sha256_file

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures/demo_gps_events.jsonl"


def _resign(root, relative):
    manifest_path = root / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["artifact_sha256"][relative] = sha256_file(root / relative)
    manifest_path.write_text(json.dumps(manifest, sort_keys=True), encoding="utf-8")


def test_raw_clean_curated_all_reconcile_and_retries_are_immutable(tmp_path):
    root, manifest = replay(FIXTURE, tmp_path / "lake")
    report = audit_run(root)
    assert report["status"] == "reconciled"
    assert report["run_key"] == manifest["run_key"]
    assert report["accepted_events"] == 3
    assert report["duplicate_events"] == 1
    assert report["quarantined_events"] == 1
    assert report["late_events"] == 1
    assert report["source_rows"] == 5
    assert report["curated_hourly_groups"] == 2
    again, same_manifest = replay(FIXTURE, tmp_path / "lake")
    assert again == root
    assert same_manifest == manifest
    assert audit_run(again) == report


def test_corrupted_aggregate_is_detected_even_when_checksum_is_updated(tmp_path):
    root, _ = replay(FIXTURE, tmp_path / "lake")
    relative = "curated/hourly_vehicle_telemetry.parquet"
    path = root / relative
    table = pq.ParquetFile(path).read()
    rows = table.to_pylist()
    rows[0]["event_count"] += 1
    pq.write_table(pa.Table.from_pylist(rows, schema=table.schema), path)
    _resign(root, relative)
    with pytest.raises(ValueError, match="Curated event counts"):
        audit_run(root)


def test_clean_partition_with_invalid_event_date_fails_even_when_resigned(tmp_path):
    root, _ = replay(FIXTURE, tmp_path / "lake")
    relative = "clean/event_date=2026-11-12/telemetry.parquet"
    path = root / relative
    table = pq.ParquetFile(path).read()
    rows = table.to_pylist()
    rows[0]["event_date"] = "2026-11-11"
    pq.write_table(pa.Table.from_pylist(rows, schema=table.schema), path)
    _resign(root, relative)
    with pytest.raises(ValueError, match="event date mismatch"):
        audit_run(root)


def test_raw_and_curated_count_mismatch_with_recomputed_hash_fails(tmp_path):
    root, _ = replay(FIXTURE, tmp_path / "lake")
    relative = "raw/events.jsonl"
    with (root / relative).open("a", encoding="utf-8") as handle:
        handle.write('{"unexpected":"raw event"}\n')
    _resign(root, relative)
    with pytest.raises(ValueError, match="Source reconciliation mismatch"):
        audit_run(root)


def test_checksum_modification_and_path_traversal_fail_closed(tmp_path):
    root, _ = replay(FIXTURE, tmp_path / "lake")
    relative = "quarantine/rejected.jsonl"
    with (root / relative).open("a", encoding="utf-8") as handle:
        handle.write('{"reason":"tampered"}\n')
    with pytest.raises(ValueError, match="checksum mismatch"):
        audit_run(root)

    root, _ = replay(FIXTURE, tmp_path / "other-lake")
    manifest_path = root / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["artifacts"].append("../external.parquet")
    manifest["artifact_sha256"]["../external.parquet"] = "0" * 64
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(ValueError, match="Unsafe or missing"):
        audit_run(root)


def test_empty_invalid_only_run_reconciles_without_fake_metrics(tmp_path):
    source = tmp_path / "invalid.jsonl"
    source.write_text("{invalid JSON\n", encoding="utf-8")
    root, _ = replay(source, tmp_path / "lake")
    report = audit_run(root)
    assert report["accepted_events"] == 0
    assert report["curated_hourly_groups"] == 0
    assert report["quarantined_events"] == 1

"""Fail-closed verification of synthetic source-order to GPS identity receipts.

This verifier is intentionally NOT a replacement for a real broker/Parquet/dbt
integration run. It refuses to infer an absent route-to-vehicle association.
"""
import argparse
import hashlib
import json
import os
import tempfile
from pathlib import Path
from uuid import UUID


class LineageError(ValueError):
    pass


def _uuid(value, field):
    if not isinstance(value, str):
        raise LineageError(f"{field}: missing string UUID")
    try:
        return str(UUID(value))
    except (ValueError, AttributeError) as exc:
        raise LineageError(f"{field}: invalid UUID") from exc


def _unique_json_object(pairs):
    """Reject ambiguous duplicate JSON keys rather than trusting last-key-wins."""
    result = {}
    for key, value in pairs:
        if key in result:
            raise LineageError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _load_unique_json(payload):
    return json.loads(payload, object_pairs_hook=_unique_json_object)


def verify(route, gps, analytics, source_bytes):
    """Return sanitized, verified identifiers; reject missing or inconsistent joins.

    route: persisted solver/approval/dispatch receipt, not an invented fixture
    gps: broker-acknowledged, database-accepted GPS receipt
    analytics: independently observed dbt fact + Parquet event IDs
    """
    if not all(isinstance(item, dict) for item in (route, gps, analytics)):
        raise LineageError("all receipts must be JSON objects")
    if route.get("algorithm_used") != "ortools-cvrptw-haversine":
        raise LineageError("actual OR-Tools persisted assignment required")
    if route.get("approval_status") != "approved" or route.get("dispatch_status") != "in_progress":
        raise LineageError("route must be explicitly approved and started")
    # A status string is not evidence of an authorised, versioned decision.
    # Require independently persisted approval-audit metadata before accepting
    # any order-to-dispatch lineage receipt.
    _uuid(route.get("approval_audit_id"), "route.approval_audit_id")
    _uuid(route.get("approver_id"), "route.approver_id")
    version = route.get("candidate_version")
    if type(version) is not int or version < 1:
        raise LineageError("route.candidate_version: positive integer required")
    approved_at = route.get("approved_at")
    if not isinstance(approved_at, str):
        raise LineageError("route.approved_at: timezone-aware timestamp required")
    try:
        from datetime import datetime, timezone
        approval_time = datetime.fromisoformat(approved_at.replace("Z", "+00:00"))
        if approval_time.tzinfo is None or approval_time.utcoffset() is None:
            raise ValueError("missing timezone")
        if approval_time.astimezone(timezone.utc).year < 2020:
            raise ValueError("implausible approval timestamp")
    except ValueError as exc:
        raise LineageError("route.approved_at: valid timezone-aware timestamp required") from exc
    if route.get("broker_ack") is not True or gps.get("broker_ack") is not True:
        raise LineageError("both dispatch and GPS broker acknowledgements required")
    if gps.get("database_accepted") is not True:
        raise LineageError("GPS event not accepted in PostGIS")
    ids = {}
    for field in ("order_id", "route_id", "driver_id", "vehicle_id"):
        ids[field] = _uuid(route.get(field), f"route.{field}")
    for field in ("route_id", "driver_id", "vehicle_id"):
        if _uuid(gps.get(field), f"gps.{field}") != ids[field]:
            raise LineageError(f"GPS {field} does not match dispatched route")
    event_id = _uuid(gps.get("event_id"), "gps.event_id")
    for field in ("raw_event_id", "clean_event_id", "curated_event_id", "dbt_event_id"):
        if _uuid(analytics.get(field), f"analytics.{field}") != event_id:
            raise LineageError(f"{field} differs from accepted GPS event")
    if _uuid(analytics.get("order_id"), "analytics.order_id") != ids["order_id"]:
        raise LineageError("dbt order association mismatch")
    if _uuid(analytics.get("route_id"), "analytics.route_id") != ids["route_id"]:
        raise LineageError("dbt route association mismatch")
    # JSON booleans compare equal to integers in Python (True == 1 and
    # False == 0). Do not let a malformed receipt masquerade as measured
    # database row counts.
    if (type(analytics.get("dbt_row_count")) is not int
            or analytics["dbt_row_count"] != 1
            or type(analytics.get("duplicate_count")) is not int
            or analytics["duplicate_count"] != 0):
        raise LineageError("analytical fact counts must be exact integers: one row, zero duplicates")
    digest = analytics.get("source_sha256")
    if not isinstance(digest, str) or len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
        raise LineageError("missing or malformed source digest")
    if not isinstance(source_bytes, bytes):
        raise LineageError("source bytes must be bytes")
    if hashlib.sha256(source_bytes).hexdigest() != digest:
        raise LineageError("actual source bytes do not match analytics digest")
    # A matching hash alone does not establish that these bytes describe the
    # GPS event being claimed. Require a single canonical source JSON event.
    try:
        source = _load_unique_json(source_bytes.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise LineageError("source must be a valid JSON event") from exc
    if not isinstance(source, dict):
        raise LineageError("source must be a JSON object")
    for field, expected in (("event_id", event_id), ("driver_id", ids["driver_id"]), ("vehicle_id", ids["vehicle_id"])):
        if _uuid(source.get(field), f"source.{field}") != expected:
            raise LineageError(f"source {field} differs from accepted GPS event")
    # An order-linked acceptance must never treat missing source order/route
    # identifiers as optional: a GPS-only event cannot prove order lineage.
    for field in ("order_id", "route_id"):
        if _uuid(source.get(field), f"source.{field}") != ids[field]:
            raise LineageError(f"source {field} differs from dispatched route")
    return {"status": "verified", **ids, "gps_event_id": event_id, "source_sha256": digest}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--route", required=True, type=Path)
    parser.add_argument("--gps", required=True, type=Path)
    parser.add_argument("--analytics", required=True, type=Path)
    parser.add_argument("--source", required=True, type=Path, help="Original persisted synthetic source-event bytes")
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    # Never leave a stale success receipt after a failed or interrupted rerun.
    try:
        args.output.unlink(missing_ok=True)
    except OSError as exc:
        parser.exit(1, f"LINEAGE REJECTED: cannot clear prior output: {exc}\n")
    try:
        receipt = verify(*(_load_unique_json(p.read_text(encoding="utf-8")) for p in (args.route, args.gps, args.analytics)), source_bytes=args.source.read_bytes())
    except (LineageError, OSError, json.JSONDecodeError) as exc:
        parser.exit(1, f"LINEAGE REJECTED: {exc}\n")
    # Publish only complete evidence. Failed writes must not leave a partial
    # success receipt for a downstream CI stage to trust.
    staged = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=args.output.parent,
            prefix=f".{args.output.name}.", suffix=".tmp", delete=False,
        ) as handle:
            staged = Path(handle.name)
            json.dump(receipt, handle, sort_keys=True, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(staged, args.output)
    except OSError as exc:
        parser.exit(1, f"LINEAGE REJECTED: cannot publish verified output: {exc}\n")
    finally:
        if staged is not None:
            staged.unlink(missing_ok=True)



if __name__ == "__main__":
    main()

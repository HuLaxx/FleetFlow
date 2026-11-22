"""Fail-closed verification of synthetic source-order to GPS identity receipts.

This verifier is intentionally NOT a replacement for a real broker/Parquet/dbt
integration run. It refuses to infer an absent route-to-vehicle association.
"""
import argparse
import hashlib
import json
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
    if analytics.get("dbt_row_count") != 1 or analytics.get("duplicate_count") != 0:
        raise LineageError("missing or duplicate analytical fact")
    digest = analytics.get("source_sha256")
    if not isinstance(digest, str) or len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
        raise LineageError("missing or malformed source digest")
    if not isinstance(source_bytes, bytes):
        raise LineageError("source bytes must be bytes")
    if hashlib.sha256(source_bytes).hexdigest() != digest:
        raise LineageError("actual source bytes do not match analytics digest")
    return {"status": "verified", **ids, "gps_event_id": event_id, "source_sha256": digest}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--route", required=True, type=Path)
    parser.add_argument("--gps", required=True, type=Path)
    parser.add_argument("--analytics", required=True, type=Path)
    parser.add_argument("--source", required=True, type=Path, help="Original persisted synthetic source-event bytes")
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    try:
        receipt = verify(*(json.loads(p.read_text(encoding="utf-8")) for p in (args.route, args.gps, args.analytics)), source_bytes=args.source.read_bytes())
    except (LineageError, OSError, json.JSONDecodeError) as exc:
        parser.exit(1, f"LINEAGE REJECTED: {exc}\n")
    args.output.write_text(json.dumps(receipt, sort_keys=True, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()

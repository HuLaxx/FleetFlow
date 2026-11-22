"""Independently reconcile the real synthetic order/approval/dispatch with GPS and dbt.

This is an *association* via a uniquely active route and matching driver/vehicle,
not a claim that the GPS event carries a native route/order foreign key.
Fail closed on ambiguous route assignments or unpublished broker events.
"""
import argparse
import asyncio
import json
from pathlib import Path
from uuid import UUID

from sqlalchemy import select

from src.database import AsyncSessionLocal, engine
from src.models import DispatchOutboxEvent, Order, Route, RouteApprovalAudit, RouteStop, Vehicle


def require_disposable_db():
    if engine.url.database != "fleetflow_test" or engine.url.host not in ("localhost", "127.0.0.1"):
        raise RuntimeError("Refusing non-disposable PostGIS database")


async def reconcile(order_receipt: dict, gps_receipt: dict, analytics_receipt: dict):
    require_disposable_db()
    order_id = UUID(order_receipt["order_id"])
    route_id = UUID(order_receipt["route_id"])
    driver_id = UUID(order_receipt["driver_id"])
    vehicle_id = UUID(order_receipt["vehicle_id"])
    event_id = UUID(gps_receipt["event_id"])
    if gps_receipt.get("outbox_published") is not True or gps_receipt.get("postgis_consumer_accepted") is not True:
        raise AssertionError("GPS broker publication and consumer receipt required")
    if gps_receipt.get("route_id") != str(route_id):
        raise AssertionError("Native GPS route identity missing or inconsistent")
    if gps_receipt.get("driver_id") != str(driver_id) or gps_receipt.get("vehicle_id") != str(vehicle_id):
        raise AssertionError("GPS identity does not match dispatch")
    if analytics_receipt.get("event_id") != str(event_id):
        raise AssertionError("Analytical event identity mismatch")
    if analytics_receipt.get("vehicle_id") != str(vehicle_id) or analytics_receipt.get("dbt_row_count") != 1:
        raise AssertionError("Analytical fact does not match dispatched vehicle")
    async with AsyncSessionLocal() as session:
        order = await session.get(Order, order_id)
        route = await session.get(Route, route_id)
        vehicle = await session.get(Vehicle, vehicle_id)
        if order is None or route is None or vehicle is None:
            raise AssertionError("Missing persisted order, route or vehicle")
        if route.algorithm_used != "ortools-cvrptw-haversine" or route.status != "in_progress":
            raise AssertionError("Real optimised and dispatched route required")
        if route.driver_id != driver_id or route.vehicle_id != vehicle_id:
            raise AssertionError("Persisted route assignment mismatch")
        if vehicle.current_driver_id != driver_id or vehicle.last_gps_event_id != event_id:
            raise AssertionError("GPS consumer did not persist matching driver/event")
        # Driver/vehicle alone cannot prove that a fix belongs to this dispatch.
        # Reject GPS recorded before the route actually started, including
        # missing timestamps. Both timestamps originate from the same PostGIS
        # database and are compared as stored (no client clock assumptions).
        if route.started_at is None or vehicle.last_gps_at is None:
            raise AssertionError("Persisted dispatch/GPS timestamps required")
        if vehicle.last_gps_at < route.started_at:
            raise AssertionError("GPS fix predates route dispatch; cannot associate with source order")
        stops = (await session.scalars(select(RouteStop).where(RouteStop.route_id == route_id))).all()
        if len(stops) != 1 or stops[0].order_id != order_id:
            raise AssertionError("Source order not assigned to exactly one route stop")
        audits = (await session.scalars(select(RouteApprovalAudit).where(RouteApprovalAudit.route_id == route_id))).all()
        if len(audits) != 1 or str(audits[0].id) != order_receipt["approval_audit_id"]:
            raise AssertionError("Authorised approval audit missing or inconsistent")
        if str(audits[0].approved_by_user_id) != order_receipt["approver_id"]:
            raise AssertionError("Approval actor mismatch")
        if audits[0].previous_status != "planned" or audits[0].new_status != "approved":
            raise AssertionError("Unexpected approval transition")
        # Do not associate one GPS fix with an arbitrary route when multiple
        # routes for the same driver/vehicle are active.
        active = (await session.scalars(select(Route).where(
            Route.driver_id == driver_id, Route.vehicle_id == vehicle_id,
            Route.status == "in_progress"
        ))).all()
        if len(active) != 1 or active[0].id != route_id:
            raise AssertionError("Ambiguous active route for GPS association")
        outbox = (await session.scalars(select(DispatchOutboxEvent).where(
            DispatchOutboxEvent.message_key == str(route_id),
            DispatchOutboxEvent.topic.in_(["routes.approved", "routes.started"])
        ))).all()
        if len(outbox) != 2 or {row.topic for row in outbox} != {"routes.approved", "routes.started"}:
            raise AssertionError("Approval/dispatch broker records missing")
        if any(row.status != "published" or row.published_at is None for row in outbox):
            raise AssertionError("Route broker publication not confirmed")
        if any(row.payload.get("route_id") != str(route_id) for row in outbox):
            raise AssertionError("Published route identity mismatch")
        gps_rows = (await session.scalars(select(DispatchOutboxEvent).where(
            DispatchOutboxEvent.id == event_id,
            DispatchOutboxEvent.topic == "gps.location"
        ))).all()
        if len(gps_rows) != 1 or gps_rows[0].status != "published":
            raise AssertionError("Exact GPS source not broker published")
    return {
        "status": "verified_synthetic_native_route_gps_lineage",
        "association_method": "native_route_id_plus_unique_active_route_and_persisted_source_order",
        "limitation": "GPS carries native route_id; individual order_id is resolved via the persisted route stop, not embedded in the GPS event",
        "order_id": str(order_id), "route_id": str(route_id),
        "driver_id": str(driver_id), "vehicle_id": str(vehicle_id),
        "gps_event_id": str(event_id), "dbt_row_count": 1,
        "route_broker_events_published": 2,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--order", required=True, type=Path)
    parser.add_argument("--gps", required=True, type=Path)
    parser.add_argument("--analytics", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    args.output.unlink(missing_ok=True)
    async def execute():
        try:
            return await reconcile(
                json.loads(args.order.read_text()),
                json.loads(args.gps.read_text()),
                json.loads(args.analytics.read_text()),
            )
        finally:
            await engine.dispose()
    receipt = asyncio.run(execute())
    args.output.write_text(json.dumps(receipt, sort_keys=True, indent=2) + "\n")
    print(json.dumps(receipt, sort_keys=True))


if __name__ == "__main__":
    main()

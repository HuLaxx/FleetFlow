"""CI-only continuous source-order -> real solver -> approval -> dispatch proof.

Runs against the SAME disposable PostGIS database and assigned driver/vehicle
used by the real Chromium GPS/Parquet/dbt workflow. No production access.
"""
import argparse
import asyncio
import json
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from uuid import UUID, uuid4

import httpx
from geoalchemy2.elements import WKTElement
from sqlalchemy import select

from src.auth.jwt import create_access_token
from src.database import AsyncSessionLocal, engine
from src.models import Customer, DispatchOutboxEvent, Order, Route, RouteApprovalAudit, RouteStop, Vehicle
from src.models.user import User, UserRole


def require_local():
    if engine.url.database != "fleetflow_test" or engine.url.host not in ("localhost", "127.0.0.1"):
        raise RuntimeError("Refusing to run outside disposable local fleetflow_test")


async def run(driver_id: UUID, vehicle_id: UUID, output: Path):
    require_local()
    async with AsyncSessionLocal() as session:
        vehicle = await session.get(Vehicle, vehicle_id)
        if vehicle is None or vehicle.current_driver_id != driver_id or vehicle.depot_id is None:
            raise ValueError("GPS fixture vehicle/driver/depot association is invalid")
        depot_id = vehicle.depot_id
        customer = Customer(
            name="Synthetic P1 Recipient", address="Synthetic test address",
            latitude=Decimal("55.8700000"), longitude=Decimal("-4.2600000"),
            location=WKTElement("POINT(-4.26 55.87)", srid=4326),
        )
        session.add(customer)
        await session.flush()
        order = Order(
            order_number=f"P1-{uuid4().hex[:16]}", customer_id=customer.id,
            depot_id=depot_id, items=[], total_weight_kg=Decimal("1.00"),
            delivery_date=date(2030, 1, 15),
            time_window_start=datetime(2030, 1, 15, 10),
            time_window_end=datetime(2030, 1, 15, 17),
            service_time_minutes=5, status="pending", source="synthetic_ci",
        )
        session.add(order)
        dispatcher_email = f"p1-dispatcher-{uuid4().hex}@example.test"
        user = User(email=dispatcher_email, hashed_password="unused-ci-token-only",
                    role=UserRole.DISPATCHER, is_active=True, is_verified=True)
        session.add(user)
        await session.commit()
        order_id = order.id
        dispatcher_id = user.id

    token = create_access_token({"sub": dispatcher_email, "role": "dispatcher"})
    headers = {"Authorization": f"Bearer {token}"}
    async with httpx.AsyncClient(base_url="http://127.0.0.1:8000", timeout=45) as client:
        request = {"depot_id": str(depot_id), "date": "2030-01-15"}
        planned = await client.post("/api/v1/optimization/routes/plan", json=request, headers=headers)
        planned.raise_for_status()
        plan = planned.json()
        if plan.get("status") != "planned" or plan.get("route_count") != 1:
            raise AssertionError(f"Expected one real OR-Tools plan, got {plan}")
        route_id = UUID(plan["route_ids"][0])
        premature = await client.post(
            f"/api/v1/routes/{route_id}/start",
            json={"driver_id": str(driver_id)}, headers=headers,
        )
        if premature.status_code != 409:
            raise AssertionError("Unapproved dispatch was not rejected")
        approved = await client.post(f"/api/v1/routes/{route_id}/approve", headers=headers)
        approved.raise_for_status()
        approval = approved.json()
        if approval.get("status") != "approved":
            raise AssertionError("Explicit approval was not recorded")
        started = await client.post(
            f"/api/v1/routes/{route_id}/start",
            json={"driver_id": str(driver_id)}, headers=headers,
        )
        started.raise_for_status()
        dispatch = started.json()
        if dispatch.get("status") != "in_progress":
            raise AssertionError("Approved route did not dispatch")

    async with AsyncSessionLocal() as session:
        route = await session.get(Route, route_id)
        stops = (await session.scalars(select(RouteStop).where(RouteStop.route_id == route_id))).all()
        audits = (await session.scalars(
            select(RouteApprovalAudit).where(RouteApprovalAudit.route_id == route_id)
        )).all()
        events = (await session.scalars(select(DispatchOutboxEvent).where(
            DispatchOutboxEvent.message_key == str(route_id),
            DispatchOutboxEvent.topic.in_(["routes.approved", "routes.started"]),
        ))).all()
        if (route is None or route.algorithm_used != "ortools-cvrptw-haversine"
            or route.status != "in_progress" or route.driver_id != driver_id
            or route.vehicle_id != vehicle_id or len(stops) != 1
            or stops[0].order_id != order_id or len(audits) != 1
            or audits[0].approved_by_user_id != dispatcher_id
            or {e.topic for e in events} != {"routes.approved", "routes.started"}
            or len(events) != 2):
            raise AssertionError("Persisted solver/approval/dispatch identity mismatch")
        if any(e.payload.get("route_id") != str(route_id) for e in events):
            raise AssertionError("Outbox route identity mismatch")
        receipt = {
            "scope": "synthetic_disposable_postgis_only",
            "order_id": str(order_id), "route_id": str(route_id),
            "driver_id": str(driver_id), "vehicle_id": str(vehicle_id),
            "approval_audit_id": str(audits[0].id),
            "approver_id": str(dispatcher_id),
            "approval_event_id": str(audits[0].event_id),
            "dispatch_event_id": dispatch["start_event_id"],
            "solver": route.algorithm_used,
            "approval_persisted": True, "dispatch_persisted": True,
        }
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x", encoding="utf-8") as file:
        json.dump(receipt, file, sort_keys=True)
    print(json.dumps(receipt, sort_keys=True))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--driver-id", type=UUID, required=True)
    parser.add_argument("--vehicle-id", type=UUID, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    async def execute():
        try:
            await run(args.driver_id, args.vehicle_id, args.output)
        finally:
            await engine.dispose()
    asyncio.run(execute())


if __name__ == "__main__":
    main()

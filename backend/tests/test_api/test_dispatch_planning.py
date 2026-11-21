"""PostGIS-backed acceptance tests: real OR-Tools preview -> persisted planned route -> approval.

These tests exercise actual SQL rows and the packaged solver. Kafka remains mocked
in the API test fixture; this is not a broker-backed end-to-end deployment test.
"""

from datetime import datetime, date
from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from geoalchemy2.elements import WKTElement
from sqlalchemy import select

from src.auth.jwt import create_access_token
from src.models import Customer, DispatchOutboxEvent, Route, RouteStop
from src.models.user import User, UserRole


async def _setup(db_session, sample_depot, sample_driver, sample_vehicle, sample_order):
    depot = await sample_depot()
    driver = await sample_driver(depot_id=depot.id)
    vehicle = await sample_vehicle(depot_id=depot.id, driver_id=driver.id)
    order = await sample_order(depot_id=depot.id)
    # A fixed future UTC date avoids CI timing flakiness around midnight.
    order.delivery_date = date(2030, 1, 15)
    order.time_window_start = datetime(2030, 1, 15, 10, 0)
    order.time_window_end = datetime(2030, 1, 15, 17, 0)
    customer = await db_session.get(Customer, order.customer_id)
    customer.latitude = Decimal("55.8700000")
    customer.longitude = Decimal("-4.2600000")
    customer.location = WKTElement("POINT(-4.26 55.87)", srid=4326)
    await db_session.flush()
    return depot, driver, vehicle, order


async def _headers(db_session, role):
    email = f"planner-{uuid4().hex}@example.test"
    user = User(
        email=email,
        hashed_password="unused-test-credential",
        role=role,
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()
    token = create_access_token({"sub": email, "role": role.value})
    return {"Authorization": f"Bearer {token}"}


def _request(depot):
    return {"depot_id": str(depot.id), "date": "2030-01-15"}


@pytest.mark.asyncio
async def test_preview_uses_real_customer_coordinates_without_writing(
    client, db_session, sample_depot, sample_driver, sample_vehicle, sample_order
):
    depot, _, vehicle, order = await _setup(
        db_session, sample_depot, sample_driver, sample_vehicle, sample_order
    )
    response = await client.post("/api/v1/optimization/routes/optimize", json=_request(depot))
    assert response.status_code == 200, response.text
    result = response.json()
    assert result["status"] == "success"
    assert result["mode"] == "preview"
    assert result["metrics"]["total_orders_scheduled"] == 1
    assert result["metrics"]["total_distance_km"] > 0
    assert result["routes"][0]["vehicle_id"] == str(vehicle.id)
    assert result["routes"][0]["stops"][0]["order_id"] == str(order.id)
    assert result["routes"][0]["stops"][0]["location"]["latitude"] == 55.87
    assert (await db_session.scalars(select(Route))).first() is None


@pytest.mark.asyncio
async def test_real_solver_persists_plan_then_requires_existing_explicit_approval(
    client, db_session, sample_depot, sample_driver, sample_vehicle, sample_order
):
    depot, driver, vehicle, order = await _setup(
        db_session, sample_depot, sample_driver, sample_vehicle, sample_order
    )
    headers = await _headers(db_session, UserRole.DISPATCHER)
    path = "/api/v1/optimization/routes/plan"

    planned = await client.post(path, json=_request(depot), headers=headers)
    assert planned.status_code == 200, planned.text
    assert planned.json()["status"] == "planned"
    assert planned.json()["approved"] is False
    assert planned.json()["route_count"] == 1
    route_id = planned.json()["route_ids"][0]

    saved = await db_session.get(Route, UUID(route_id))
    assert saved is not None
    assert saved.status == "planned"
    assert saved.algorithm_used == "ortools-cvrptw-haversine"
    assert saved.planned_distance_km > 0
    assert saved.planned_duration_minutes >= 0
    assert saved.driver_id == driver.id and saved.vehicle_id == vehicle.id
    stops = (
        await db_session.scalars(select(RouteStop).where(RouteStop.route_id == saved.id))
    ).all()
    assert len(stops) == 1
    assert stops[0].order_id == order.id
    assert stops[0].stop_sequence == 1
    assert stops[0].latitude == Decimal("55.8700000")
    assert stops[0].planned_arrival >= order.time_window_start
    assert stops[0].planned_arrival <= order.time_window_end

    blocked = await client.post(
        f"/api/v1/routes/{route_id}/start",
        json={"driver_id": str(driver.id)},
        headers=headers,
    )
    assert blocked.status_code == 409

    approved = await client.post(f"/api/v1/routes/{route_id}/approve", headers=headers)
    assert approved.status_code == 200, approved.text
    assert approved.json()["status"] == "approved"

    # Follow the *same real OR-Tools source order* through the approval
    # boundary and durable dispatch outbox. This is a DB-backed integration
    # slice, not yet a broker/GPS/Parquet/dbt golden-path claim.
    started = await client.post(
        f"/api/v1/routes/{route_id}/start",
        json={"driver_id": str(driver.id)},
        headers=headers,
    )
    assert started.status_code == 200, started.text
    assert started.json()["status"] == "in_progress"
    assert started.json()["delivery_status"] == "pending"
    start_event_id = UUID(started.json()["start_event_id"])
    start_event = await db_session.get(DispatchOutboxEvent, start_event_id)
    assert start_event is not None
    assert start_event.topic == "routes.started"
    assert start_event.status == "pending"
    assert start_event.message_key == route_id
    assert start_event.payload["event_id"] == str(start_event_id)
    assert start_event.payload["route_id"] == route_id
    assert start_event.payload["driver_id"] == str(driver.id)
    assert start_event.payload["vehicle_id"] == str(vehicle.id)
    assert start_event.payload["schema_version"] == 1
    assert "email" not in start_event.payload

    repeated_start = await client.post(
        f"/api/v1/routes/{route_id}/start",
        json={"driver_id": str(driver.id)},
        headers=headers,
    )
    assert repeated_start.status_code == 409
    start_events = (
        await db_session.scalars(
            select(DispatchOutboxEvent).where(
                DispatchOutboxEvent.topic == "routes.started",
                DispatchOutboxEvent.message_key == route_id,
            )
        )
    ).all()
    assert len(start_events) == 1

    detail = await client.get(f"/api/v1/routes/{route_id}")
    assert detail.status_code == 200, detail.text
    assert detail.json()["stops"][0]["customer_name"] == "Test Recipient"

    # The source order is already assigned, so no eligible pending orders remain.
    # Planning must fail closed without fabricating a second route. The API
    # reports infeasible/no eligible work as 422, not an approval conflict (409).
    duplicate = await client.post(path, json=_request(depot), headers=headers)
    assert duplicate.status_code == 422, duplicate.text
    routes = (await db_session.scalars(select(Route))).all()
    assert len(routes) == 1
    assert routes[0].id == saved.id


@pytest.mark.asyncio
async def test_plan_requires_dispatcher_role(
    client, db_session, sample_depot, sample_driver, sample_vehicle, sample_order
):
    depot, _, _, _ = await _setup(
        db_session, sample_depot, sample_driver, sample_vehicle, sample_order
    )
    path = "/api/v1/optimization/routes/plan"
    anonymous = await client.post(path, json=_request(depot))
    assert anonymous.status_code == 401
    viewer = await client.post(
        path, json=_request(depot), headers=await _headers(db_session, UserRole.VIEWER)
    )
    assert viewer.status_code == 403
    assert (await db_session.scalars(select(Route))).first() is None


@pytest.mark.asyncio
async def test_no_location_is_rejected_without_database_mutation(
    client, db_session, sample_depot, sample_driver, sample_vehicle, sample_order
):
    depot, _, _, order = await _setup(
        db_session, sample_depot, sample_driver, sample_vehicle, sample_order
    )
    order.customer_id = None
    await db_session.flush()
    result = await client.post(
        "/api/v1/optimization/routes/plan",
        json=_request(depot),
        headers=await _headers(db_session, UserRole.DISPATCHER),
    )
    assert result.status_code == 422
    assert "coordinates" in result.json()["detail"]
    assert (await db_session.scalars(select(Route))).first() is None


@pytest.mark.asyncio
async def test_unavailable_vehicle_is_rejected(
    client, db_session, sample_depot, sample_driver, sample_vehicle, sample_order
):
    depot, _, vehicle, _ = await _setup(
        db_session, sample_depot, sample_driver, sample_vehicle, sample_order
    )
    vehicle.status = "maintenance"
    await db_session.flush()
    result = await client.post(
        "/api/v1/optimization/routes/plan",
        json=_request(depot),
        headers=await _headers(db_session, UserRole.DISPATCHER),
    )
    assert result.status_code == 422
    assert (await db_session.scalars(select(Route))).first() is None


@pytest.mark.asyncio
async def test_infeasible_capacity_returns_failure_not_fabricated_routes(
    client, db_session, sample_depot, sample_driver, sample_vehicle, sample_order
):
    depot, _, _, order = await _setup(
        db_session, sample_depot, sample_driver, sample_vehicle, sample_order
    )
    order.total_weight_kg = Decimal("9999")
    await db_session.flush()
    result = await client.post(
        "/api/v1/optimization/routes/plan",
        json=_request(depot),
        headers=await _headers(db_session, UserRole.DISPATCHER),
    )
    assert result.status_code == 422
    assert "feasible" in result.json()["detail"]
    assert (await db_session.scalars(select(Route))).first() is None

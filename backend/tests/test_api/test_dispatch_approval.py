"""Database-backed dispatch approval and factual performance API regression tests."""

from datetime import timedelta
from decimal import Decimal
from uuid import uuid4

import pytest
from geoalchemy2.elements import WKTElement

from src.auth.jwt import create_access_token
from src.models import Route, RouteStop
from src.models.user import User, UserRole


async def seed_dispatch(db_session, sample_depot, sample_driver, sample_vehicle, sample_order):
    depot = await sample_depot()
    driver = await sample_driver(depot_id=depot.id)
    vehicle = await sample_vehicle(driver_id=driver.id, depot_id=depot.id)
    order = await sample_order(depot_id=depot.id)
    route = Route(
        route_date=order.delivery_date,
        driver_id=driver.id,
        vehicle_id=vehicle.id,
        depot_id=depot.id,
        planned_stops=1,
        completed_stops=0,
        planned_distance_km=Decimal("12.50"),
        planned_duration_minutes=40,
        algorithm_used="seeded-test-only",
        status="planned",
    )
    db_session.add(route)
    await db_session.flush()
    stop = RouteStop(
        route_id=route.id,
        order_id=order.id,
        stop_sequence=1,
        latitude=Decimal("55.8642"),
        longitude=Decimal("-4.2518"),
        location=WKTElement("POINT(-4.2518 55.8642)", srid=4326),
        address="42 Example Street, Glasgow",
        planned_arrival=order.time_window_start + timedelta(minutes=10),
        status="pending",
    )
    db_session.add(stop)
    await db_session.flush()
    return route, stop, driver, order


async def token_for(db_session, role, *, driver_id=None):
    email = f"dispatch-{uuid4().hex[:12]}@example.test"
    user = User(
        email=email,
        hashed_password="not-used-in-token-test",
        role=role,
        is_active=True,
        driver_id=driver_id,
    )
    db_session.add(user)
    await db_session.flush()
    token = create_access_token({"sub":email, "role":role.value})
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_dispatch_approval_requires_authenticated_dispatcher(
    client, db_session, sample_depot, sample_driver, sample_vehicle, sample_order
):
    route, _, _, _ = await seed_dispatch(
        db_session, sample_depot, sample_driver, sample_vehicle, sample_order
    )
    endpoint = f"/api/v1/routes/{route.id}/approve"
    unauthenticated = await client.post(endpoint)
    assert unauthenticated.status_code == 401

    viewer_headers = await token_for(db_session, UserRole.VIEWER)
    viewer = await client.post(endpoint, headers=viewer_headers)
    assert viewer.status_code == 403
    assert route.status == "planned"


@pytest.mark.asyncio
async def test_route_can_start_only_after_explicit_approval_and_correct_driver(
    client, db_session, sample_depot, sample_driver, sample_vehicle, sample_order
):
    route, _, driver, _ = await seed_dispatch(
        db_session, sample_depot, sample_driver, sample_vehicle, sample_order
    )
    dispatcher_headers = await token_for(db_session, UserRole.DISPATCHER)
    start = f"/api/v1/routes/{route.id}/start"
    payload = {"driver_id": str(driver.id)}

    blocked = await client.post(start, headers=dispatcher_headers, json=payload)
    assert blocked.status_code == 409
    assert route.status == "planned"

    approved = await client.post(
        f"/api/v1/routes/{route.id}/approve", headers=dispatcher_headers
    )
    assert approved.status_code == 200
    assert approved.json()["status"] == "approved"
    assert route.status == "approved"

    repeated = await client.post(
        f"/api/v1/routes/{route.id}/approve", headers=dispatcher_headers
    )
    assert repeated.status_code == 409

    wrong_driver = await client.post(
        start, headers=dispatcher_headers, json={"driver_id": str(uuid4())}
    )
    assert wrong_driver.status_code == 422
    assert route.status == "approved"

    started = await client.post(start, headers=dispatcher_headers, json=payload)
    assert started.status_code == 200
    assert started.json()["status"] == "in_progress"
    assert route.status == "in_progress"


@pytest.mark.asyncio
async def test_driver_cannot_start_another_driver_route(
    client, db_session, sample_depot, sample_driver, sample_vehicle, sample_order
):
    route, _, driver, _ = await seed_dispatch(
        db_session, sample_depot, sample_driver, sample_vehicle, sample_order
    )
    dispatcher_headers = await token_for(db_session, UserRole.ADMIN)
    approved = await client.post(
        f"/api/v1/routes/{route.id}/approve", headers=dispatcher_headers
    )
    assert approved.status_code == 200

    other_driver_headers = await token_for(db_session, UserRole.DRIVER, driver_id=uuid4())
    forbidden = await client.post(
        f"/api/v1/routes/{route.id}/start",
        headers=other_driver_headers,
        json={"driver_id": str(driver.id)},
    )
    assert forbidden.status_code == 403
    assert route.status == "approved"


@pytest.mark.asyncio
async def test_approval_rejects_capacity_and_time_window_violations(
    client, db_session, sample_depot, sample_driver, sample_vehicle, sample_order
):
    route, stop, _, order = await seed_dispatch(
        db_session, sample_depot, sample_driver, sample_vehicle, sample_order
    )
    headers = await token_for(db_session, UserRole.DISPATCHER)
    endpoint = f"/api/v1/routes/{route.id}/approve"

    order.total_weight_kg = Decimal("10000.0")
    response = await client.post(endpoint, headers=headers)
    assert response.status_code == 422
    assert "capacity" in response.json()["detail"].lower()
    assert route.status == "planned"

    order.total_weight_kg = Decimal("4.50")
    stop.planned_arrival = order.time_window_end + timedelta(minutes=1)
    response = await client.post(endpoint, headers=headers)
    assert response.status_code == 422
    assert "time window" in response.json()["detail"].lower()
    assert route.status == "planned"


@pytest.mark.asyncio
async def test_stats_do_not_invent_on_time_or_efficiency_numbers(
    client, db_session, sample_depot, sample_driver, sample_vehicle, sample_order
):
    route, stop, _, order = await seed_dispatch(
        db_session, sample_depot, sample_driver, sample_vehicle, sample_order
    )
    response = await client.get("/api/v1/routes/stats/summary")
    assert response.status_code == 200
    before = response.json()
    assert before["on_time_rate"] is None
    assert before["on_time_sample_size"] == 0
    assert before["fleet_efficiency"] is None
    assert before["avg_route_duration_minutes"] is None
    assert before["by_status"]["planned"] == 1

    route.status = "completed"
    route.actual_duration_minutes = 40
    stop.status = "completed"
    stop.actual_arrival = stop.planned_arrival - timedelta(minutes=5)
    order.status = "delivered"
    await db_session.flush()

    response = await client.get("/api/v1/routes/stats/summary")
    assert response.status_code == 200
    after = response.json()
    assert after["on_time_rate"] == 1.0
    assert after["on_time_sample_size"] == 1
    assert after["avg_route_duration_minutes"] == 40.0
    assert after["fleet_efficiency"] is None

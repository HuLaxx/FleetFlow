"""Database-backed dispatch approval and factual performance API regression tests."""

from datetime import timedelta
from decimal import Decimal
from uuid import uuid4

import pytest
from geoalchemy2.elements import WKTElement
from sqlalchemy import select

from src.auth.jwt import create_access_token
from src.models import DispatchOutboxEvent, Route, RouteStop, Vehicle
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
    assert started.json()["delivery_status"] == "pending"
    assert route.status == "in_progress"
    events = (
        await db_session.scalars(
            select(DispatchOutboxEvent).where(
                DispatchOutboxEvent.topic == "routes.started",
                DispatchOutboxEvent.message_key == str(route.id),
            )
        )
    ).all()
    assert len(events) == 1
    assert str(events[0].id) == started.json()["start_event_id"]
    assert events[0].status == "pending"
    assert events[0].payload["route_id"] == str(route.id)
    assert events[0].payload["driver_id"] == str(driver.id)
    assert events[0].payload["event_id"] == str(events[0].id)

    repeated_start = await client.post(start, headers=dispatcher_headers, json=payload)
    assert repeated_start.status_code == 409
    assert (
        await db_session.scalars(
            select(DispatchOutboxEvent).where(
                DispatchOutboxEvent.topic == "routes.started",
                DispatchOutboxEvent.message_key == str(route.id),
            )
        )
    ).all() == events


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
async def test_approval_rejects_stale_vehicle_driver_assignment(
    client, db_session, sample_depot, sample_driver, sample_vehicle, sample_order
):
    """Human approval must recheck the live assignment after planning."""
    route, _, _, _ = await seed_dispatch(
        db_session, sample_depot, sample_driver, sample_vehicle, sample_order
    )
    vehicle = await db_session.get(Vehicle, route.vehicle_id)
    replacement_driver = await sample_driver(depot_id=route.depot_id)
    vehicle.current_driver_id = replacement_driver.id
    await db_session.flush()

    headers = await token_for(db_session, UserRole.DISPATCHER)
    response = await client.post(
        f"/api/v1/routes/{route.id}/approve", headers=headers
    )
    assert response.status_code == 409
    assert (
        response.json()["detail"]
        == "Vehicle driver assignment changed since planning"
    )
    assert route.status == "planned"


@pytest.mark.asyncio
async def test_start_rejects_vehicle_reassigned_after_approval(
    client, db_session, sample_depot, sample_driver, sample_vehicle, sample_order
):
    """An approved route cannot start after its vehicle changes drivers."""
    route, _, driver, _ = await seed_dispatch(
        db_session, sample_depot, sample_driver, sample_vehicle, sample_order
    )
    dispatcher_headers = await token_for(db_session, UserRole.DISPATCHER)
    approved = await client.post(
        f"/api/v1/routes/{route.id}/approve", headers=dispatcher_headers
    )
    assert approved.status_code == 200
    assert route.status == "approved"

    vehicle = await db_session.get(Vehicle, route.vehicle_id)
    replacement_driver = await sample_driver(depot_id=route.depot_id)
    vehicle.current_driver_id = replacement_driver.id
    await db_session.flush()

    response = await client.post(
        f"/api/v1/routes/{route.id}/start",
        headers=dispatcher_headers,
        json={"driver_id": str(driver.id)},
    )
    assert response.status_code == 409
    assert (
        response.json()["detail"]
        == "Vehicle driver assignment changed since approval"
    )
    assert route.status == "approved"
    assert route.started_at is None


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


@pytest.mark.asyncio
async def test_stop_completion_rejects_unauthenticated_and_inactive_routes(
    client, db_session, sample_depot, sample_driver, sample_vehicle, sample_order
):
    """A planned or approved route cannot have its delivery marked complete."""
    route, stop, driver, order = await seed_dispatch(
        db_session, sample_depot, sample_driver, sample_vehicle, sample_order
    )
    endpoint = f"/api/v1/routes/{route.id}/stops/{stop.id}/complete"
    anonymous = await client.post(endpoint, json={})
    assert anonymous.status_code == 401

    driver_headers = await token_for(db_session, UserRole.DRIVER, driver_id=driver.id)
    planned = await client.post(endpoint, headers=driver_headers, json={})
    assert planned.status_code == 409
    assert stop.status == "pending"
    assert order.status == "pending"

    dispatcher_headers = await token_for(db_session, UserRole.DISPATCHER)
    approved = await client.post(
        f"/api/v1/routes/{route.id}/approve", headers=dispatcher_headers
    )
    assert approved.status_code == 200
    before_start = await client.post(endpoint, headers=driver_headers, json={})
    assert before_start.status_code == 409
    assert stop.status == "pending"


@pytest.mark.asyncio
async def test_stop_completion_rejects_wrong_driver_on_active_route(
    client, db_session, sample_depot, sample_driver, sample_vehicle, sample_order
):
    """A different signed driver cannot complete another driver's stop."""
    route, stop, driver, order = await seed_dispatch(
        db_session, sample_depot, sample_driver, sample_vehicle, sample_order
    )
    dispatcher_headers = await token_for(db_session, UserRole.DISPATCHER)
    approved = await client.post(
        f"/api/v1/routes/{route.id}/approve", headers=dispatcher_headers
    )
    assert approved.status_code == 200
    started = await client.post(
        f"/api/v1/routes/{route.id}/start",
        headers=dispatcher_headers,
        json={"driver_id": str(driver.id)},
    )
    assert started.status_code == 200

    wrong_headers = await token_for(db_session, UserRole.DRIVER, driver_id=uuid4())
    denied = await client.post(
        f"/api/v1/routes/{route.id}/stops/{stop.id}/complete",
        headers=wrong_headers,
        json={"recipient_name": "Not authorized"},
    )
    assert denied.status_code == 403
    assert stop.status == "pending"
    assert order.status == "pending"
    assert route.completed_stops == 0


@pytest.mark.asyncio
async def test_stop_completion_persists_single_durable_event_and_rejects_replay(
    client, db_session, sample_depot, sample_driver, sample_vehicle, sample_order
):
    """Completion and its retryable outbox record commit as one unit."""
    route, stop, driver, order = await seed_dispatch(
        db_session, sample_depot, sample_driver, sample_vehicle, sample_order
    )
    dispatcher = await token_for(db_session, UserRole.DISPATCHER)
    driver_headers = await token_for(db_session, UserRole.DRIVER, driver_id=driver.id)
    approved = await client.post(
        f"/api/v1/routes/{route.id}/approve", headers=dispatcher
    )
    assert approved.status_code == 200
    started = await client.post(
        f"/api/v1/routes/{route.id}/start",
        headers=driver_headers,
        json={"driver_id": str(driver.id)},
    )
    assert started.status_code == 200

    endpoint = f"/api/v1/routes/{route.id}/stops/{stop.id}/complete"
    completed = await client.post(
        endpoint, headers=driver_headers, json={"recipient_name": "Synthetic recipient"}
    )
    assert completed.status_code == 200
    body = completed.json()
    assert body["delivery_status"] == "pending"
    assert stop.status == "completed"
    assert order.status == "delivered"
    assert route.completed_stops == 1

    events = (
        await db_session.scalars(
            select(DispatchOutboxEvent).where(
                DispatchOutboxEvent.topic == "routes.stops",
                DispatchOutboxEvent.message_key == str(route.id),
            )
        )
    ).all()
    assert len(events) == 1
    event = events[0]
    assert event.status == "pending"
    assert str(event.id) == body["completion_event_id"]
    assert event.payload["event_id"] == str(event.id)
    assert event.payload["route_id"] == str(route.id)
    assert event.payload["stop_id"] == str(stop.id)
    assert event.payload["order_id"] == str(order.id)
    assert event.payload["driver_id"] == str(driver.id)
    assert event.payload["schema_version"] == 1
    assert "recipient_name" not in event.payload

    replay = await client.post(endpoint, headers=driver_headers, json={})
    assert replay.status_code == 409
    assert route.completed_stops == 1
    assert (
        await db_session.scalars(
            select(DispatchOutboxEvent).where(
                DispatchOutboxEvent.topic == "routes.stops",
                DispatchOutboxEvent.message_key == str(route.id),
            )
        )
    ).all() == events

"""Routes API endpoints - with DATABASE integration."""

from datetime import UTC, datetime
from datetime import date as calendar_date
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import and_, case, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from src.auth.dependencies import require_dispatcher, require_driver
from src.database import get_db
from src.events import (
    RouteStartedEvent,
    StopCompletedEvent,
    get_kafka_producer,
)
from src.models import Route, RouteStop
from src.models.user import User, UserRole

router = APIRouter()


# ============================================
# Request/Response Models
# ============================================


class StartRouteRequest(BaseModel):
    """Request to start a route."""

    driver_id: UUID


class CompleteStopRequest(BaseModel):
    """Request to complete a stop."""

    recipient_name: str | None = None
    signature_url: str | None = None
    photo_url: str | None = None
    notes: str | None = None


# ============================================
# Endpoints
# ============================================


@router.get("")
async def list_routes(
    date: str | None = Query(None, description="Filter by route date"),
    status: str | None = Query(None, description="Filter by status"),
    driver_id: UUID | None = Query(None, description="Filter by driver"),
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """List routes with optional filters."""
    # Build query
    stmt = select(Route).options(joinedload(Route.driver), joinedload(Route.vehicle)).limit(limit)

    conditions = []
    if date:
        try:
            filter_date = calendar_date.fromisoformat(date)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail="Invalid ISO route date") from exc
        conditions.append(Route.route_date == filter_date)
    if status:
        conditions.append(Route.status == status)
    if driver_id:
        conditions.append(Route.driver_id == driver_id)

    if conditions:
        stmt = stmt.where(and_(*conditions))

    stmt = stmt.order_by(Route.route_date.desc(), Route.created_at.desc())

    # Execute
    result = await db.execute(stmt)
    routes = result.scalars().unique().all()

    # Get total count
    count_stmt = select(func.count(Route.id))
    if conditions:
        count_stmt = count_stmt.where(and_(*conditions))
    total_result = await db.execute(count_stmt)
    total = total_result.scalar()

    # Format response
    route_list = []
    for route in routes:
        route_data = {
            "id": str(route.id),
            "route_date": route.route_date.isoformat(),
            "driver": (
                {
                    "id": str(route.driver.id),
                    "name": route.driver.full_name,
                }
                if route.driver
                else None
            ),
            "vehicle": (
                {
                    "id": str(route.vehicle.id),
                    "number": route.vehicle.vehicle_number,
                }
                if route.vehicle
                else None
            ),
            "status": route.status,
            "stops_completed": route.completed_stops,
            "stops_total": route.planned_stops,
            "planned_distance_km": (
                float(route.planned_distance_km) if route.planned_distance_km else None
            ),
            "planned_duration_minutes": route.planned_duration_minutes,
            "started_at": route.started_at.isoformat() if route.started_at else None,
        }
        route_list.append(route_data)

    return {
        "routes": route_list,
        "total": total,
    }


@router.get("/{route_id}")
async def get_route(
    route_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get route details with all stops."""
    # Query with relationships
    stmt = (
        select(Route)
        .options(
            joinedload(Route.driver),
            joinedload(Route.vehicle),
            joinedload(Route.depot),
            joinedload(Route.stops).joinedload(RouteStop.order),
        )
        .where(Route.id == route_id)
    )

    result = await db.execute(stmt)
    route = result.scalar_one_or_none()

    if not route:
        raise HTTPException(status_code=404, detail="Route not found")

    # Format stops
    stops = []
    for stop in sorted(route.stops, key=lambda s: s.stop_sequence):
        stop_data = {
            "id": str(stop.id),
            "sequence": stop.stop_sequence,
            "order_id": str(stop.order_id) if stop.order_id else None,
            "order_number": stop.order.order_number if stop.order else None,
            "customer_name": (
                stop.order.customer.name if stop.order and stop.order.customer else "Unknown"
            ),
            "address": stop.address,
            "latitude": float(stop.latitude),
            "longitude": float(stop.longitude),
            "status": stop.status,
            "planned_arrival": stop.planned_arrival.isoformat() if stop.planned_arrival else None,
            "actual_arrival": stop.actual_arrival.isoformat() if stop.actual_arrival else None,
            "distance_from_prev_km": (
                float(stop.distance_from_prev_km) if stop.distance_from_prev_km else None
            ),
        }
        stops.append(stop_data)

    response = {
        "id": str(route.id),
        "route_date": route.route_date.isoformat(),
        "driver": (
            {
                "id": str(route.driver.id),
                "name": route.driver.full_name,
                "phone": route.driver.phone,
            }
            if route.driver
            else None
        ),
        "vehicle": (
            {
                "id": str(route.vehicle.id),
                "number": route.vehicle.vehicle_number,
                "type": route.vehicle.type,
            }
            if route.vehicle
            else None
        ),
        "depot": (
            {
                "id": str(route.depot.id),
                "name": route.depot.name,
                "address": route.depot.address,
            }
            if route.depot
            else None
        ),
        "status": route.status,
        "started_at": route.started_at.isoformat() if route.started_at else None,
        "completed_at": route.completed_at.isoformat() if route.completed_at else None,
        "stops": stops,
        "metrics": {
            "planned_distance_km": (
                float(route.planned_distance_km) if route.planned_distance_km else None
            ),
            "actual_distance_km": (
                float(route.actual_distance_km) if route.actual_distance_km else None
            ),
            "planned_duration_minutes": route.planned_duration_minutes,
            "actual_duration_minutes": route.actual_duration_minutes,
            "stops_completed": route.completed_stops,
            "stops_total": route.planned_stops,
        },
    }

    return response


@router.post("/{route_id}/approve")
async def approve_route(
    route_id: UUID,
    current_user: User = Depends(require_dispatcher),
    db: AsyncSession = Depends(get_db),
):
    """Explicitly approve a persisted planned route after checking basic dispatch constraints.

    The route must already exist in the database. This does not create routes from
    optimizer previews, record a durable approval audit or prove global optimality.
    """
    stmt = (
        select(Route)
        .options(
            selectinload(Route.stops).joinedload(RouteStop.order),
            selectinload(Route.vehicle),
        )
        .where(Route.id == route_id)
        .with_for_update(of=Route)
    )
    result = await db.execute(stmt)
    route = result.scalar_one_or_none()
    if route is None:
        raise HTTPException(status_code=404, detail="Route not found")
    if route.status != "planned":
        raise HTTPException(status_code=409, detail="Only planned routes can be approved")
    if route.driver_id is None or route.vehicle_id is None or route.depot_id is None:
        raise HTTPException(
            status_code=422, detail="Route is missing an assigned driver, vehicle or depot"
        )
    if not route.vehicle or route.vehicle.depot_id != route.depot_id:
        raise HTTPException(
            status_code=422, detail="Assigned vehicle is not stationed at route depot"
        )

    stops = sorted(route.stops, key=lambda stop: stop.stop_sequence)
    if not stops or route.planned_stops != len(stops):
        raise HTTPException(status_code=422, detail="Route stop count does not match the plan")
    if [stop.stop_sequence for stop in stops] != list(range(1, len(stops) + 1)):
        raise HTTPException(status_code=422, detail="Route stop sequence must be contiguous")

    order_ids = [stop.order_id for stop in stops]
    if None in order_ids or len(set(order_ids)) != len(order_ids):
        raise HTTPException(
            status_code=422, detail="Route has missing or repeated order assignments"
        )

    total_weight = 0
    for stop in stops:
        if stop.status != "pending" or stop.order is None or stop.order.status != "pending":
            raise HTTPException(
                status_code=422, detail="Only pending orders and stops can be approved"
            )
        if stop.order.depot_id != route.depot_id or stop.order.delivery_date != route.route_date:
            raise HTTPException(status_code=422, detail="Order and route depot/date mismatch")
        if (
            stop.planned_arrival is None
            or not stop.order.time_window_start
            <= stop.planned_arrival
            <= stop.order.time_window_end
        ):
            raise HTTPException(
                status_code=422, detail="Planned arrival violates an order time window"
            )
        total_weight += stop.order.total_weight_kg

    if total_weight > route.vehicle.capacity_kg:
        raise HTTPException(
            status_code=422, detail="Total order weight exceeds assigned vehicle capacity"
        )

    route.status = "approved"
    route.updated_at = datetime.now(UTC).replace(tzinfo=None)
    await db.commit()
    return {"route_id": str(route.id), "status": route.status, "approved_by": current_user.email}


@router.post("/{route_id}/start")
async def start_route(
    route_id: UUID,
    request: StartRouteRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(require_driver),
    db: AsyncSession = Depends(get_db),
):
    """Start an explicitly approved route using the assigned driver identity."""
    stmt = (
        select(Route)
        .options(selectinload(Route.driver))
        .where(Route.id == route_id)
        .with_for_update(of=Route)
    )
    result = await db.execute(stmt)
    route = result.scalar_one_or_none()

    if not route:
        raise HTTPException(status_code=404, detail="Route not found")

    if route.status != "approved":
        raise HTTPException(status_code=409, detail="Route requires explicit dispatcher approval")
    if route.driver_id is None or route.driver_id != request.driver_id:
        raise HTTPException(
            status_code=422, detail="Requested driver is not assigned to this route"
        )
    if current_user.role == UserRole.DRIVER and current_user.driver_id != route.driver_id:
        raise HTTPException(
            status_code=403, detail="Drivers may only start their own assigned routes"
        )

    # Update route
    route.status = "in_progress"
    route.started_at = datetime.now(UTC).replace(tzinfo=None)
    route.updated_at = datetime.now(UTC).replace(tzinfo=None)

    # Update driver status
    if route.driver:
        route.driver.status = "on_route"

    await db.commit()

    # Publish event
    event = RouteStartedEvent(
        route_id=route_id,
        driver_id=request.driver_id,
        started_at=datetime.now(UTC),
        first_stop_eta=datetime.now(UTC),
    )

    async def publish_event():
        producer = get_kafka_producer()
        await producer.publish_async(
            topic="routes.started",
            event=event,
            key=str(route_id),
        )

    background_tasks.add_task(publish_event)

    return {
        "route_id": str(route_id),
        "status": "in_progress",
        "started_at": route.started_at.isoformat(),
    }


@router.post("/{route_id}/stops/{stop_id}/complete")
async def complete_stop(
    route_id: UUID,
    stop_id: UUID,
    request: CompleteStopRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """Mark a stop as completed."""
    # Get stop
    stmt = (
        select(RouteStop)
        .options(joinedload(RouteStop.route), joinedload(RouteStop.order))
        .where(and_(RouteStop.id == stop_id, RouteStop.route_id == route_id))
    )

    result = await db.execute(stmt)
    stop = result.scalar_one_or_none()

    if not stop:
        raise HTTPException(status_code=404, detail="Stop not found")

    if stop.status == "completed":
        raise HTTPException(status_code=400, detail="Stop already completed")

    # Update stop
    stop.status = "completed"
    stop.actual_arrival = datetime.now(UTC).replace(tzinfo=None)
    stop.actual_departure = datetime.now(UTC).replace(tzinfo=None)
    stop.recipient_name = request.recipient_name
    stop.signature_url = request.signature_url
    stop.photo_url = request.photo_url
    stop.updated_at = datetime.now(UTC).replace(tzinfo=None)

    # Update order status
    if stop.order:
        stop.order.status = "delivered"
        stop.order.updated_at = datetime.now(UTC).replace(tzinfo=None)

    # Increment route completed stops
    if stop.route:
        stop.route.completed_stops = (stop.route.completed_stops or 0) + 1

    await db.commit()

    # Publish event
    event = StopCompletedEvent(
        route_id=route_id,
        stop_id=stop_id,
        order_id=stop.order_id,
        driver_id=stop.route.driver_id if stop.route else None,
        completed_at=datetime.now(UTC),
        actual_service_time_minutes=5,  # TODO: Calculate from timestamps
        next_stop_eta=datetime.now(UTC),
    )

    async def publish_event():
        producer = get_kafka_producer()
        await producer.publish_async(
            topic="routes.stops",
            event=event,
            key=str(route_id),
        )

    background_tasks.add_task(publish_event)

    return {
        "route_id": str(route_id),
        "stop_id": str(stop_id),
        "status": "completed",
        "completed_at": datetime.now(UTC).isoformat(),
        "recipient_name": request.recipient_name,
    }


@router.get("/{route_id}/progress")
async def get_route_progress(
    route_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get real-time route progress."""
    # Get route with vehicle for location
    stmt = (
        select(Route)
        .options(joinedload(Route.vehicle), joinedload(Route.stops))
        .where(Route.id == route_id)
    )

    result = await db.execute(stmt)
    route = result.scalar_one_or_none()

    if not route:
        raise HTTPException(status_code=404, detail="Route not found")

    # Find current stop (first pending stop)
    current_stop = None
    for stop in sorted(route.stops, key=lambda s: s.stop_sequence):
        if stop.status in ["pending", "en_route"]:
            current_stop = stop
            break

    response = {
        "route_id": str(route_id),
        "driver_location": None,
        "current_stop": None,
        "progress": {
            "completed": route.completed_stops,
            "pending": (route.planned_stops or 0) - (route.completed_stops or 0),
            "total": route.planned_stops,
            "percentage": (
                round((route.completed_stops / route.planned_stops * 100), 1)
                if route.planned_stops
                else 0
            ),
        },
        "time": {
            "started_at": route.started_at.isoformat() if route.started_at else None,
            "elapsed_minutes": None,  # TODO: Calculate
            "remaining_minutes": route.planned_duration_minutes,
            "eta_completion": None,
        },
        "distance": {
            "completed_km": float(route.actual_distance_km) if route.actual_distance_km else 0,
            "remaining_km": (
                float(route.planned_distance_km) - float(route.actual_distance_km or 0)
                if route.planned_distance_km
                else None
            ),
            "total_km": float(route.planned_distance_km) if route.planned_distance_km else None,
        },
    }

    # Add driver location if available
    if route.vehicle and route.vehicle.latitude and route.vehicle.longitude:
        response["driver_location"] = {
            "latitude": float(route.vehicle.latitude),
            "longitude": float(route.vehicle.longitude),
            "updated_at": route.vehicle.updated_at.isoformat(),
        }

    # Add current stop info
    if current_stop:
        response["current_stop"] = {
            "sequence": current_stop.stop_sequence,
            "status": current_stop.status,
            "eta": (
                current_stop.planned_arrival.isoformat() if current_stop.planned_arrival else None
            ),
            "distance_remaining_km": (
                float(current_stop.distance_from_prev_km)
                if current_stop.distance_from_prev_km
                else None
            ),
        }

    return response


@router.get("/stats/summary")
async def get_route_stats(
    date: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """Get route statistics."""
    target_date = date or datetime.now(UTC).strftime("%Y-%m-%d")

    # Total routes for date
    total_stmt = select(func.count(Route.id))
    if date:
        total_stmt = total_stmt.where(Route.route_date == target_date)
    total_result = await db.execute(total_stmt)
    total = total_result.scalar()

    # Count by status
    status_stmt = select(Route.status, func.count(Route.id))
    if date:
        status_stmt = status_stmt.where(Route.route_date == target_date)
    status_stmt = status_stmt.group_by(Route.status)

    status_result = await db.execute(status_stmt)
    by_status = dict(status_result.all())

    # Aggregate metrics
    metrics_stmt = select(
        func.sum(Route.planned_stops),
        func.sum(Route.completed_stops),
        func.sum(Route.planned_distance_km),
    )
    if date:
        metrics_stmt = metrics_stmt.where(Route.route_date == target_date)

    metrics_result = await db.execute(metrics_stmt)
    total_stops, completed_stops, total_distance = metrics_result.one()

    # Only report observed performance. No arbitrary demo percentages.
    observed = (
        select(
            func.count(RouteStop.id),
            func.sum(case((RouteStop.actual_arrival <= RouteStop.planned_arrival, 1), else_=0)),
        )
        .join(Route, RouteStop.route_id == Route.id)
        .where(
            RouteStop.status == "completed",
            RouteStop.actual_arrival.is_not(None),
            RouteStop.planned_arrival.is_not(None),
        )
    )
    duration = select(func.avg(Route.actual_duration_minutes)).where(
        Route.status == "completed", Route.actual_duration_minutes.is_not(None)
    )
    if date:
        observed = observed.where(Route.route_date == target_date)
        duration = duration.where(Route.route_date == target_date)
    observed_total, on_schedule = (await db.execute(observed)).one()
    avg_actual_duration = (await db.execute(duration)).scalar()

    return {
        "date": target_date,
        "total_routes": total,
        "by_status": {
            "planned": by_status.get("planned", 0),
            "approved": by_status.get("approved", 0),
            "in_progress": by_status.get("in_progress", 0),
            "completed": by_status.get("completed", 0),
            "cancelled": by_status.get("cancelled", 0),
        },
        "total_stops": total_stops or 0,
        "stops_completed": completed_stops or 0,
        "on_time_rate": (round(on_schedule / observed_total, 4) if observed_total else None),
        "on_time_rate_definition": "fraction of completed stops arriving at or before planned arrival",
        "on_time_sample_size": observed_total,
        "total_distance_km": float(total_distance) if total_distance else 0,
        "avg_route_duration_minutes": (
            round(float(avg_actual_duration), 1) if avg_actual_duration is not None else None
        ),
        "fleet_efficiency": None,  # No validated business definition or observed measurement
    }

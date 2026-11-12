"""Routes API endpoints - with DATABASE integration."""

from datetime import UTC, datetime
from datetime import date as calendar_date
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from src.database import get_db
from src.events import (
    RouteStartedEvent,
    StopCompletedEvent,
    get_kafka_producer,
)
from src.models import Route, RouteStop

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


@router.post("/{route_id}/start")
async def start_route(
    route_id: UUID,
    request: StartRouteRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """Start a route."""
    # Get route
    stmt = select(Route).where(Route.id == route_id)
    result = await db.execute(stmt)
    route = result.scalar_one_or_none()

    if not route:
        raise HTTPException(status_code=404, detail="Route not found")

    if route.status != "planned":
        raise HTTPException(
            status_code=400, detail=f"Cannot start route with status: {route.status}"
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

    return {
        "date": target_date,
        "total_routes": total,
        "by_status": {
            "planned": by_status.get("planned", 0),
            "in_progress": by_status.get("in_progress", 0),
            "completed": by_status.get("completed", 0),
            "cancelled": by_status.get("cancelled", 0),
        },
        "total_stops": total_stops or 0,
        "stops_completed": completed_stops or 0,
        "on_time_rate": 0.92,  # TODO: Calculate from actual vs planned times
        "total_distance_km": float(total_distance) if total_distance else 0,
        "avg_route_duration_minutes": 0,  # TODO: Calculate
        "fleet_efficiency": 0.87,  # TODO: Calculate
    }

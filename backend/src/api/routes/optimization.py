"""Route planning endpoints.

The original optimisation endpoint remains a read-only preview. Dispatchers can
explicitly save candidates as *planned* routes, which require a separate
approval step before a driver may start them. No live GPS or dispatch events are
implied by generating a candidate.
"""

from datetime import date
from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from geoalchemy2.elements import WKTElement
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.auth.dependencies import require_dispatcher
from src.database import get_db
from src.models import Customer, Depot, Driver, Order, Route, RouteStop, Vehicle
from src.models.user import User
from src.optimization import VehicleRoutingOptimizer

router = APIRouter()


class OptimizeRequest(BaseModel):
    depot_id: UUID
    date: date


async def _load_inputs(db: AsyncSession, request: OptimizeRequest, *, lock: bool):
    depot = await db.scalar(
        select(Depot).where(Depot.id == request.depot_id, Depot.is_active.is_(True))
    )
    if depot is None:
        raise HTTPException(status_code=404, detail="Active depot not found")

    vehicles_query = (
        select(Vehicle)
        .join(Driver, Driver.id == Vehicle.current_driver_id)
        .where(
            Vehicle.depot_id == depot.id,
            Vehicle.status == "available",
            Driver.status == "available",
        )
        .order_by(Vehicle.id)
    )
    if lock:
        vehicles_query = vehicles_query.with_for_update(of=Vehicle)
    vehicles = (await db.scalars(vehicles_query)).all()
    if not vehicles:
        raise HTTPException(status_code=422, detail="No available, driver-assigned vehicles")

    orders_query = (
        select(Order)
        .options(selectinload(Order.customer))
        .where(
            Order.depot_id == depot.id,
            Order.delivery_date == request.date,
            Order.status == "pending",
        )
        .order_by(Order.id)
    )
    if lock:
        orders_query = orders_query.with_for_update(of=Order)
    orders = (await db.scalars(orders_query)).all()
    if not orders:
        raise HTTPException(status_code=422, detail="No pending orders for this depot and date")

    # The ORM stores customer coordinates on Customer, not Order.
    if any(
        order.customer is None
        or order.customer.latitude is None
        or order.customer.longitude is None
        for order in orders
    ):
        raise HTTPException(status_code=422, detail="Order missing customer delivery coordinates")

    if lock:
        # Check both order and vehicle conflicts inside the same locked transaction.
        occupied_orders = (
            await db.scalars(
                select(RouteStop.order_id)
                .join(Route, Route.id == RouteStop.route_id)
                .where(
                    RouteStop.order_id.in_([order.id for order in orders]),
                    Route.status.in_(("planned", "approved", "in_progress")),
                )
            )
        ).all()
        if occupied_orders:
            raise HTTPException(status_code=409, detail="Orders already appear in active plans")

        occupied_vehicles = set(
            (
                await db.scalars(
                    select(Route.vehicle_id).where(
                        Route.vehicle_id.in_([vehicle.id for vehicle in vehicles]),
                        Route.route_date == request.date,
                        Route.status.in_(("planned", "approved", "in_progress")),
                    )
                )
            ).all()
        )
        vehicles = [vehicle for vehicle in vehicles if vehicle.id not in occupied_vehicles]
        if not vehicles:
            raise HTTPException(status_code=409, detail="All eligible vehicles already have plans")

    return depot, vehicles, orders


def _solve(depot, vehicles, orders, route_date: date):
    try:
        routes = VehicleRoutingOptimizer(planning_time_limit_sec=5).optimize(
            orders, vehicles, depot, route_date
        )
    except (ValueError, TypeError, RuntimeError, AttributeError) as exc:
        raise HTTPException(status_code=422, detail="Cannot optimise this set of constraints") from exc

    if not routes:
        raise HTTPException(
            status_code=422, detail="No feasible route for vehicle capacities and time windows"
        )

    return routes


def _check_candidate_integrity(routes, vehicles, orders):
    """Validate solver output before a transactional database write."""
    available = {vehicle.id: vehicle for vehicle in vehicles}
    expected = {order.id: order for order in orders}
    visited = []
    vehicles_used = set()

    for candidate in routes:
        vehicle_id = candidate["vehicle_id"]
        vehicle = available.get(vehicle_id)
        if vehicle is None or vehicle_id in vehicles_used:
            raise HTTPException(status_code=422, detail="Solver returned invalid vehicle assignment")
        vehicles_used.add(vehicle_id)
        if candidate["driver_id"] is None or candidate["driver_id"] != vehicle.current_driver_id:
            raise HTTPException(status_code=422, detail="Solver returned an unassigned driver")
        if not candidate["stops"]:
            raise HTTPException(status_code=422, detail="Solver returned an empty route")

        for sequence, stop in enumerate(candidate["stops"], start=1):
            order_id = stop["order_id"]
            order = expected.get(order_id)
            if order is None or stop["sequence"] != sequence:
                raise HTTPException(status_code=422, detail="Solver returned invalid stop order")
            arrival = stop["planned_arrival"]
            if not order.time_window_start <= arrival <= order.time_window_end:
                raise HTTPException(status_code=422, detail="Solver stop violates delivery window")
            visited.append(order_id)

        total_weight = sum(
            (expected[stop["order_id"]].total_weight_kg for stop in candidate["stops"]),
            Decimal("0"),
        )
        if total_weight > vehicle.capacity_kg:
            raise HTTPException(status_code=422, detail="Solver route exceeds vehicle capacity")

    if len(visited) != len(expected) or set(visited) != set(expected):
        raise HTTPException(status_code=422, detail="Solver missed or repeated orders")


@router.post("/routes/optimize")
async def optimize_routes(request: OptimizeRequest, db: AsyncSession = Depends(get_db)):
    """Backward-compatible read-only preview, with no database mutation."""
    depot, vehicles, orders = await _load_inputs(db, request, lock=False)
    routes = _solve(depot, vehicles, orders, request.date)
    _check_candidate_integrity(routes, vehicles, orders)
    return {
        "status": "preview",
        "routes": routes,
        "metrics": {
            "total_vehicles_used": len(routes),
            "total_orders_scheduled": sum(len(route["stops"]) for route in routes),
            "total_distance_km": sum(
                route["metrics"]["total_distance_km"] for route in routes
            ),
            "distance_basis": "Haversine straight-line estimate, not road distance",
        },
    }


@router.post("/routes/plan")
async def persist_candidate_routes(
    request: OptimizeRequest,
    current_user: User = Depends(require_dispatcher),
    db: AsyncSession = Depends(get_db),
):
    """Save real optimiser candidates without approving or starting dispatch."""
    depot, vehicles, orders = await _load_inputs(db, request, lock=True)
    candidates = _solve(depot, vehicles, orders, request.date)
    _check_candidate_integrity(candidates, vehicles, orders)

    route_ids = []
    for candidate in candidates:
        route = Route(
            route_date=request.date,
            driver_id=candidate["driver_id"],
            vehicle_id=candidate["vehicle_id"],
            depot_id=depot.id,
            planned_distance_km=Decimal(str(candidate["metrics"]["total_distance_km"])),
            planned_duration_minutes=candidate["metrics"]["total_duration_minutes"],
            planned_stops=len(candidate["stops"]),
            completed_stops=0,
            algorithm_used="ortools-cvrptw-haversine",
            status="planned",
        )
        db.add(route)
        await db.flush()

        for stop in candidate["stops"]:
            order = next(order for order in orders if order.id == stop["order_id"])
            customer = order.customer
            db.add(
                RouteStop(
                    route_id=route.id,
                    order_id=order.id,
                    stop_sequence=stop["sequence"],
                    latitude=customer.latitude,
                    longitude=customer.longitude,
                    location=WKTElement(
                        f"POINT({customer.longitude} {customer.latitude})", srid=4326
                    ),
                    address=customer.address,
                    planned_arrival=stop["planned_arrival"],
                    status="pending",
                )
            )
        route_ids.append(str(route.id))

    # Both Route and RouteStop rows are durable or neither is committed.
    await db.commit()
    return {
        "status": "planned",
        "route_ids": route_ids,
        "route_count": len(route_ids),
        "order_count": len(orders),
        "approved": False,
        "generated_by": current_user.email,
        "distance_basis": "Haversine straight-line estimate, not road distance",
    }

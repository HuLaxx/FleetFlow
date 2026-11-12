"""
Optimization API endpoints.

Handles requests for route optimization and demand forecasting.
"""

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Body, Depends, HTTPException
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db
from src.models import Depot, Order, Vehicle

# Import the optimizer (assuming ml package is installed/available in path)
# In a microservice architecture, this might be a gRPC call or HTTP request to the ML service.
# For this monolith setup, we import directly.
try:
    from ml.route_optimizer import VehicleRoutingOptimizer
except ImportError:
    # Fallback or mock for dev environments without ML dependencies
    VehicleRoutingOptimizer = None

router = APIRouter()


@router.post("/routes/optimize")
async def optimize_routes(
    depot_id: UUID = Body(..., embed=True),
    date_str: str = Body(..., alias="date", embed=True),
    db: AsyncSession = Depends(get_db),
):
    """
    Generate optimized routes for a specific depot and date.
    """
    if not VehicleRoutingOptimizer:
        raise HTTPException(
            status_code=501, detail="Optimization service not available (ML dependencies missing)"
        )

    try:
        route_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")

    # 1. Fetch Data

    # Depot
    depot_result = await db.execute(select(Depot).where(Depot.id == depot_id))
    depot = depot_result.scalar_one_or_none()
    if not depot:
        raise HTTPException(status_code=404, detail="Depot not found")

    # Available Vehicles (assigned to this depot)
    # TODO: Add available status check
    vehicles_result = await db.execute(select(Vehicle).where(Vehicle.depot_id == depot_id))
    vehicles = vehicles_result.scalars().all()
    if not vehicles:
        raise HTTPException(status_code=400, detail="No vehicles available at this depot")

    # Orders (Pending orders for this date, not yet assigned to a route)
    # Assuming 'pending' status and matching date
    orders_stmt = select(Order).where(
        and_(
            Order.depot_id == depot_id,
            Order.delivery_date == route_date,
            Order.status == "pending",  # Only optimize pending orders
        )
    )
    orders_result = await db.execute(orders_stmt)
    orders = orders_result.scalars().all()

    if not orders:
        raise HTTPException(status_code=400, detail="No pending orders found for this date")

    # 2. Run Optimization
    # Initialize optimizer with constraints
    optimizer = VehicleRoutingOptimizer(planning_time_limit_sec=5)  # fast optimized for demo

    try:
        solution_routes = optimizer.optimize(orders, vehicles, depot, route_date)
    except Exception as e:
        # Log error
        raise HTTPException(status_code=500, detail=f"Optimization failed: {e!s}")

    if not solution_routes:
        return {"message": "No solution found that satisfies all constraints", "routes": []}

    # 3. Save Routes to Database
    # We don't commit immediately for "preview" mode, but here we assume we want to create them.
    # Or we could return them as a preview. Let's return as preview first or create based on a flag?
    # The requirement usually implies action. Let's return the preview structure.
    # If the user wants to "Apply", that would be a separate confirmation step or we assume this IS the action.
    # Given the standard flow, let's persist them as "planned" routes.

    created_routes = []

    # We need to map solution back to DB objects
    # The optimizer returns dictionaries.

    total_distance = 0
    total_stops = 0

    # Note: In a real app, we might want to delete existing planned routes for this day/depot first if re-optimizing?
    # For now, we assume we are just creating new ones.

    return {
        "status": "success",
        "message": f"Generated {len(solution_routes)} routes",
        "routes": solution_routes,  # The frontend can render these
        "metrics": {
            "total_vehicles_used": len(solution_routes),
            "total_orders_scheduled": sum(len(r["stops"]) for r in solution_routes),
            "total_distance_km": sum(r["metrics"]["total_distance_km"] for r in solution_routes),
        },
    }

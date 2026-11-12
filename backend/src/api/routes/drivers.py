"""Drivers API endpoints - with DATABASE integration."""

from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from src.database import get_db
from src.events import (
    DriverStatus,
    DriverStatusEvent,
    GPSLocationEvent,
    Location,
    get_kafka_producer,
)
from src.models import Driver, Route, Vehicle

router = APIRouter()


# ============================================
# Request/Response Models
# ============================================


class UpdateLocationRequest(BaseModel):
    """GPS location update from driver app."""

    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    speed_kmh: float | None = Field(None, ge=0)
    heading: float | None = Field(None, ge=0, le=360)
    accuracy_m: float | None = Field(None, ge=0)
    altitude_m: float | None = None
    battery_level: int | None = Field(None, ge=0, le=100)
    is_moving: bool = True


class UpdateStatusRequest(BaseModel):
    """Status update request."""

    status: str = Field(..., pattern="^(available|on_route|on_break|offline)$")
    reason: str | None = None


# ============================================
# Endpoints
# ============================================


@router.get("")
async def list_drivers(
    status: str | None = Query(None, description="Filter by status"),
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """List all drivers with optional status filter."""
    # Build query
    stmt = select(Driver).options(joinedload(Driver.preferred_depot)).limit(limit)

    if status:
        stmt = stmt.where(Driver.status == status)

    # Execute query
    result = await db.execute(stmt)
    drivers = result.scalars().unique().all()

    # Get total count
    count_stmt = select(func.count(Driver.id))
    if status:
        count_stmt = count_stmt.where(Driver.status == status)
    total_result = await db.execute(count_stmt)
    total = total_result.scalar()

    # Find current vehicle for each driver
    vehicle_stmt = select(Vehicle).where(Vehicle.current_driver_id.in_([d.id for d in drivers]))
    vehicle_result = await db.execute(vehicle_stmt)
    vehicles = {v.current_driver_id: v for v in vehicle_result.scalars().all()}

    # Format response
    driver_list = []
    for driver in drivers:
        vehicle = vehicles.get(driver.id)
        driver_data = {
            "id": str(driver.id),
            "employee_id": driver.employee_id,
            "name": driver.full_name,
            "email": driver.email,
            "phone": driver.phone,
            "status": driver.status,
            "rating": float(driver.rating),
            "total_deliveries": driver.total_deliveries,
            "current_location": None,
            "vehicle": None,
        }

        if vehicle and vehicle.latitude and vehicle.longitude:
            driver_data["current_location"] = {
                "latitude": float(vehicle.latitude),
                "longitude": float(vehicle.longitude),
            }
            driver_data["vehicle"] = {
                "id": str(vehicle.id),
                "number": vehicle.vehicle_number,
                "type": vehicle.type,
            }

        driver_list.append(driver_data)

    return {
        "drivers": driver_list,
        "total": total,
    }


@router.get("/{driver_id}")
async def get_driver(
    driver_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get driver details by ID."""
    # Query driver with relationships
    stmt = select(Driver).options(joinedload(Driver.preferred_depot)).where(Driver.id == driver_id)

    result = await db.execute(stmt)
    driver = result.scalar_one_or_none()

    if not driver:
        raise HTTPException(status_code=404, detail="Driver not found")

    # Get current vehicle
    vehicle_stmt = select(Vehicle).where(Vehicle.current_driver_id == driver_id)
    vehicle_result = await db.execute(vehicle_stmt)
    vehicle = vehicle_result.scalar_one_or_none()

    # Get current route
    route_stmt = (
        select(Route)
        .where(and_(Route.driver_id == driver_id, Route.status == "in_progress"))
        .limit(1)
    )
    route_result = await db.execute(route_stmt)
    current_route = route_result.scalar_one_or_none()

    # Build response
    response = {
        "id": str(driver.id),
        "employee_id": driver.employee_id,
        "name": driver.full_name,
        "email": driver.email,
        "phone": driver.phone,
        "status": driver.status,
        "rating": float(driver.rating),
        "total_deliveries": driver.total_deliveries,
        "license_number": driver.license_number,
        "license_expiry": driver.license_expiry.isoformat() if driver.license_expiry else None,
        "max_working_hours_per_day": float(driver.max_working_hours_per_day),
    }

    if driver.preferred_depot:
        response["preferred_depot"] = {
            "id": str(driver.preferred_depot.id),
            "name": driver.preferred_depot.name,
        }

    if vehicle:
        response["current_vehicle"] = {
            "id": str(vehicle.id),
            "number": vehicle.vehicle_number,
            "type": vehicle.type,
            "capacity_kg": float(vehicle.capacity_kg),
        }
        if vehicle.latitude and vehicle.longitude:
            response["current_location"] = {
                "latitude": float(vehicle.latitude),
                "longitude": float(vehicle.longitude),
                "updated_at": vehicle.updated_at.isoformat(),
            }

    if current_route:
        response["current_route"] = {
            "id": str(current_route.id),
            "stops_completed": current_route.completed_stops,
            "stops_total": current_route.planned_stops,
            "started_at": (
                current_route.started_at.isoformat() if current_route.started_at else None
            ),
        }

    # TODO: Calculate stats from database
    response["stats"] = {
        "on_time_rate": 0.96,
        "avg_delivery_time_minutes": 22,
        "deliveries_today": 0,
        "distance_today_km": 0.0,
    }

    return response


@router.post("/{driver_id}/location")
async def update_location(
    driver_id: UUID,
    request: UpdateLocationRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """
    Update driver's GPS location.

    Updates the vehicle's current location and publishes to Kafka.
    """
    # Get driver's current vehicle
    vehicle_stmt = select(Vehicle).where(Vehicle.current_driver_id == driver_id)
    result = await db.execute(vehicle_stmt)
    vehicle = result.scalar_one_or_none()

    if not vehicle:
        raise HTTPException(status_code=404, detail="Driver has no assigned vehicle")

    # Update vehicle location (trigger will sync with PostGIS)
    vehicle.latitude = Decimal(str(request.latitude))
    vehicle.longitude = Decimal(str(request.longitude))
    vehicle.updated_at = datetime.now(UTC).replace(tzinfo=None)

    await db.commit()

    # Publish GPS event to Kafka
    event = GPSLocationEvent(
        driver_id=driver_id,
        vehicle_id=vehicle.id,
        location=Location(
            latitude=request.latitude,
            longitude=request.longitude,
        ),
        speed_kmh=request.speed_kmh,
        heading=request.heading,
        accuracy_m=request.accuracy_m,
        altitude_m=request.altitude_m,
        battery_level=request.battery_level,
        is_moving=request.is_moving,
    )

    async def publish_event():
        producer = get_kafka_producer()
        await producer.publish_async(
            topic="gps.location",
            event=event,
            key=str(driver_id),
        )

    background_tasks.add_task(publish_event)

    return {
        "driver_id": str(driver_id),
        "vehicle_id": str(vehicle.id),
        "location": {
            "latitude": request.latitude,
            "longitude": request.longitude,
        },
        "received_at": datetime.now(UTC).isoformat(),
    }


@router.post("/{driver_id}/status")
async def update_status(
    driver_id: UUID,
    request: UpdateStatusRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """
    Update driver's status.

    Publishes DriverStatusEvent to Kafka.
    """
    # Get driver
    stmt = select(Driver).where(Driver.id == driver_id)
    result = await db.execute(stmt)
    driver = result.scalar_one_or_none()

    if not driver:
        raise HTTPException(status_code=404, detail="Driver not found")

    previous_status = DriverStatus(driver.status)
    new_status = DriverStatus(request.status)

    # Update status
    driver.status = request.status
    driver.updated_at = datetime.now(UTC).replace(tzinfo=None)

    await db.commit()

    # Publish event
    event = DriverStatusEvent(
        driver_id=driver_id,
        previous_status=previous_status,
        new_status=new_status,
        reason=request.reason,
    )

    async def publish_event():
        producer = get_kafka_producer()
        await producer.publish_async(
            topic="drivers.status",
            event=event,
            key=str(driver_id),
        )

    background_tasks.add_task(publish_event)

    return {
        "driver_id": str(driver_id),
        "previous_status": previous_status.value,
        "new_status": new_status.value,
        "updated_at": datetime.now(UTC).isoformat(),
    }


@router.get("/{driver_id}/route")
async def get_driver_current_route(
    driver_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get driver's current route."""
    stmt = (
        select(Route)
        .where(and_(Route.driver_id == driver_id, Route.status == "in_progress"))
        .limit(1)
    )

    result = await db.execute(stmt)
    route = result.scalar_one_or_none()

    if not route:
        return None

    # TODO: Load route stops with orders
    # For now return basic route info
    return {
        "route_id": str(route.id),
        "driver_id": str(driver_id),
        "status": route.status,
        "started_at": route.started_at.isoformat() if route.started_at else None,
        "progress": {
            "completed": route.completed_stops,
            "total": route.planned_stops,
        },
    }


@router.get("/stats/summary")
async def get_driver_stats(db: AsyncSession = Depends(get_db)):
    """Get driver fleet statistics."""
    # Get total count
    total_stmt = select(func.count(Driver.id))
    total_result = await db.execute(total_stmt)
    total_drivers = total_result.scalar()

    # Get count by status
    status_stmt = select(Driver.status, func.count(Driver.id)).group_by(Driver.status)

    status_result = await db.execute(status_stmt)
    by_status = dict(status_result.all())

    # Get average rating
    rating_stmt = select(func.avg(Driver.rating))
    rating_result = await db.execute(rating_stmt)
    avg_rating = rating_result.scalar()

    return {
        "total_drivers": total_drivers,
        "by_status": {
            "available": by_status.get("available", 0),
            "on_route": by_status.get("on_route", 0),
            "on_break": by_status.get("on_break", 0),
            "offline": by_status.get("offline", 0),
        },
        "active_today": by_status.get("on_route", 0) + by_status.get("available", 0),
        "avg_rating": float(avg_rating) if avg_rating else 0.0,
        "avg_deliveries_per_driver": 0,  # TODO: Calculate from routes
        "fleet_utilization": 0.0,  # TODO: Calculate
    }

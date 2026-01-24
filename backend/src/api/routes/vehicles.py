"""Vehicles API endpoints - with DATABASE integration."""

from datetime import datetime
from typing import Optional
from uuid import UUID
from decimal import Decimal

from fastapi import APIRouter, HTTPException, Query, Depends
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from src.database import get_db
from src.models import Vehicle, Driver, Depot

router = APIRouter()


@router.get("")
async def list_vehicles(
    status: Optional[str] = Query(None),
    depot_id: Optional[UUID] = Query(None),
    type: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """List all vehicles with optional filters."""
    # Build query
    stmt = select(Vehicle).options(
        joinedload(Vehicle.current_driver),
        joinedload(Vehicle.depot)
    ).limit(limit)
    
    conditions = []
    if status:
        conditions.append(Vehicle.status == status)
    if depot_id:
        conditions.append(Vehicle.depot_id == depot_id)
    if type:
        conditions.append(Vehicle.type == type)
    
    if conditions:
        stmt = stmt.where(and_(*conditions))
    
    # Execute
    result = await db.execute(stmt)
    vehicles = result.scalars().unique().all()
    
    # Get total count
    count_stmt = select(func.count(Vehicle.id))
    if conditions:
        count_stmt = count_stmt.where(and_(*conditions))
    total_result = await db.execute(count_stmt)
    total = total_result.scalar()
    
    # Format response
    vehicle_list = []
    for vehicle in vehicles:
        vehicle_data = {
            "id": str(vehicle.id),
            "vehicle_number": vehicle.vehicle_number,
            "type": vehicle.type,
            "make": vehicle.make,
            "model": vehicle.model,
            "year": vehicle.year,
            "capacity_kg": float(vehicle.capacity_kg),
            "fuel_type": vehicle.fuel_type,
            "status": vehicle.status,
            "current_driver": None,
            "current_location": None,
            "depot": None,
        }
        
        if vehicle.current_driver:
            vehicle_data["current_driver"] = {
                "id": str(vehicle.current_driver.id),
                "name": vehicle.current_driver.full_name,
            }
        
        if vehicle.latitude and vehicle.longitude:
            vehicle_data["current_location"] = {
                "latitude": float(vehicle.latitude),
                "longitude": float(vehicle.longitude),
            }
        
        if vehicle.depot:
            vehicle_data["depot"] = {
                "id": str(vehicle.depot.id),
                "name": vehicle.depot.name,
            }
        
        vehicle_list.append(vehicle_data)
    
    return {
        "vehicles": vehicle_list,
        "total": total,
    }


@router.get("/{vehicle_id}")
async def get_vehicle(
    vehicle_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get vehicle details by ID."""
    # Query with relationships
    stmt = select(Vehicle).options(
        joinedload(Vehicle.current_driver),
        joinedload(Vehicle.depot)
    ).where(Vehicle.id == vehicle_id)
    
    result = await db.execute(stmt)
    vehicle = result.scalar_one_or_none()
    
    if not vehicle:
        raise HTTPException(status_code=404, detail="Vehicle not found")
    
    response = {
        "id": str(vehicle.id),
        "vehicle_number": vehicle.vehicle_number,
        "type": vehicle.type,
        "make": vehicle.make,
        "model": vehicle.model,
        "year": vehicle.year,
        "capacity_kg": float(vehicle.capacity_kg),
        "capacity_cubic_m": float(vehicle.capacity_cubic_m) if vehicle.capacity_cubic_m else None,
        "fuel_type": vehicle.fuel_type,
        "fuel_efficiency_km_per_l": float(vehicle.fuel_efficiency_km_per_l) if vehicle.fuel_efficiency_km_per_l else None,
        "co2_emission_g_per_km": float(vehicle.co2_emission_g_per_km) if vehicle.co2_emission_g_per_km else None,
        "status": vehicle.status,
    }
    
    if vehicle.current_driver:
        response["current_driver"] = {
            "id": str(vehicle.current_driver.id),
            "name": vehicle.current_driver.full_name,
        }
    
    if vehicle.latitude and vehicle.longitude:
        response["current_location"] = {
            "latitude": float(vehicle.latitude),
            "longitude": float(vehicle.longitude),
            "updated_at": vehicle.updated_at.isoformat(),
        }
    
    if vehicle.depot:
        response["depot"] = {
            "id": str(vehicle.depot.id),
            "name": vehicle.depot.name,
            "address": vehicle.depot.address,
        }
    
    if vehicle.last_maintenance_date or vehicle.next_maintenance_date:
        response["maintenance"] = {
            "last_date": vehicle.last_maintenance_date.isoformat() if vehicle.last_maintenance_date else None,
            "next_date": vehicle.next_maintenance_date.isoformat() if vehicle.next_maintenance_date else None,
        }
    
    # TODO: Calculate stats from routes/deliveries
    response["stats"] = {
        "total_distance_km": 0,
        "deliveries_completed": 0,
        "utilization_rate": 0.0,
    }
    
    return response


@router.get("/{vehicle_id}/location")
async def get_vehicle_location(
    vehicle_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get vehicle's current location."""
    stmt = select(Vehicle).options(
        joinedload(Vehicle.current_driver)
    ).where(Vehicle.id == vehicle_id)
    
    result = await db.execute(stmt)
    vehicle = result.scalar_one_or_none()
    
    if not vehicle:
        raise HTTPException(status_code=404, detail="Vehicle not found")
    
    if not vehicle.latitude or not vehicle.longitude:
        raise HTTPException(status_code=404, detail="Vehicle location not available")
    
    return {
        "vehicle_id": str(vehicle.id),
        "location": {
            "latitude": float(vehicle.latitude),
            "longitude": float(vehicle.longitude),
        },
        "updated_at": vehicle.updated_at.isoformat(),
        "driver_id": str(vehicle.current_driver.id) if vehicle.current_driver else None,
    }


@router.get("/stats/summary")
async def get_vehicle_stats(db: AsyncSession = Depends(get_db)):
    """Get fleet vehicle statistics."""
    # Total vehicles
    total_stmt = select(func.count(Vehicle.id))
    total_result = await db.execute(total_stmt)
    total = total_result.scalar()
    
    # Count by status
    status_stmt = select(
        Vehicle.status,
        func.count(Vehicle.id)
    ).group_by(Vehicle.status)
    
    status_result = await db.execute(status_stmt)
    by_status = dict(status_result.all())
    
    # Count by type
    type_stmt = select(
        Vehicle.type,
        func.count(Vehicle.id)
    ).group_by(Vehicle.type)
    
    type_result = await db.execute(type_stmt)
    by_type = dict(type_result.all())
    
    # Count by fuel
    fuel_stmt = select(
        Vehicle.fuel_type,
        func.count(Vehicle.id)
    ).group_by(Vehicle.fuel_type)
    
    fuel_result = await db.execute(fuel_stmt)
    by_fuel = dict(fuel_result.all())
    
    # Count needing maintenance (next_maintenance_date within 7 days)
    from datetime import date, timedelta
    today = date.today()
    week_from_now = today + timedelta(days=7)
    
    maintenance_stmt = select(func.count(Vehicle.id)).where(
        and_(
            Vehicle.next_maintenance_date.isnot(None),
            Vehicle.next_maintenance_date <= week_from_now
        )
    )
    maintenance_result = await db.execute(maintenance_stmt)
    needing_maintenance = maintenance_result.scalar()
    
    return {
        "total_vehicles": total,
        "by_status": {
            "available": by_status.get("available", 0),
            "in_use": by_status.get("in_use", 0),
            "maintenance": by_status.get("maintenance", 0),
            "retired": by_status.get("retired", 0),
        },
        "by_type": {
            "van": by_type.get("van", 0),
            "truck": by_type.get("truck", 0),
            "bike": by_type.get("bike", 0),
            "car": by_type.get("car", 0),
        },
        "by_fuel": {
            "diesel": by_fuel.get("diesel", 0),
            "electric": by_fuel.get("electric", 0),
            "hybrid": by_fuel.get("hybrid", 0),
            "petrol": by_fuel.get("petrol", 0),
        },
        "avg_utilization_rate": 0.78,  # TODO: Calculate from route data
        "total_distance_today_km": 0.0,  # TODO: Calculate from today's routes
        "vehicles_needing_maintenance": needing_maintenance,
    }

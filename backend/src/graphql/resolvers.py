"""
GraphQL Resolvers for FleetFlow.
"""

from typing import Optional, List
from uuid import UUID
import strawberry
from strawberry.types import Info
from sqlalchemy import select, func
from sqlalchemy.orm import joinedload

from src.database import AsyncSessionLocal
from src.models import Driver as DriverModel, Order as OrderModel, Route as RouteModel
from src.models import Vehicle as VehicleModel, Depot as DepotModel
from src.graphql.types import (
    Driver, Order, Route, Vehicle, Depot, Location,
    DriverStats, OrderStats, RouteStats, DashboardStats,
    OptimizationResult, RouteStop, OrderItem,
)


# Helper to convert DB models to GraphQL types
def db_driver_to_graphql(driver: DriverModel, vehicle: Optional[VehicleModel] = None) -> Driver:
    """Convert DB driver to GraphQL type."""
    current_location = None
    current_vehicle = None
    
    if vehicle:
        if vehicle.latitude and vehicle.longitude:
            current_location = Location(
                latitude=float(vehicle.latitude),
                longitude=float(vehicle.longitude),
            )
        current_vehicle = Vehicle(
            id=strawberry.ID(str(vehicle.id)),
            vehicle_number=vehicle.vehicle_number,
            type=vehicle.type,
            capacity_kg=float(vehicle.capacity_kg),
            status=vehicle.status,
            current_location=current_location,
        )
    
    return Driver(
        id=strawberry.ID(str(driver.id)),
        employee_id=driver.employee_id,
        name=driver.full_name,
        email=driver.email,
        phone=driver.phone,
        status=driver.status,
        rating=float(driver.rating),
        total_deliveries=driver.total_deliveries,
        current_location=current_location,
        current_vehicle=current_vehicle,
    )


def db_order_to_graphql(order: OrderModel) -> Order:
    """Convert DB order to GraphQL type."""
    items = [
        OrderItem(
            name=item.get("name", "Item"),
            quantity=item.get("quantity", 1),
            weight_kg=item.get("weight_kg", 0),
        )
        for item in (order.items or [])
    ]
    
    return Order(
        id=strawberry.ID(str(order.id)),
        order_number=order.order_number,
        status=order.status,
        priority=order.priority,
        delivery_date=order.delivery_date.isoformat() if order.delivery_date else "",
        time_window_start=order.time_window_start.isoformat() if order.time_window_start else "",
        time_window_end=order.time_window_end.isoformat() if order.time_window_end else "",
        total_weight_kg=float(order.total_weight_kg),
        total_value=float(order.total_value) if order.total_value else None,
        items=items,
    )


@strawberry.type
class Query:
    """GraphQL Query resolvers."""
    
    @strawberry.field
    async def drivers(
        self,
        status: Optional[str] = None,
        limit: int = 50,
    ) -> List[Driver]:
        """Get all drivers."""
        async with AsyncSessionLocal() as db:
            stmt = select(DriverModel).limit(limit)
            if status:
                stmt = stmt.where(DriverModel.status == status)
            
            result = await db.execute(stmt)
            drivers = result.scalars().all()
            
            # Get vehicles
            vehicle_stmt = select(VehicleModel).where(
                VehicleModel.current_driver_id.in_([d.id for d in drivers])
            )
            vehicle_result = await db.execute(vehicle_stmt)
            vehicles = {v.current_driver_id: v for v in vehicle_result.scalars().all()}
            
            return [
                db_driver_to_graphql(driver, vehicles.get(driver.id))
                for driver in drivers
            ]
    
    @strawberry.field
    async def driver(self, id: strawberry.ID) -> Optional[Driver]:
        """Get driver by ID."""
        async with AsyncSessionLocal() as db:
            stmt = select(DriverModel).where(DriverModel.id == UUID(id))
            result = await db.execute(stmt)
            driver = result.scalar_one_or_none()
            
            if not driver:
                return None
            
            # Get vehicle
            vehicle_stmt = select(VehicleModel).where(
                VehicleModel.current_driver_id == driver.id
            )
            vehicle_result = await db.execute(vehicle_stmt)
            vehicle = vehicle_result.scalar_one_or_none()
            
            return db_driver_to_graphql(driver, vehicle)
    
    @strawberry.field
    async def orders(
        self,
        status: Optional[str] = None,
        date: Optional[str] = None,
        limit: int = 50,
    ) -> List[Order]:
        """Get all orders."""
        async with AsyncSessionLocal() as db:
            stmt = select(OrderModel).limit(limit)
            if status:
                stmt = stmt.where(OrderModel.status == status)
            
            result = await db.execute(stmt)
            orders = result.scalars().all()
            
            return [db_order_to_graphql(order) for order in orders]
    
    @strawberry.field
    async def order(self, id: strawberry.ID) -> Optional[Order]:
        """Get order by ID."""
        async with AsyncSessionLocal() as db:
            stmt = select(OrderModel).where(OrderModel.id == UUID(id))
            result = await db.execute(stmt)
            order = result.scalar_one_or_none()
            
            return db_order_to_graphql(order) if order else None
    
    @strawberry.field
    async def dashboard_stats(self) -> DashboardStats:
        """Get dashboard statistics."""
        async with AsyncSessionLocal() as db:
            # Driver stats
            driver_stmt = select(
                DriverModel.status,
                func.count(DriverModel.id)
            ).group_by(DriverModel.status)
            driver_result = await db.execute(driver_stmt)
            driver_by_status = dict(driver_result.all())
            
            driver_total_stmt = select(func.count(DriverModel.id))
            driver_total = (await db.execute(driver_total_stmt)).scalar()
            
            rating_stmt = select(func.avg(DriverModel.rating))
            avg_rating = (await db.execute(rating_stmt)).scalar() or 0
            
            # Order stats
            order_stmt = select(
                OrderModel.status,
                func.count(OrderModel.id)
            ).group_by(OrderModel.status)
            order_result = await db.execute(order_stmt)
            order_by_status = dict(order_result.all())
            
            order_total_stmt = select(func.count(OrderModel.id))
            order_total = (await db.execute(order_total_stmt)).scalar()
            
            # Route stats
            route_total_stmt = select(func.count(RouteModel.id))
            route_total = (await db.execute(route_total_stmt)).scalar()
            
            return DashboardStats(
                drivers=DriverStats(
                    total_drivers=driver_total or 0,
                    available=driver_by_status.get("available", 0),
                    on_route=driver_by_status.get("on_route", 0),
                    on_break=driver_by_status.get("on_break", 0),
                    offline=driver_by_status.get("offline", 0),
                    avg_rating=float(avg_rating),
                ),
                orders=OrderStats(
                    total_orders=order_total or 0,
                    pending=order_by_status.get("pending", 0),
                    in_transit=order_by_status.get("in_transit", 0),
                    delivered=order_by_status.get("delivered", 0),
                    failed=order_by_status.get("failed", 0),
                ),
                routes=RouteStats(
                    total_routes=route_total or 0,
                    in_progress=0,  # TODO
                    completed=0,  # TODO
                    total_distance_km=0.0,
                    avg_stops_per_route=0.0,
                ),
            )


@strawberry.type
class Mutation:
    """GraphQL Mutation resolvers."""
    
    @strawberry.mutation
    async def update_driver_location(
        self,
        driver_id: strawberry.ID,
        latitude: float,
        longitude: float,
        speed_kmh: Optional[float] = None,
    ) -> Driver:
        """Update driver location."""
        # Update vehicle location directly in DB
        async with AsyncSessionLocal() as db:
            # Get driver
            stmt = select(DriverModel).where(DriverModel.id == UUID(driver_id))
            result = await db.execute(stmt)
            driver = result.scalar_one_or_none()
            
            if not driver:
                raise ValueError("Driver not found")
            
            # Get and update vehicle
            vehicle_stmt = select(VehicleModel).where(
                VehicleModel.current_driver_id == driver.id
            )
            vehicle_result = await db.execute(vehicle_stmt)
            vehicle = vehicle_result.scalar_one_or_none()
            
            if vehicle:
                vehicle.latitude = latitude
                vehicle.longitude = longitude
                await db.commit()
            
            return db_driver_to_graphql(driver, vehicle)
    
    @strawberry.mutation
    async def cancel_order(
        self,
        order_id: strawberry.ID,
        reason: Optional[str] = None,
    ) -> Order:
        """Cancel an order."""
        async with AsyncSessionLocal() as db:
            stmt = select(OrderModel).where(OrderModel.id == UUID(order_id))
            result = await db.execute(stmt)
            order = result.scalar_one_or_none()
            
            if not order:
                raise ValueError("Order not found")
            
            order.status = "cancelled"
            await db.commit()
            await db.refresh(order)
            
            return db_order_to_graphql(order)

"""Orders API endpoints - with DATABASE integration."""

from datetime import datetime, date
from typing import Optional
from uuid import UUID, uuid4
from decimal import Decimal

from fastapi import APIRouter, HTTPException, Query, BackgroundTasks, Depends
from pydantic import BaseModel, Field
from sqlalchemy import select, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from src.database import get_db
from src.models import Order, Customer, Depot, Route, Driver
from src.events import (
    get_kafka_producer,
    OrderCreatedEvent,
    OrderCancelledEvent,
    Location,
    Address,
    TimeWindow,
    OrderItem,
    OrderPriority,
)

router = APIRouter()


# ============================================
# Request/Response Models
# ============================================

class CreateOrderRequest(BaseModel):
    """Request to create a new order."""
    customer_id: Optional[UUID] = None  # If existing customer
    customer_name: str
    customer_email: Optional[str] = None
    customer_phone: Optional[str] = None
    
    # Address
    street: str
    city: str
    state: str
    postal_code: str
    latitude: float
    longitude: float
    
    # Delivery
    delivery_date: str  # ISO date
    time_window_start: datetime
    time_window_end: datetime
    
    # Items
    items: list[dict] = Field(default_factory=list)
    total_weight_kg: float
    total_value: Optional[float] = None
    
    # Options
    priority: int = Field(default=2, ge=1, le=5)
    special_instructions: Optional[str] = None
    external_order_id: Optional[str] = None


class CancelOrderRequest(BaseModel):
    """Request to cancel an order."""
    reason: str
    cancelled_by: str = "dispatcher"


# ============================================
# Endpoints
# ============================================

@router.post("", status_code=201)
async def create_order(
    request: CreateOrderRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """
    Create a new delivery order.
    
    Creates customer if needed, inserts order, publishes to Kafka.
    """
    # Find or create customer
    customer_id = request.customer_id
    
    if not customer_id:
        # Create new customer
        customer = Customer(
            name=request.customer_name,
            email=request.customer_email,
            phone=request.customer_phone,
            address=f"{request.street}, {request.city}, {request.state} {request.postal_code}",
            latitude=Decimal(str(request.latitude)),
            longitude=Decimal(str(request.longitude)),
        )
        db.add(customer)
        await db.flush()
        customer_id = customer.id
    
    # Find nearest depot
    depot_stmt = select(Depot).where(Depot.is_active == True).limit(1)
    depot_result = await db.execute(depot_stmt)
    depot = depot_result.scalar_one_or_none()
    
    if not depot:
        raise HTTPException(status_code=500, detail="No active depot found")
    
    # Create order
    order_number = f"ORD-{datetime.utcnow().strftime('%Y%m%d')}-{str(uuid4())[:8].upper()}"
    
    order = Order(
        order_number=order_number,
        customer_id=customer_id,
        depot_id=depot.id,
        items=request.items,
        total_weight_kg=Decimal(str(request.total_weight_kg)),
        total_value=Decimal(str(request.total_value)) if request.total_value else None,
        delivery_date=date.fromisoformat(request.delivery_date),
        time_window_start=request.time_window_start,
        time_window_end=request.time_window_end,
        status="pending",
        priority=request.priority,
        source="api",
        external_order_id=request.external_order_id,
    )
    
    db.add(order)
    await db.commit()
    await db.refresh(order)
    
    # Publish Kafka event
    event = OrderCreatedEvent(
        order_id=order.id,
        order_number=order.order_number,
        customer_id=customer_id,
        delivery_address=Address(
            street=request.street,
            city=request.city,
            state=request.state,
            postal_code=request.postal_code,
            location=Location(
                latitude=request.latitude,
                longitude=request.longitude,
            ),
        ),
        delivery_date=request.delivery_date,
        time_window=TimeWindow(
            start=request.time_window_start,
            end=request.time_window_end,
        ),
        items=[OrderItem(**item) for item in request.items] if request.items else [],
        total_weight_kg=request.total_weight_kg,
        total_value=request.total_value,
        priority=OrderPriority(request.priority),
        special_instructions=request.special_instructions,
        external_order_id=request.external_order_id,
        source="api",
    )
    
    async def publish_event():
        producer = get_kafka_producer()
        await producer.publish_async(
            topic="orders.created",
            event=event,
            key=str(order.id),
        )
    
    background_tasks.add_task(publish_event)
    
    return {
        "order_id": str(order.id),
        "order_number": order.order_number,
        "status": order.status,
        "customer_name": request.customer_name,
        "address": f"{request.street}, {request.city}, {request.state} {request.postal_code}",
        "delivery_date": request.delivery_date,
        "time_window": f"{request.time_window_start.strftime('%I:%M %p')} - {request.time_window_end.strftime('%I:%M %p')}",
        "priority": request.priority,
        "total_weight_kg": request.total_weight_kg,
        "created_at": order.created_at.isoformat(),
    }


@router.get("")
async def list_orders(
    date: Optional[str] = Query(None, description="Filter by delivery date (ISO format)"),
    status: Optional[str] = Query(None, description="Filter by status"),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """List orders with optional filters."""
    # Build query
    stmt = select(Order).options(
        joinedload(Order.customer)
    ).offset(offset).limit(limit)
    
    conditions = []
    if date:
        conditions.append(Order.delivery_date == date)
    if status:
        conditions.append(Order.status == status)
    
    if conditions:
        stmt = stmt.where(and_(*conditions))
    
    stmt = stmt.order_by(Order.created_at.desc())
    
    # Execute
    result = await db.execute(stmt)
    orders = result.scalars().unique().all()
    
    # Get total count
    count_stmt = select(func.count(Order.id))
    if conditions:
        count_stmt = count_stmt.where(and_(*conditions))
    total_result = await db.execute(count_stmt)
    total = total_result.scalar()
    
    # Format response
    order_list = []
    for order in orders:
        order_list.append({
            "order_id": str(order.id),
            "order_number": order.order_number,
            "status": order.status,
            "customer_name": order.customer.name if order.customer else "Unknown",
            "address": order.customer.address if order.customer else "N/A",
            "delivery_date": order.delivery_date.isoformat(),
            "time_window": f"{order.time_window_start.strftime('%I:%M %p')} - {order.time_window_end.strftime('%I:%M %p')}",
            "priority": order.priority,
            "total_weight_kg": float(order.total_weight_kg),
        })
    
    return {
        "orders": order_list,
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.get("/{order_id}")
async def get_order(
    order_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get order by ID with full details."""
    # Query with relationships
    stmt = select(Order).options(
        joinedload(Order.customer),
        joinedload(Order.depot)
    ).where(Order.id == order_id)
    
    result = await db.execute(stmt)
    order = result.scalar_one_or_none()
    
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    # Find assigned route/driver (if any)
    route_stmt = select(Route).options(
        joinedload(Route.driver)
    ).join(
        Driver  # This assumes route_stops table exists with order_id FK
    ).where(
        and_(
            Route.status.in_(["planned", "in_progress"]),
            # Would need route_stops join here
        )
    ).limit(1)
    
    # For now, simple route lookup
    route = None  # TODO: Implement route_stops join
    
    response = {
        "order_id": str(order.id),
        "order_number": order.order_number,
        "status": order.status,
        "customer": {
            "name": order.customer.name,
            "email": order.customer.email,
            "phone": order.customer.phone,
        } if order.customer else None,
        "address": {
            "street": order.customer.address if order.customer else "",
            "latitude": float(order.customer.latitude) if order.customer else 0,
            "longitude": float(order.customer.longitude) if order.customer else 0,
        } if order.customer else None,
        "delivery_date": order.delivery_date.isoformat(),
        "time_window": {
            "start": order.time_window_start.strftime("%H:%M:%S"),
            "end": order.time_window_end.strftime("%H:%M:%S"),
        },
        "items": order.items,
        "total_weight_kg": float(order.total_weight_kg),
        "total_value": float(order.total_value) if order.total_value else None,
        "priority": order.priority,
        "assigned_route_id": str(route.id) if route else None,
        "driver": {
            "id": str(route.driver.id),
            "name": route.driver.full_name,
        } if route and route.driver else None,
    }
    
    return response


@router.post("/{order_id}/cancel")
async def cancel_order(
    order_id: UUID,
    request: CancelOrderRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """Cancel an order."""
    # Get order
    stmt = select(Order).where(Order.id == order_id)
    result = await db.execute(stmt)
    order = result.scalar_one_or_none()
    
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    if order.status in ["delivered", "cancelled"]:
        raise HTTPException(status_code=400, detail=f"Cannot cancel order with status: {order.status}")
    
    # Update status
    order.status = "cancelled"
    order.updated_at = datetime.utcnow()
    
    await db.commit()
    
    # Publish event
    event = OrderCancelledEvent(
        order_id=order_id,
        order_number=order.order_number,
        reason=request.reason,
        cancelled_by=request.cancelled_by,
    )
    
    async def publish_event():
        producer = get_kafka_producer()
        await producer.publish_async(
            topic="orders.cancelled",
            event=event,
            key=str(order_id),
        )
    
    background_tasks.add_task(publish_event)
    
    return {
        "order_id": str(order_id),
        "status": "cancelled",
        "cancelled_at": datetime.utcnow().isoformat(),
        "reason": request.reason,
    }


@router.get("/stats/summary")
async def get_order_stats(
    date: Optional[str] = Query(None, description="Date for stats (ISO format)"),
    db: AsyncSession = Depends(get_db),
):
    """Get order statistics for dashboard."""
    target_date = date or datetime.utcnow().strftime("%Y-%m-%d")
    
    # Total orders for date
    total_stmt = select(func.count(Order.id))
    if date:
        total_stmt = total_stmt.where(Order.delivery_date == target_date)
    total_result = await db.execute(total_stmt)
    total = total_result.scalar()
    
    # Count by status
    status_stmt = select(
        Order.status,
        func.count(Order.id)
    )
    if date:
        status_stmt = status_stmt.where(Order.delivery_date == target_date)
    status_stmt = status_stmt.group_by(Order.status)
    
    status_result = await db.execute(status_stmt)
    by_status = dict(status_result.all())
    
    # Count by priority
    priority_stmt = select(
        Order.priority,
        func.count(Order.id)
    )
    if date:
        priority_stmt = priority_stmt.where(Order.delivery_date == target_date)
    priority_stmt = priority_stmt.group_by(Order.priority)
    
    priority_result = await db.execute(priority_stmt)
    priority_counts = dict(priority_result.all())
    
    return {
        "date": target_date,
        "total_orders": total,
        "by_status": {
            "pending": by_status.get("pending", 0),
            "assigned": by_status.get("assigned", 0),
            "in_transit": by_status.get("in_transit", 0),
            "delivered": by_status.get("delivered", 0),
            "failed": by_status.get("failed", 0),
            "cancelled": by_status.get("cancelled", 0),
        },
        "by_priority": {
            "1": priority_counts.get(1, 0),
            "2": priority_counts.get(2, 0),
            "3": priority_counts.get(3, 0),
            "4": priority_counts.get(4, 0),
            "5": priority_counts.get(5, 0),
        },
        "on_time_rate": 0.94,  # TODO: Calculate from actual delivery times
        "avg_delivery_time_minutes": 24,  # TODO: Calculate from route data
    }

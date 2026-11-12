"""
Tests for Orders API endpoints.
"""

import pytest
from httpx import AsyncClient
from datetime import datetime, timedelta


@pytest.mark.asyncio
async def test_list_orders_empty(client: AsyncClient):
    """Test listing orders when none exist."""
    response = await client.get("/api/v1/orders")
    assert response.status_code == 200
    data = response.json()
    assert "orders" in data
    assert isinstance(data["orders"], list)


@pytest.mark.asyncio
async def test_list_orders_with_filters(client: AsyncClient, sample_depot, sample_order):
    """Test listing orders with status filter."""
    depot = await sample_depot()
    await sample_order(depot_id=depot.id, status='pending')
    await sample_order(depot_id=depot.id, status='delivered')
    
    response = await client.get("/api/v1/orders?status=pending")
    assert response.status_code == 200
    data = response.json()
    assert len(data["orders"]) >= 1
    assert all(o["status"] == "pending" for o in data["orders"])


@pytest.mark.asyncio
async def test_get_order_by_id(client: AsyncClient, sample_depot, sample_order):
    """Test getting a specific order."""
    depot = await sample_depot()
    order = await sample_order(depot_id=depot.id)
    
    response = await client.get(f"/api/v1/orders/{order.id}")
    assert response.status_code == 200
    data = response.json()
    assert data["order_id"] == str(order.id)
    assert data["order_number"] == order.order_number


@pytest.mark.asyncio
async def test_create_order(client: AsyncClient, sample_depot):
    """Test creating a new order."""
    depot = await sample_depot()
    now = datetime.utcnow()
    
    order_data = {
        "customer_name": "Test Customer",
        "customer_phone": "+1234567890",
        "street": "123 Test St",
        "city": "Glasgow",
        "state": "Scotland",
        "postal_code": "G1 1AA",
        "latitude": 55.8642,
        "longitude": -4.2518,
        "delivery_date": now.date().isoformat(),
        "time_window_start": (now + timedelta(hours=2)).isoformat(),
        "time_window_end": (now + timedelta(hours=4)).isoformat(),
        "items": [{"sku": "BOOK", "name": "Parcel", "quantity": 1, "weight_kg": 1.5}],
        "total_weight_kg": 1.5,
        "priority": 3,
    }

    response = await client.post("/api/v1/orders", json=order_data)
    assert response.status_code == 201
    data = response.json()
    assert data["order_number"].startswith("ORD-")
    assert data["order_id"]
    assert data["status"] == "pending"


@pytest.mark.asyncio
async def test_cancel_order(client: AsyncClient, sample_depot, sample_order):
    """Test cancelling an order."""
    depot = await sample_depot()
    order = await sample_order(depot_id=depot.id, status='pending')
    
    response = await client.post(
        f"/api/v1/orders/{order.id}/cancel",
        json={"reason": "Customer request"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "cancelled"


@pytest.mark.asyncio
async def test_get_pending_orders(client: AsyncClient, sample_depot, sample_order):
    """Test getting pending orders for optimization."""
    depot = await sample_depot()
    today = datetime.utcnow().date()
    
    # Create pending and non-pending orders
    await sample_order(depot_id=depot.id, status='pending')
    await sample_order(depot_id=depot.id, status='delivered')
    
    response = await client.get(f"/api/v1/orders?status=pending&date={today}")
    assert response.status_code == 200
    data = response.json()
    assert all(o["status"] == "pending" for o in data["orders"])

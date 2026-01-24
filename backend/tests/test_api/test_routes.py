"""
Tests for Routes API endpoints.
"""

import pytest
from httpx import AsyncClient
from datetime import datetime, date


@pytest.mark.asyncio
async def test_list_routes_empty(client: AsyncClient):
    """Test listing routes when none exist."""
    response = await client.get("/api/v1/routes")
    assert response.status_code == 200
    data = response.json()
    assert "routes" in data
    assert isinstance(data["routes"], list)


@pytest.mark.asyncio
async def test_list_routes_by_date(client: AsyncClient):
    """Test filtering routes by date."""
    today = date.today().isoformat()
    response = await client.get(f"/api/v1/routes?date={today}")
    assert response.status_code == 200
    data = response.json()
    assert "routes" in data


@pytest.mark.asyncio
async def test_get_route_not_found(client: AsyncClient):
    """Test getting non-existent route returns 404."""
    fake_id = "00000000-0000-0000-0000-000000000000"
    response = await client.get(f"/api/v1/routes/{fake_id}")
    assert response.status_code == 404

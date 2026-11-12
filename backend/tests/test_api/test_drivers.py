"""
Tests for Driver API endpoints.
"""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_list_drivers_empty(client: AsyncClient):
    """Test listing drivers when none exist."""
    response = await client.get("/api/v1/drivers")
    assert response.status_code == 200
    data = response.json()
    assert "drivers" in data
    assert isinstance(data["drivers"], list)
    assert len(data["drivers"]) == 0


@pytest.mark.asyncio
async def test_list_drivers_with_data(client: AsyncClient, sample_depot, sample_driver):
    """Test listing drivers with data."""
    # Create depot and driver
    depot = await sample_depot()
    driver = await sample_driver(depot_id=depot.id)
    
    response = await client.get("/api/v1/drivers")
    assert response.status_code == 200
    data = response.json()
    assert len(data["drivers"]) == 1
    assert data["drivers"][0]["id"] == str(driver.id)
    assert data["drivers"][0]["name"] == driver.full_name


@pytest.mark.asyncio
async def test_get_driver_by_id(client: AsyncClient, sample_depot, sample_driver):
    """Test getting a specific driver by ID."""
    depot = await sample_depot()
    driver = await sample_driver(depot_id=depot.id)
    
    response = await client.get(f"/api/v1/drivers/{driver.id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(driver.id)
    assert data["name"] == driver.full_name
    assert data["email"] == driver.email


@pytest.mark.asyncio
async def test_get_driver_not_found(client: AsyncClient):
    """Test getting non-existent driver returns 404."""
    fake_id = "00000000-0000-0000-0000-000000000000"
    response = await client.get(f"/api/v1/drivers/{fake_id}")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_filter_drivers_by_status(client: AsyncClient, sample_depot, sample_driver):
    """Test filtering drivers by status."""
    depot = await sample_depot()
    
    # Create drivers with different statuses
    await sample_driver(depot_id=depot.id)  # available
    
    response = await client.get("/api/v1/drivers?status=available")
    assert response.status_code == 200
    data = response.json()
    assert len(data["drivers"]) >= 1
    assert all(d["status"] == "available" for d in data["drivers"])


@pytest.mark.asyncio
async def test_update_driver_location(client: AsyncClient, sample_depot, sample_driver, sample_vehicle):
    """Test updating driver GPS location."""
    depot = await sample_depot()
    driver = await sample_driver(depot_id=depot.id)
    await sample_vehicle(driver_id=driver.id, depot_id=depot.id)
    
    location_data = {
        "latitude": 40.7580,
        "longitude": -73.9855,
        "speed_kmh": 45.5,
        "heading": 180.0
    }
    
    response = await client.post(
        f"/api/v1/drivers/{driver.id}/location",
        json=location_data
    )
    assert response.status_code == 200
    data = response.json()
    assert data["driver_id"] == str(driver.id)
    assert data["location"]["latitude"] == 40.7580


@pytest.mark.integration
@pytest.mark.asyncio
async def test_driver_workflow(client: AsyncClient, sample_depot, sample_driver, sample_vehicle):
    """Integration test: Create driver, update status, get driver."""
    depot = await sample_depot()
    driver = await sample_driver(depot_id=depot.id)
    await sample_vehicle(driver_id=driver.id, depot_id=depot.id)
    
    # Get driver
    response = await client.get(f"/api/v1/drivers/{driver.id}")
    assert response.status_code == 200
    
    # Update location
    response = await client.post(
        f"/api/v1/drivers/{driver.id}/location",
        json={"latitude": 40.7590, "longitude": -73.9800}
    )
    assert response.status_code == 200
    
    # Verify driver still exists
    response = await client.get(f"/api/v1/drivers/{driver.id}")
    assert response.status_code == 200

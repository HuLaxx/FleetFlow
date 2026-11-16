"""GPS coordinates must remain private across REST as well as WebSocket."""

from decimal import Decimal

import pytest

from src.models.user import UserRole
from tests.test_api.test_tracking_socket import make_user


@pytest.mark.asyncio
async def test_rest_vehicle_location_enforces_same_scopes_as_websocket(
    client, db_session, sample_depot, sample_driver, sample_vehicle
):
    depot = await sample_depot()
    other_depot = await sample_depot()
    driver = await sample_driver(depot_id=depot.id)
    vehicle = await sample_vehicle(driver_id=driver.id, depot_id=depot.id)
    vehicle.latitude = Decimal("55.8700")
    vehicle.longitude = Decimal("-4.2600")
    await db_session.flush()

    path = f"/api/v1/vehicles/{vehicle.id}/location"
    assert (await client.get(path)).status_code == 401

    roles = (
        (UserRole.VIEWER, None, None, 403),
        (UserRole.DRIVER, None, None, 403),
        (UserRole.DRIVER, driver.id, None, 200),
        (UserRole.DISPATCHER, None, None, 403),
        (UserRole.DISPATCHER, None, other_depot.id, 403),
        (UserRole.DISPATCHER, None, depot.id, 200),
        (UserRole.ADMIN, None, None, 200),
    )
    for role, driver_id, depot_id, status in roles:
        _, token = await make_user(
            db_session, role, driver_id=driver_id, depot_id=depot_id
        )
        response = await client.get(
            path, headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == status, response.text
        if status == 200:
            assert response.json()["location"] == {
                "latitude": 55.87, "longitude": -4.26
            }


@pytest.mark.asyncio
async def test_public_list_and_detail_redact_gps_coordinates(
    client, db_session, sample_depot, sample_driver, sample_vehicle
):
    depot = await sample_depot()
    driver = await sample_driver(depot_id=depot.id)
    vehicle = await sample_vehicle(driver_id=driver.id, depot_id=depot.id)
    vehicle.latitude = Decimal("55.8700")
    vehicle.longitude = Decimal("-4.2600")
    await db_session.flush()

    list_vehicles = await client.get("/api/v1/vehicles")
    assert list_vehicles.status_code == 200
    match = next(v for v in list_vehicles.json()["vehicles"] if v["id"] == str(vehicle.id))
    assert match["current_location"] is None

    vehicle_detail = await client.get(f"/api/v1/vehicles/{vehicle.id}")
    assert vehicle_detail.status_code == 200
    assert "current_location" not in vehicle_detail.json()

    listed_drivers = await client.get("/api/v1/drivers")
    assert listed_drivers.status_code == 200
    found = next(d for d in listed_drivers.json()["drivers"] if d["id"] == str(driver.id))
    assert found["current_location"] is None

    driver_detail = await client.get(f"/api/v1/drivers/{driver.id}")
    assert driver_detail.status_code == 200
    assert "current_location" not in driver_detail.json()

    _, token = await make_user(db_session, UserRole.DRIVER, driver_id=driver.id)
    headers = {"Authorization": f"Bearer {token}"}
    allowed = await client.get(f"/api/v1/vehicles/{vehicle.id}", headers=headers)
    assert allowed.json()["current_location"]["latitude"] == 55.87
    allowed_driver = await client.get(f"/api/v1/drivers/{driver.id}", headers=headers)
    assert allowed_driver.json()["current_location"]["latitude"] == 55.87

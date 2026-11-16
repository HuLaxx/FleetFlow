"""Seed only an explicitly isolated local fleetflow_test PostGIS DB.

CI fixture data, not production telemetry. Prints fixture IDs as JSON.
Never logs credentials or JWTs.
"""

import asyncio
import json
import os
from decimal import Decimal
from uuid import uuid4

from geoalchemy2.elements import WKTElement

from src.auth.jwt import get_password_hash
from src.database import AsyncSessionLocal, engine
from src.models import Depot, Driver, Vehicle
from src.models.user import User, UserRole


async def seed():
    if engine.url.database != "fleetflow_test" or engine.url.host not in (
        "localhost", "127.0.0.1"
    ):
        raise RuntimeError("Refusing to seed non-local or non-test database")

    email = os.environ["GPS_E2E_EMAIL"]
    password = os.environ["GPS_E2E_PASSWORD"]
    if len(password) < 18:
        raise RuntimeError("CI tracking password is too short")
    suffix = uuid4().hex[:10]
    async with AsyncSessionLocal() as session:
        depot = Depot(
            name=f"Acceptance depot {suffix}",
            address="Synthetic logistics facility",
            latitude=Decimal("55.8642"),
            longitude=Decimal("-4.2518"),
            location=WKTElement("POINT(-4.2518 55.8642)", srid=4326),
            is_active=True,
        )
        session.add(depot)
        await session.flush()
        driver = Driver(
            employee_id=f"E2E-{suffix}",
            first_name="Acceptance",
            last_name="Driver",
            email=f"driver-{suffix}@example.test",
            status="available",
            preferred_depot_id=depot.id,
        )
        session.add(driver)
        await session.flush()
        vehicle = Vehicle(
            vehicle_number=f"E2E-{suffix}",
            type="van",
            capacity_kg=Decimal("100"),
            depot_id=depot.id,
            current_driver_id=driver.id,
            status="available",
        )
        session.add(vehicle)
        session.add(
            User(
                email=email,
                hashed_password=get_password_hash(password),
                full_name="CI Synthetic Driver",
                role=UserRole.DRIVER,
                driver_id=driver.id,
                is_active=True,
                is_verified=True,
            )
        )
        await session.commit()

    print(json.dumps({"driver_id": str(driver.id), "vehicle_id": str(vehicle.id)}))


if __name__ == "__main__":
    asyncio.run(seed())

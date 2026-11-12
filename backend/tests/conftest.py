"""
Test configuration and fixtures.
Simplified to avoid import issues with optional dependencies.
"""

import pytest
import asyncio
from typing import AsyncGenerator, Generator
from faker import Faker

# Create faker instance
fake = Faker()


@pytest.fixture(scope="session")
def event_loop() -> Generator:
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def sample_depot_data():
    """Sample depot data for testing."""
    return {
        "name": "Test Depot",
        "address": "123 Test St",
        "city": "Test City",
        "state": "TS",
        "latitude": 40.7128,
        "longitude": -74.0060,
    }


@pytest.fixture
def sample_driver_data():
    """Sample driver data for testing."""
    return {
        "employee_id": fake.unique.random_number(digits=6),
        "name": fake.name(),
        "email": fake.email(),
        "phone": fake.phone_number(),
        "license_number": fake.bothify(text='??######'),
        "status": "available",
    }


@pytest.fixture
def sample_vehicle_data():
    """Sample vehicle data for testing."""
    return {
        "vehicle_number": fake.bothify(text='VAN-###'),
        "vehicle_type": "van",
        "capacity_kg": 1000.0,
        "status": "available",
        "latitude": 40.7128,
        "longitude": -74.0060,
    }


@pytest.fixture
def sample_order_data():
    """Sample order data for testing."""
    from datetime import datetime, timedelta
    now = datetime.utcnow()
    
    return {
        "order_number": fake.bothify(text='ORD-#####'),
        "customer_name": fake.company(),
        "customer_phone": fake.phone_number(),
        "delivery_address": fake.address(),
        "delivery_latitude": 40.7128 + fake.pyfloat(min_value=-0.1, max_value=0.1),
        "delivery_longitude": -74.0060 + fake.pyfloat(min_value=-0.1, max_value=0.1),
        "delivery_date": now.date().isoformat(),
        "time_window_start": (now + timedelta(hours=2)).isoformat(),
        "time_window_end": (now + timedelta(hours=4)).isoformat(),
        "total_weight_kg": fake.pyfloat(min_value=1.0, max_value=50.0),
        "priority": fake.random_int(min=1, max=5),
        "status": "pending",
    }

# Real API integration fixtures, isolated from production and external Kafka.
# PostGIS lives in the GitHub Actions test service configured in backend-tests.yml.
import os
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock

import pytest_asyncio
from geoalchemy2.elements import WKTElement
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from src.database import Base, get_db
from src.models import Customer, Depot, Driver, Order, Vehicle


@pytest_asyncio.fixture(scope="session")
async def integration_engine():
    url = os.environ.get("DATABASE_URL")
    if not url:
        pytest.skip("Real API database tests require DATABASE_URL for isolated PostGIS test DB")
    parsed = make_url(url)
    if parsed.database != "fleetflow_test" or parsed.host not in {"localhost", "127.0.0.1"}:
        raise RuntimeError("Refusing to create test schema outside local fleetflow_test database")

    engine = create_async_engine(url, pool_pre_ping=True)
    async with engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS postgis"))
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()  # No database deletion; only test transactions are rolled back.


@pytest_asyncio.fixture
async def db_session(integration_engine):
    # Savepoint semantics keep endpoint db.commit() real without persisting across tests.
    async with integration_engine.connect() as conn:
        outer = await conn.begin()
        session = AsyncSession(bind=conn, expire_on_commit=False, join_transaction_mode="create_savepoint")
        try:
            yield session
        finally:
            await session.close()
            await outer.rollback()


@pytest_asyncio.fixture
async def client(db_session, monkeypatch):
    from src.main import app
    from src.api.routes import orders, drivers, routes

    async def override_get_db():
        yield db_session

    mock_kafka = MagicMock()
    mock_kafka.publish_async = AsyncMock()
    for module in (orders, drivers, routes):
        monkeypatch.setattr(module, "get_kafka_producer", lambda: mock_kafka)
    app.dependency_overrides[get_db] = override_get_db
    try:
        # ASGITransport does not execute startup (which needs a live Kafka broker).
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as http:
            yield http
    finally:
        app.dependency_overrides.pop(get_db, None)


@pytest.fixture
def sample_depot(db_session):
    async def create():
        depot = Depot(
            name="Glasgow Test Depot",
            address="123 Example Street",
            latitude=Decimal("55.8642"),
            longitude=Decimal("-4.2518"),
            location=WKTElement("POINT(-4.2518 55.8642)", srid=4326),
            is_active=True,
        )
        db_session.add(depot)
        await db_session.flush()
        return depot
    return create


@pytest.fixture
def sample_driver(db_session):
    async def create(depot_id=None, status="available"):
        suffix = uuid4().hex[:8]
        driver = Driver(
            employee_id=f"TEST-{suffix}",
            first_name="Test",
            last_name="Driver",
            email=f"driver-{suffix}@example.test",
            phone="00000000000",
            status=status,
            preferred_depot_id=depot_id,
            rating=Decimal("5.00"),
            total_deliveries=0,
            max_working_hours_per_day=Decimal("8.00"),
        )
        db_session.add(driver)
        await db_session.flush()
        return driver
    return create


@pytest.fixture
def sample_vehicle(db_session):
    async def create(driver_id=None, depot_id=None):
        vehicle = Vehicle(
            vehicle_number=f"TEST-{uuid4().hex[:8]}",
            type="van",
            capacity_kg=Decimal("750"),
            current_driver_id=driver_id,
            depot_id=depot_id,
            status="available",
        )
        db_session.add(vehicle)
        await db_session.flush()
        return vehicle
    return create


@pytest.fixture
def sample_order(db_session):
    async def create(depot_id=None, status="pending"):
        customer = Customer(
            name="Test Recipient",
            address="42 Example Street, Glasgow",
            latitude=Decimal("55.8642"),
            longitude=Decimal("-4.2518"),
            location=WKTElement("POINT(-4.2518 55.8642)", srid=4326),
        )
        db_session.add(customer)
        await db_session.flush()
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        order = Order(
            order_number=f"TEST-{uuid4().hex[:10]}",
            customer_id=customer.id,
            depot_id=depot_id,
            items=[],
            total_weight_kg=Decimal("4.50"),
            delivery_date=now.date(),
            time_window_start=now + timedelta(hours=2),
            time_window_end=now + timedelta(hours=4),
            status=status,
            priority=2,
        )
        db_session.add(order)
        await db_session.flush()
        return order
    return create

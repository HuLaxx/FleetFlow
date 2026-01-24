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

"""
Database seeding script for development/testing.

Populates the database with realistic seed data:
- 3 depots (NYC area)
- 10 drivers
- 8 vehicles
- 30 customers
- 25 orders
- 5 routes with stops

Usage:
    python scripts/seed_database.py
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime, date, time, timedelta
from decimal import Decimal
from random import randint, choice, uniform

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy import text

from src.config import get_settings
from src.database import Base
from src.models import Depot, Driver, Vehicle, Customer, Order, Route, RouteStop

settings = get_settings()


# Seed Data
DEPOTS_DATA = [
    {
        "name": "NYC Main Hub",
        "address": "123 Warehouse Ave, Brooklyn, NY 11201",
        "latitude": Decimal("40.6892"),
        "longitude": Decimal("-73.9857"),
        "capacity_vehicles": 100,
    },
    {
        "name": "Manhattan Distribution",
        "address": "456 Distribution Blvd, New York, NY 10001",
        "latitude": Decimal("40.7505"),
        "longitude": Decimal("-73.9934"),
        "capacity_vehicles": 50,
    },
    {
        "name": "Jersey City Depot",
        "address": "789 Logistics Way, Jersey City, NJ 07302",
        "latitude": Decimal("40.7178"),
        "longitude": Decimal("-74.0431"),
        "capacity_vehicles": 75,
    },
]

DRIVER_NAMES = [
    ("Marcus", "Johnson"),
    ("Sarah", "Chen"),
    ("James", "Wilson"),
    ("Emily", "Rodriguez"),
    ("David", "Kim"),
    ("Anna", "Martinez"),
    ("Michael", "Thompson"),
    ("Lisa", "Park"),
    ("Robert", "Garcia"),
    ("Jennifer", "Lee"),
]

VEHICLE_TYPES = ["van", "truck", "car"]
VEHICLE_MAKES = ["Ford", "Mercedes", "Toyota", "Ram", "Nissan"]

CUSTOMER_NAMES = [
    "John Smith", "Emma Brown", "William Davis", "Olivia Miller",
    "Ava Wilson", "James Moore", "Isabella Taylor", "Benjamin Anderson",
    "Mia Thomas", "Lucas Jackson", "Charlotte White", "Henry Harris",
    "Amelia Martin", "Alexander Thompson", "Harper Garcia", "Daniel Martinez",
    "Evelyn Robinson", "Matthew Clark", "Abigail Rodriguez", "Joseph Lewis",
    "Emily Lee", "David Walker", "Elizabeth Hall", "Christopher Allen",
    "Sofia Young", "Andrew Hernandez", "Victoria King", "Joshua Wright",
    "Madison Lopez", "Ryan Hill",
]


async def seed_database():
    """Seed the database with test data."""
    print("🌱 Starting database seeding...")
    
    # Create engine
    engine = create_async_engine(settings.database_url, echo=True)
    AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)
    
    async with AsyncSessionLocal() as session:
        # Clear existing data
        print("\n🗑️  Clearing existing data...")
        await session.execute(text("TRUNCATE TABLE route_stops, routes, orders, customers, vehicles, drivers, depots CASCADE"))
        await session.commit()
        
        # Create Depots
        print("\n🏭 Creating depots...")
        depots = []
        for depot_data in DEPOTS_DATA:
            # Create PostGIS point from lat/lon
            depot = Depot(**depot_data)
            session.add(depot)
            depots.append(depot)
        
        await session.flush()  # Get IDs
        print(f"   ✓ Created {len(depots)} depots")
        
        # Create Drivers
        print("\n👷 Creating drivers...")
        drivers = []
        for i, (first_name, last_name) in enumerate(DRIVER_NAMES):
            driver = Driver(
                employee_id=f"DRV-{1000 + i}",
                first_name=first_name,
                last_name=last_name,
                email=f"{first_name.lower()}.{last_name.lower()}@fleetflow.com",
                phone=f"+1-555-{1000 + i}",
                license_number=f"DL-{randint(10000000, 99999999)}",
                license_expiry=date.today() + timedelta(days=randint(365, 730)),
                preferred_depot_id=choice(depots).id,
                status=choice(["available", "on_route", "on_break"]) if i < 8 else "offline",
                rating=Decimal(str(round(uniform(4.5, 5.0), 2))),
                total_deliveries=randint(100, 500),
            )
            session.add(driver)
            drivers.append(driver)
        
        await session.flush()
        print(f"   ✓ Created {len(drivers)} drivers")
        
        # Create Vehicles
        print("\n🚚 Creating vehicles...")
        vehicles = []
        for i in range(8):
            vehicle_type = choice(VEHICLE_TYPES)
            capacity = {
                "van": Decimal("500.00"),
                "truck": Decimal("2000.00"),
                "car": Decimal("200.00"),
            }[vehicle_type]
            
            # Assign to depot and potentially a driver
            depot = choice(depots)
            driver = drivers[i] if i < len(drivers) else None
            
            # Random location near depot
            lat_offset = Decimal(str(uniform(-0.05, 0.05)))
            lon_offset = Decimal(str(uniform(-0.05, 0.05)))
            
            vehicle = Vehicle(
                vehicle_number=f"VEH-{100 + i}",
                type=vehicle_type,
                make=choice(VEHICLE_MAKES),
                model=f"Model {randint(1, 9)}",
                year=randint(2018, 2024),
                capacity_kg=capacity,
                capacity_cubic_m=Decimal(str(round(uniform(10, 30), 2))),
                fuel_type=choice(["diesel", "petrol", "electric"]),
                fuel_efficiency_km_per_l=Decimal(str(round(uniform(8, 15), 2))),
                depot_id=depot.id,
                current_driver_id=driver.id if driver else None,
                latitude=depot.latitude + lat_offset,
                longitude=depot.longitude + lon_offset,
                status="in_use" if driver and driver.status == "on_route" else "available",
            )
            session.add(vehicle)
            vehicles.append(vehicle)
        
        await session.flush()
        print(f"   ✓ Created {len(vehicles)} vehicles")
        
        # Create Customers
        print("\n👥 Creating customers...")
        customers = []
        for i, name in enumerate(CUSTOMER_NAMES):
            # Random location in NYC area
            base_depot = choice(depots)
            lat_offset = Decimal(str(uniform(-0.03, 0.03)))
            lon_offset = Decimal(str(uniform(-0.03, 0.03)))
            
            customer = Customer(
                external_id=f"CUST-{randint(100000, 999999)}",
                name=name,
                email=f"{name.replace(' ', '.').lower()}@example.com",
                phone=f"+1-555-{2000 + i}",
                address=f"{randint(100, 999)} Main St, New York, NY {randint(10000, 10999)}",
                latitude=base_depot.latitude + lat_offset,
                longitude=base_depot.longitude + lon_offset,
                priority=randint(1, 3),
            )
            session.add(customer)
            customers.append(customer)
        
        await session.flush()
        print(f"   ✓ Created {len(customers)} customers")
        
        # Create Orders
        print("\n📦 Creating orders...")
        orders = []
        today = date.today()
        
        for i in range(25):
            customer = choice(customers)
            depot = choice(depots)
            
            delivery_date = today + timedelta(days=randint(0, 2))
            time_start = datetime.combine(delivery_date, time(9, 0)) + timedelta(hours=randint(0, 6))
            time_end = time_start + timedelta(hours=randint(1, 3))
            
            order = Order(
                order_number=f"ORD-{10000 + i}",
                customer_id=customer.id,
                depot_id=depot.id,
                items=[
                    {"sku": f"ITEM-{randint(1000, 9999)}", "quantity": randint(1, 5), "name": f"Product {i}"}
                ],
                total_weight_kg=Decimal(str(round(uniform(5, 50), 2))),
                total_value=Decimal(str(round(uniform(100, 1000), 2))),
                delivery_date=delivery_date,
                time_window_start=time_start,
                time_window_end=time_end,
                status=choice(["pending", "pending", "pending", "assigned", "in_transit"]),
                priority=randint(1, 3),
                source="api",
            )
            session.add(order)
            orders.append(order)
        
        await session.flush()
        print(f"   ✓ Created {len(orders)} orders")
        
        # Create Routes
        print("\n🗺️  Creating routes...")
        active_drivers = [d for d in drivers if d.status in ["on_route", "available"]][:5]
        
        for i, driver in enumerate(active_drivers):
            # Get driver's vehicle
            vehicle = next((v for v in vehicles if v.current_driver_id == driver.id), None)
            if not vehicle:
                continue
            
            route =Route(
                route_date=today,
                driver_id=driver.id,
                vehicle_id=vehicle.id,
                depot_id=driver.preferred_depot_id,
                planned_distance_km=Decimal(str(round(uniform(30, 80), 2))),
                planned_duration_minutes=randint(180, 360),
                planned_stops=randint(3, 6),
                status="in_progress" if driver.status == "on_route" else "planned",
                algorithm_used="OR-Tools",
                optimization_score=Decimal(str(round(uniform(0.85, 0.95), 4))),
                computation_time_ms=randint(500, 2000),
                started_at=datetime.now() - timedelta(hours=randint(1, 3)) if driver.status == "on_route" else None,
            )
            session.add(route)
            # Simple: will add stops in next commit
        
        await session.commit()
        print(f"   ✓ Created routes")
        
    await engine.dispose()
    print("\n✅ Database seeding complete!\n")


if __name__ == "__main__":
    asyncio.run(seed_database())

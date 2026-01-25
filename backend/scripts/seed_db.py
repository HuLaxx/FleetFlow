"""Deterministic database seeding for local FleetFlow."""

from __future__ import annotations

import argparse
import asyncio
from datetime import date, datetime, timedelta, time
from decimal import Decimal
from pathlib import Path
import random
import sys
from typing import Iterable

from geoalchemy2 import WKTElement
from sqlalchemy import text

BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from src.database import AsyncSessionLocal  # noqa: E402
from src.models import (  # noqa: E402
    Depot,
    Driver,
    Vehicle,
    Customer,
    Order,
    Route,
    RouteStop,
)


def _point(lat: float, lon: float) -> WKTElement:
    return WKTElement(f"POINT({lon} {lat})", srid=4326)


def _rand_point(rng: random.Random, base_lat: float, base_lon: float, delta: float) -> tuple[float, float]:
    return (
        base_lat + rng.uniform(-delta, delta),
        base_lon + rng.uniform(-delta, delta),
    )


def _decimal(value: float, precision: int = 2) -> Decimal:
    fmt = f"{{:.{precision}f}}"
    return Decimal(fmt.format(value))


async def reset_db() -> None:
    async with AsyncSessionLocal() as session:
        await session.execute(
            text(
                "TRUNCATE TABLE route_stops, routes, orders, vehicles, drivers, customers, depots CASCADE"
            )
        )
        await session.commit()


async def seed_db(
    seed: int,
    drivers_count: int,
    customers_count: int,
    orders_count: int,
    routes_count: int,
) -> None:
    rng = random.Random(seed)
    base_lat, base_lon = 40.7128, -74.0060

    async with AsyncSessionLocal() as session:
        depot = Depot(
            name="FleetFlow Central Hub",
            address="100 Main St, New York, NY",
            latitude=_decimal(base_lat, 7),
            longitude=_decimal(base_lon, 7),
            location=_point(base_lat, base_lon),
            capacity_vehicles=drivers_count,
            operating_hours_start=time(6, 0),
            operating_hours_end=time(22, 0),
            is_active=True,
        )
        session.add(depot)
        await session.flush()

        drivers = []
        for i in range(drivers_count):
            lat, lon = _rand_point(rng, base_lat, base_lon, 0.08)
            driver = Driver(
                employee_id=f"DRV-{i:03d}",
                first_name=f"Driver{i+1}",
                last_name="Fleet",
                email=f"driver{i+1}@fleetflow.local",
                phone=f"+1-555-010{i:02d}",
                preferred_depot_id=depot.id,
                home_location=_point(lat, lon),
                status="available",
                rating=_decimal(4.7 + (i % 3) * 0.1, 2),
            )
            drivers.append(driver)
        session.add_all(drivers)
        await session.flush()

        vehicles = []
        vehicle_types = ["van", "truck", "bike", "car"]
        for i, driver in enumerate(drivers):
            lat, lon = _rand_point(rng, base_lat, base_lon, 0.06)
            vehicle = Vehicle(
                vehicle_number=f"VH-{i:03d}",
                type=vehicle_types[i % len(vehicle_types)],
                make="FleetFlow",
                model=f"Series-{(i % 4) + 1}",
                year=2022 + (i % 3),
                capacity_kg=_decimal(450 + (i % 4) * 75, 2),
                fuel_type="electric" if i % 3 == 0 else "diesel",
                fuel_efficiency_km_per_l=_decimal(12 + (i % 3) * 1.5, 2),
                depot_id=depot.id,
                current_driver_id=driver.id,
                latitude=_decimal(lat, 7),
                longitude=_decimal(lon, 7),
                current_location=_point(lat, lon),
                status="available",
            )
            vehicles.append(vehicle)
        session.add_all(vehicles)
        await session.flush()

        customers = []
        for i in range(customers_count):
            lat, lon = _rand_point(rng, base_lat, base_lon, 0.12)
            customer = Customer(
                external_id=f"CUST-{i:04d}",
                name=f"Customer {i+1}",
                email=f"customer{i+1}@example.com",
                phone=f"+1-555-020{i:02d}",
                address=f"{200 + i} Market St, New York, NY",
                latitude=_decimal(lat, 7),
                longitude=_decimal(lon, 7),
                location=_point(lat, lon),
                delivery_instructions="Leave at front desk",
                priority=1 + (i % 3),
            )
            customers.append(customer)
        session.add_all(customers)
        await session.flush()

        orders = []
        today = date.today()
        base_time = datetime.now().replace(minute=0, second=0, microsecond=0)
        for i in range(orders_count):
            customer = customers[i % len(customers)]
            start_time = base_time + timedelta(hours=2 + (i % 5))
            end_time = start_time + timedelta(hours=2)
            order = Order(
                order_number=f"ORD-{today.strftime('%Y%m%d')}-{i:04d}",
                customer_id=customer.id,
                depot_id=depot.id,
                items=[
                    {
                        "sku": f"SKU-{i:04d}",
                        "name": "FleetFlow Package",
                        "quantity": 1 + (i % 3),
                        "weight_kg": round(2.5 + (i % 5) * 1.2, 2),
                    }
                ],
                total_weight_kg=_decimal(5 + (i % 6) * 2.5, 2),
                total_value=_decimal(50 + (i % 8) * 15, 2),
                delivery_date=today,
                time_window_start=start_time,
                time_window_end=end_time,
                service_time_minutes=5,
                status="pending",
                priority=1 + (i % 4),
                source="seed",
            )
            orders.append(order)
        session.add_all(orders)
        await session.flush()

        routes = []
        max_routes = min(routes_count, max(0, len(orders) // 5))
        route_orders = orders[: max_routes * 5]
        for i in range(max_routes):
            driver = drivers[i % len(drivers)]
            vehicle = vehicles[i % len(vehicles)]
            route = Route(
                route_date=today,
                driver_id=driver.id,
                vehicle_id=vehicle.id,
                depot_id=depot.id,
                planned_distance_km=_decimal(35 + i * 4.2, 2),
                planned_duration_minutes=120 + i * 15,
                planned_stops=5,
                algorithm_used="ortools",
                optimization_score=_decimal(0.85 + (i * 0.02), 4),
                computation_time_ms=1200 + i * 150,
                status="in_progress" if i == 0 else "planned",
            )
            routes.append(route)
        session.add_all(routes)
        await session.flush()

        stops = []
        for i, route in enumerate(routes):
            for j in range(5):
                order = route_orders[i * 5 + j]
                customer = customers[(i * 5 + j) % len(customers)]
                lat = float(customer.latitude)
                lon = float(customer.longitude)
                stop = RouteStop(
                    route_id=route.id,
                    order_id=order.id,
                    stop_sequence=j + 1,
                    latitude=_decimal(lat, 7),
                    longitude=_decimal(lon, 7),
                    location=_point(lat, lon),
                    address=customer.address,
                    planned_arrival=base_time + timedelta(hours=j + 1),
                    planned_departure=base_time + timedelta(hours=j + 1, minutes=10),
                    status="completed" if i == 0 and j == 0 else "pending",
                )
                stops.append(stop)
                order.status = "assigned" if i == 0 else order.status
        session.add_all(stops)

        await session.commit()

        print(
            f"Seeded depot=1, drivers={len(drivers)}, vehicles={len(vehicles)}, "
            f"customers={len(customers)}, orders={len(orders)}, routes={len(routes)}, stops={len(stops)}"
        )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Seed FleetFlow database with deterministic data")
    parser.add_argument("--reset", action="store_true", help="Truncate tables before seeding")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    parser.add_argument("--drivers", type=int, default=10, help="Number of drivers")
    parser.add_argument("--customers", type=int, default=40, help="Number of customers")
    parser.add_argument("--orders", type=int, default=80, help="Number of orders")
    parser.add_argument("--routes", type=int, default=3, help="Number of routes")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.reset:
        asyncio.run(reset_db())
    asyncio.run(
        seed_db(
            seed=args.seed,
            drivers_count=args.drivers,
            customers_count=args.customers,
            orders_count=args.orders,
            routes_count=args.routes,
        )
    )


if __name__ == "__main__":
    main()

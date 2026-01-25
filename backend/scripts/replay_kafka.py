"""Deterministic Kafka replay for FleetFlow local demo."""

from __future__ import annotations

import argparse
import asyncio
from datetime import datetime, timedelta
from pathlib import Path
import random
import sys

from sqlalchemy import select

BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from src.database import AsyncSessionLocal  # noqa: E402
from src.models import Customer, Depot, Driver, Order, Route, RouteStop, Vehicle  # noqa: E402
from src.events.producer import get_kafka_producer  # noqa: E402


def _address_payload(customer: Customer) -> dict:
    return {
        "street": customer.address,
        "city": "New York",
        "state": "NY",
        "postal_code": "10001",
        "country": "US",
        "location": {
            "latitude": float(customer.latitude),
            "longitude": float(customer.longitude),
        },
    }


def _time_window(order: Order) -> dict:
    return {
        "start": order.time_window_start.isoformat(),
        "end": order.time_window_end.isoformat(),
    }


async def _load_data():
    async with AsyncSessionLocal() as session:
        customers = (await session.execute(select(Customer))).scalars().all()
        depots = (await session.execute(select(Depot))).scalars().all()
        drivers = (await session.execute(select(Driver))).scalars().all()
        vehicles = (await session.execute(select(Vehicle))).scalars().all()
        orders = (await session.execute(select(Order))).scalars().all()
        routes = (await session.execute(select(Route))).scalars().all()
        stops = (await session.execute(select(RouteStop))).scalars().all()
    return customers, depots, drivers, vehicles, orders, routes, stops


def _publish_orders(producer, orders, customers, depots, max_orders: int) -> int:
    count = 0
    customer_map = {c.id: c for c in customers}
    depot_map = {d.id: d for d in depots}

    for order in orders[:max_orders]:
        customer = customer_map.get(order.customer_id)
        if not customer:
            continue
        depot_id = order.depot_id or (depots[0].id if depots else None)
        event = {
            "order_id": order.id,
            "order_number": order.order_number,
            "customer_id": order.customer_id,
            "depot_id": depot_id,
            "delivery_address": _address_payload(customer),
            "delivery_date": order.delivery_date.isoformat(),
            "time_window": _time_window(order),
            "items": order.items,
            "total_weight_kg": float(order.total_weight_kg),
            "total_value": float(order.total_value) if order.total_value else None,
            "priority": order.priority,
            "source": order.source,
            "timestamp": datetime.utcnow().isoformat(),
        }
        producer.publish("orders.created", event, key=str(order.id))
        count += 1
    return count


def _publish_driver_status(producer, drivers, max_drivers: int) -> int:
    count = 0
    for driver in drivers[:max_drivers]:
        event = {
            "driver_id": driver.id,
            "previous_status": "available",
            "new_status": driver.status,
            "reason": "local replay",
            "timestamp": datetime.utcnow().isoformat(),
        }
        producer.publish("drivers.status", event, key=str(driver.id))
        count += 1
    return count


def _publish_gps(producer, drivers, vehicles, depots, rng: random.Random, max_events: int) -> int:
    count = 0
    depot = depots[0] if depots else None
    for i, vehicle in enumerate(vehicles):
        if count >= max_events:
            break
        lat = float(vehicle.latitude) if vehicle.latitude else float(depot.latitude)
        lon = float(vehicle.longitude) if vehicle.longitude else float(depot.longitude)
        jitter_lat = lat + rng.uniform(-0.002, 0.002)
        jitter_lon = lon + rng.uniform(-0.002, 0.002)
        driver_id = vehicle.current_driver_id or (drivers[i % len(drivers)].id if drivers else None)
        if not driver_id:
            continue
        event = {
            "driver_id": driver_id,
            "vehicle_id": vehicle.id,
            "location": {"latitude": jitter_lat, "longitude": jitter_lon},
            "speed_kmh": round(25 + rng.random() * 10, 2),
            "heading": round(rng.random() * 360, 1),
            "accuracy_m": 5.0,
            "battery_level": 80,
            "is_moving": True,
            "timestamp": datetime.utcnow().isoformat(),
        }
        producer.publish("gps.location", event, key=str(vehicle.id))
        count += 1
    return count


def _publish_routes(producer, routes, stops, max_routes: int) -> tuple[int, int]:
    started_count = 0
    stop_count = 0
    stops_by_route = {}
    for stop in stops:
        stops_by_route.setdefault(stop.route_id, []).append(stop)

    for route in routes[:max_routes]:
        event = {
            "route_id": route.id,
            "driver_id": route.driver_id,
            "started_at": (route.started_at or datetime.utcnow()).isoformat(),
            "first_stop_eta": (datetime.utcnow() + timedelta(minutes=20)).isoformat(),
            "timestamp": datetime.utcnow().isoformat(),
        }
        producer.publish("routes.started", event, key=str(route.id))
        started_count += 1

        for stop in (stops_by_route.get(route.id, [])[:3]):
            stop_event = {
                "route_id": route.id,
                "stop_id": stop.id,
                "order_id": stop.order_id,
                "driver_id": route.driver_id,
                "completed_at": datetime.utcnow().isoformat(),
                "actual_service_time_minutes": 5,
                "next_stop_eta": (datetime.utcnow() + timedelta(minutes=15)).isoformat(),
                "timestamp": datetime.utcnow().isoformat(),
            }
            producer.publish("routes.stops", stop_event, key=str(stop.id))
            stop_count += 1
    return started_count, stop_count


async def replay(seed: int, max_orders: int, max_drivers: int, max_gps: int, max_routes: int, dry_run: bool) -> None:
    rng = random.Random(seed)
    customers, depots, drivers, vehicles, orders, routes, stops = await _load_data()

    if dry_run:
        print(
            f"Dry run: orders={len(orders)}, drivers={len(drivers)}, vehicles={len(vehicles)}, "
            f"routes={len(routes)}, stops={len(stops)}"
        )
        return

    producer = get_kafka_producer()
    await producer.ensure_topics_exist()

    orders_sent = _publish_orders(producer, orders, customers, depots, max_orders)
    drivers_sent = _publish_driver_status(producer, drivers, max_drivers)
    gps_sent = _publish_gps(producer, drivers, vehicles, depots, rng, max_gps)
    routes_sent, stops_sent = _publish_routes(producer, routes, stops, max_routes)

    producer.flush(10)
    producer.close()

    print(
        "Kafka replay complete: "
        f"orders={orders_sent}, drivers={drivers_sent}, gps={gps_sent}, "
        f"routes={routes_sent}, stops={stops_sent}"
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Replay Kafka events for local demo")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--max-orders", type=int, default=50)
    parser.add_argument("--max-drivers", type=int, default=10)
    parser.add_argument("--max-gps", type=int, default=20)
    parser.add_argument("--max-routes", type=int, default=3)
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    asyncio.run(
        replay(
            seed=args.seed,
            max_orders=args.max_orders,
            max_drivers=args.max_drivers,
            max_gps=args.max_gps,
            max_routes=args.max_routes,
            dry_run=args.dry_run,
        )
    )


if __name__ == "__main__":
    main()
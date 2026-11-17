"""Measured synthetic comparison of real OR-Tools CVRPTW and honest heuristics.

The same Haversine metre matrix, 30 km/h speed, service-time and UTC
time-window checks evaluate all solvers. This is NOT road-network, actual
delivery, ML accuracy or a claim of optimized production cost.
"""

import argparse
import json
import math
import time
from datetime import UTC, date, datetime, time as dt_time, timedelta
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
from uuid import NAMESPACE_DNS, UUID, uuid5

from src.optimization.route_optimizer import VehicleRoutingOptimizer

TEST_DATE = date(2030, 1, 15)
COST_PER_KM_GBP = 0.35  # synthetic sensitivity parameter, not real operations
COST_PER_HOUR_GBP = 12.0  # synthetic sensitivity parameter


def _id(case: str, category: str, index: int) -> UUID:
    return uuid5(NAMESPACE_DNS, f"fleetflow-synthetic-{case}-{category}-{index}")


def scenario(name: str):
    """Named, deterministic scenarios; no production customers or address data."""
    depot = SimpleNamespace(
        id=_id(name, "depot", 0),
        latitude=55.8642,
        longitude=-4.2518,
        operating_hours_start=dt_time(6, 0),
        operating_hours_end=dt_time(22, 0),
    )
    if name == "city_feasible":
        points = [
            (55.868, -4.242, 3, 9, 17),
            (55.859, -4.263, 4, 9, 17),
            (55.875, -4.254, 2, 9, 17),
            (55.856, -4.246, 3, 9, 17),
            (55.882, -4.277, 4, 9, 17),
            (55.866, -4.283, 2, 9, 17),
        ]
        capacities = [12, 12]
    elif name == "window_feasible":
        points = [
            (55.866, -4.258, 2, 9, 11),
            (55.874, -4.250, 2, 11, 13),
            (55.862, -4.248, 2, 13, 15),
            (55.858, -4.268, 2, 15, 17),
        ]
        capacities = [12]
    elif name == "capacity_infeasible":
        points = [(55.870, -4.245, 9, 9, 17), (55.862, -4.270, 9, 9, 17)]
        capacities = [10]
    else:
        raise ValueError(f"Unknown synthetic scenario: {name}")

    orders = [
        SimpleNamespace(
            id=_id(name, "order", index),
            total_weight_kg=Decimal(str(weight)),
            service_time_minutes=5,
            time_window_start=datetime.combine(TEST_DATE, dt_time(start_hour, 0)),
            time_window_end=datetime.combine(TEST_DATE, dt_time(end_hour, 0)),
            customer=SimpleNamespace(
                latitude=lat, longitude=lon, address="Synthetic, no real address"
            ),
        )
        for index, (lat, lon, weight, start_hour, end_hour) in enumerate(points)
    ]
    vehicles = [
        SimpleNamespace(
            id=_id(name, "vehicle", i),
            current_driver_id=_id(name, "driver", i),
            capacity_kg=Decimal(str(capacity)),
        )
        for i, capacity in enumerate(capacities)
    ]
    return depot, orders, vehicles


def _distance(a, b) -> int:
    return round(
        VehicleRoutingOptimizer._haversine(
            float(a.latitude), float(a.longitude), float(b.latitude), float(b.longitude)
        )
    )


def _seconds(ts: datetime) -> int:
    return (ts.hour * 60 + ts.minute) * 60 + ts.second


def _simulate(depot, orders, vehicles, assignments) -> dict:
    """Independent capacity/UTC-window check of route stop sequences."""
    order_lookup = {order.id: order for order in orders}
    vehicle_lookup = {vehicle.id: vehicle for vehicle in vehicles}
    served: set[UUID] = set()
    violations = 0
    distance_m = 0
    duration_min = 0
    start_sec = 6 * 3600
    close_sec = 22 * 3600

    for vehicle_id, stop_ids in assignments.items():
        if not stop_ids:
            continue
        vehicle = vehicle_lookup.get(vehicle_id)
        if vehicle is None:
            violations += 1
            continue
        weight_g = 0
        clock = start_sec
        last = depot
        service_before_next = 0
        for order_id in stop_ids:
            order = order_lookup.get(order_id)
            if order is None or order_id in served:
                violations += 1
                continue
            served.add(order_id)
            weight_g += math.ceil(float(order.total_weight_kg) * 1000)
            next_distance = _distance(last, order.customer)
            distance_m += next_distance
            clock += service_before_next + math.ceil(next_distance / (30_000 / 3600))
            clock = max(clock, _seconds(order.time_window_start))
            if clock > _seconds(order.time_window_end):
                violations += 1
            service_before_next = int(order.service_time_minutes) * 60
            last = order.customer
        last_leg = _distance(last, depot)
        distance_m += last_leg
        clock += service_before_next + math.ceil(last_leg / (30_000 / 3600))
        if clock > close_sec:
            violations += 1
        if weight_g > math.floor(float(vehicle.capacity_kg) * 1000):
            violations += 1
        duration_min += math.ceil((clock - start_sec) / 60)

    unassigned = len(order_lookup) - len(served)
    feasible = unassigned == 0 and violations == 0
    return {
        "orders": len(orders),
        "served": len(served),
        "unassigned": unassigned,
        "constraint_violations": violations,
        "total_distance_km": round(distance_m / 1000, 3),
        "total_duration_minutes": duration_min,
        "is_feasible": feasible,
        # Cost is deliberately NULL for partial/infeasible schedules.
        "illustrative_cost_gbp": (
            round(distance_m / 1000 * COST_PER_KM_GBP + duration_min / 60 * COST_PER_HOUR_GBP, 2)
            if feasible
            else None
        ),
    }


def _append_if_feasible(depot, orders, vehicles, plan, vehicle_id, order_id):
    candidate = {key: list(value) for key, value in plan.items()}
    candidate[vehicle_id].append(order_id)
    # The checker intentionally permits incomplete plans when constructing
    # partial feasible schedules, but no capacity/window violations.
    return _simulate(depot, orders, vehicles, candidate)["constraint_violations"] == 0


def _input_order(depot, orders, vehicles):
    plan = {v.id: [] for v in vehicles}
    for order in orders:
        for vehicle in vehicles:
            if _append_if_feasible(depot, orders, vehicles, plan, vehicle.id, order.id):
                plan[vehicle.id].append(order.id)
                break
    return plan


def _nearest_neighbour(depot, orders, vehicles):
    plan = {v.id: [] for v in vehicles}
    remaining = {o.id: o for o in orders}
    for vehicle in vehicles:
        while remaining:
            last = next(
                (o.customer for o in orders if plan[vehicle.id] and o.id == plan[vehicle.id][-1]),
                depot,
            )
            candidates = sorted(
                remaining.values(), key=lambda order: (_distance(last, order.customer), str(order.id))
            )
            selected = next(
                (
                    order for order in candidates
                    if _append_if_feasible(depot, orders, vehicles, plan, vehicle.id, order.id)
                ),
                None,
            )
            if selected is None:
                break
            plan[vehicle.id].append(selected.id)
            del remaining[selected.id]
    return plan


def benchmark_scenario(name: str, *, solver_seconds: int = 1) -> list[dict]:
    depot, orders, vehicles = scenario(name)
    optimizer = VehicleRoutingOptimizer(planning_time_limit_sec=solver_seconds)
    results = []
    for label, run in (
        ("input_order", lambda: _input_order(depot, orders, vehicles)),
        ("nearest_neighbour", lambda: _nearest_neighbour(depot, orders, vehicles)),
        ("ortools_cvrptw", lambda: {
            route["vehicle_id"]: [stop["order_id"] for stop in route["stops"]]
            for route in optimizer.optimize(orders, vehicles, depot, TEST_DATE)
        }),
    ):
        started = time.perf_counter()
        assignments = run()
        duration_ms = round((time.perf_counter() - started) * 1000, 3)
        metrics = _simulate(depot, orders, vehicles, assignments)
        results.append({
            "scenario": name,
            "method": label,
            "solve_time_ms": duration_ms,
            **metrics,
        })
    return results


def run_all(*, solver_seconds: int = 1) -> dict:
    result = [
        case
        for name in ("city_feasible", "window_feasible", "capacity_infeasible")
        for case in benchmark_scenario(name, solver_seconds=solver_seconds)
    ]
    return {
        "dataset": "fixed-synthetic-fleetflow-routing-v1",
        "test_date": TEST_DATE.isoformat(),
        "distance": "Haversine, round metres",
        "travel": "fixed 30 km/h, no traffic/OSRM",
        "cost": "illustrative 0.35 GBP/km + 12 GBP/hour, not actual expenditure",
        "measured_at_utc": datetime.now(UTC).isoformat(),
        "results": result,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Reproduce FleetFlow synthetic route baselines")
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--solver-seconds", type=int, default=1)
    args = parser.parse_args()
    if not 1 <= args.solver_seconds <= 30:
        parser.error("--solver-seconds must be 1..30")
    result = run_all(solver_seconds=args.solver_seconds)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "dataset": result["dataset"],
        "scenarios": 3,
        "methods": 3,
        "results_file": str(args.output),
        "full_feasible": sum(row["is_feasible"] for row in result["results"]),
    }, sort_keys=True))


if __name__ == "__main__":
    main()

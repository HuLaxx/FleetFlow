"""Offline comparative routing study on synthetic Glasgow-like coordinates.

Same orders, vehicles, depot and delivery windows for an OR-Tools CVRPTW
plan and deterministic capacity/window-aware nearest-neighbour baseline.
This is NOT road-network distance, actual delivery time or monetary savings.
"""

import argparse
import json
import math
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from pathlib import Path
from time import perf_counter
from types import SimpleNamespace
from uuid import NAMESPACE_URL, uuid5

from src.optimization.route_optimizer import VehicleRoutingOptimizer

SPEED_METRES_PER_SECOND = 30_000 / 3_600
ASSUMED_GBP_PER_KM = 0.35
ROUTE_DATE = date(2030, 1, 15)


@dataclass
class Scenario:
    name: str
    depot: SimpleNamespace
    vehicles: list[SimpleNamespace]
    orders: list[SimpleNamespace]


def _uid(label: str):
    return uuid5(NAMESPACE_URL, "fleetflow-routing-fixture:" + label)


def synthetic_cases() -> list[Scenario]:
    """Original fixed fixtures, intentionally not any real customers."""
    offsets = [
        (0.012, -0.022),
        (0.018, -0.008),
        (-0.014, 0.012),
        (0.002, 0.025),
        (-0.023, -0.014),
        (0.025, 0.019),
        (-0.010, -0.026),
        (-0.029, 0.008),
        (0.032, 0.004),
        (-0.004, 0.034),
        (0.021, -0.032),
        (-0.027, 0.027),
    ]

    def make(label: str, count: int, fleet: int, capacity: int, weight: int) -> Scenario:
        depot = SimpleNamespace(
            id=_uid(label + ":depot"),
            latitude=55.8600,
            longitude=-4.2500,
            operating_hours_start=time(9),
            operating_hours_end=time(18),
        )
        vehicles = [
            SimpleNamespace(
                id=_uid(f"{label}:vehicle:{i}"),
                current_driver_id=_uid(f"{label}:driver:{i}"),
                capacity_kg=capacity,
            )
            for i in range(fleet)
        ]
        orders = []
        for i, (lat_delta, lon_delta) in enumerate(offsets[:count]):
            orders.append(
                SimpleNamespace(
                    id=_uid(f"{label}:order:{i}"),
                    customer=SimpleNamespace(
                        latitude=55.8600 + lat_delta,
                        longitude=-4.2500 + lon_delta,
                        address=f"Fixture stop {i + 1}",
                    ),
                    total_weight_kg=weight,
                    service_time_minutes=4,
                    time_window_start=datetime(2030, 1, 15, 9),
                    time_window_end=datetime(2030, 1, 15, 17),
                )
            )
        return Scenario(name=label, depot=depot, vehicles=vehicles, orders=orders)

    return [
        make("single_van_8_stops", 8, 1, 130, 10),
        make("two_vans_12_stops", 12, 2, 90, 10),
        make("infeasible_capacity", 1, 1, 15, 50),
    ]


def _metres(left, right) -> int:
    return round(
        VehicleRoutingOptimizer._haversine(
            float(left.latitude),
            float(left.longitude),
            float(right.latitude),
            float(right.longitude),
        )
    )


def _arrival_seconds(value: datetime) -> int:
    return int((value - datetime.combine(ROUTE_DATE, time())).total_seconds())


def nearest_neighbour(case: Scenario) -> list[dict]:
    """Greedy first-feasible local heuristic, never ignores windows/capacity.

    Unlike the global optimiser, this deliberately does not revise earlier
    choices or reassign a stop across vehicles. Unassigned orders are explicit.
    """
    pending = {order.id: order for order in case.orders}
    start = VehicleRoutingOptimizer._time_to_seconds(case.depot.operating_hours_start)
    finish = VehicleRoutingOptimizer._time_to_seconds(case.depot.operating_hours_end)
    routes = []
    for vehicle in case.vehicles:
        position = case.depot
        clock = start
        used = 0.0
        travelled = 0
        stops = []
        while pending:
            feasible = []
            for order in pending.values():
                weight = float(order.total_weight_kg)
                if used + weight > float(vehicle.capacity_kg):
                    continue
                distance = _metres(position, order.customer)
                travel_seconds = math.ceil(distance / SPEED_METRES_PER_SECOND)
                arrival = max(
                    clock + (4 * 60 if stops else 0) + travel_seconds,
                    _arrival_seconds(order.time_window_start),
                )
                return_seconds = math.ceil(
                    _metres(order.customer, case.depot) / SPEED_METRES_PER_SECOND
                )
                if (
                    arrival > _arrival_seconds(order.time_window_end)
                    or arrival + 4 * 60 + return_seconds > finish
                ):
                    continue
                feasible.append((distance, str(order.id), order, arrival))
            if not feasible:
                break
            distance, _, order, arrival = min(feasible, key=lambda x: (x[0], x[1]))
            stops.append(
                {
                    "sequence": len(stops) + 1,
                    "order_id": order.id,
                    "planned_arrival": datetime.combine(ROUTE_DATE, time())
                    + timedelta(seconds=arrival),
                }
            )
            travelled += distance
            used += float(order.total_weight_kg)
            clock = arrival
            position = order.customer
            del pending[order.id]
        if stops:
            travelled += _metres(position, case.depot)
            duration = (
                clock
                + 4 * 60
                + math.ceil(_metres(position, case.depot) / SPEED_METRES_PER_SECOND)
                - start
            )
            routes.append(
                {
                    "vehicle_id": vehicle.id,
                    "stops": stops,
                    "metrics": {
                        "total_distance_km": travelled / 1000,
                        "total_duration_minutes": math.ceil(duration / 60),
                    },
                }
            )
    return routes


def measure(case: Scenario, routes: list[dict], solve_ms: float) -> dict:
    """Independently count infeasible and duplicate assignments."""
    expected = {order.id: order for order in case.orders}
    vehicles = {vehicle.id: vehicle for vehicle in case.vehicles}
    assigned = set()
    violations = 0
    total_metres = 0
    duration_minutes = 0.0
    for route in routes:
        vehicle = vehicles.get(route["vehicle_id"])
        if vehicle is None:
            violations += 1
            continue
        weight = 0.0
        position = case.depot
        for stop in route["stops"]:
            key = stop["order_id"]
            order = expected.get(key)
            if order is None or key in assigned:
                violations += 1
                continue
            assigned.add(key)
            weight += float(order.total_weight_kg)
            if not order.time_window_start <= stop["planned_arrival"] <= order.time_window_end:
                violations += 1
            total_metres += _metres(position, order.customer)
            position = order.customer
        total_metres += _metres(position, case.depot)
        if weight > float(vehicle.capacity_kg):
            violations += 1
        duration_minutes += float(route["metrics"]["total_duration_minutes"])
    return {
        "assigned_orders": len(assigned),
        "unassigned_orders": len(expected) - len(assigned),
        "capacity_or_window_or_duplicate_violations": violations,
        "distance_km_haversine": round(total_metres / 1000, 3),
        "route_duration_minutes_sum": round(duration_minutes, 2),
        "illustrative_route_cost_gbp": round(
            total_metres / 1000 * ASSUMED_GBP_PER_KM, 2
        ),
        "solve_ms_single_run": round(solve_ms, 3),
    }


def run_benchmark() -> dict:
    rows = []
    for case in synthetic_cases():
        t0 = perf_counter()
        routes = VehicleRoutingOptimizer(planning_time_limit_sec=1).optimize(
            case.orders, case.vehicles, case.depot, ROUTE_DATE
        )
        solver_ms = (perf_counter() - t0) * 1000
        t1 = perf_counter()
        baseline = nearest_neighbour(case)
        baseline_ms = (perf_counter() - t1) * 1000
        score = measure(case, routes, solver_ms)
        naive_score = measure(case, baseline, baseline_ms)
        assert score["capacity_or_window_or_duplicate_violations"] == 0
        assert naive_score["capacity_or_window_or_duplicate_violations"] == 0
        if case.name != "infeasible_capacity":
            assert score["unassigned_orders"] == 0, "Solver lost a feasible fixture order"
        else:
            assert score["unassigned_orders"] == len(case.orders)
        rows.append(
            {
                "scenario": case.name,
                "orders": len(case.orders),
                "vehicles": len(case.vehicles),
                "ortools": score,
                "nearest_neighbour": naive_score,
                "comparison_valid_only_if_equal_assignments": (
                    score["assigned_orders"] == naive_score["assigned_orders"]
                ),
            }
        )
    return {
        "version": "fleetflow_synthetic_cvrptw_benchmark_v1",
        "route_date": ROUTE_DATE.isoformat(),
        "assumptions": {
            "coordinates": "original synthetic location offsets near Glasgow",
            "distance": "round-to-metre Haversine straight-line",
            "speed_kmh": 30,
            "vehicle_cost_gbp_per_km_illustrative": ASSUMED_GBP_PER_KM,
            "model": "not road network, traffic ETA or actual fleet costs",
            "scope": "single unpinned CI machine, not a production SLA",
        },
        "results": rows,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = run_benchmark()
    with args.output.open("x", encoding="utf-8") as handle:
        json.dump(report, handle, sort_keys=True, indent=2)
        handle.write("\n")
    print(json.dumps({"scenarios": len(report["results"]), "output": str(args.output)}))


if __name__ == "__main__":
    main()

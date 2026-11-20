"""Required real OR-Tools versus constraint-aware nearest-neighbour acceptance."""

from datetime import datetime

from src.optimization.benchmark import (
    measure,
    nearest_neighbour,
    run_benchmark,
    synthetic_cases,
)
from src.optimization.route_optimizer import VehicleRoutingOptimizer


def test_scenarios_are_deterministic_and_synthetic():
    first = synthetic_cases()
    second = synthetic_cases()
    assert [s.name for s in first] == [s.name for s in second]
    assert [str(o.id) for s in first for o in s.orders] == [
        str(o.id) for s in second for o in s.orders
    ]
    assert sum(len(s.orders) for s in first) == 21


def test_real_ortools_serves_feasible_orders_without_violations():
    for case in synthetic_cases()[:2]:
        routes = VehicleRoutingOptimizer(planning_time_limit_sec=1).optimize(
            case.orders,
            case.vehicles,
            case.depot,
            case.orders[0].time_window_start.date(),
        )
        result = measure(case, routes, 0.0)
        assert result["assigned_orders"] == len(case.orders)
        assert result["unassigned_orders"] == 0
        assert result["capacity_or_window_or_duplicate_violations"] == 0
        assert result["distance_km_haversine"] > 0


def test_nearest_neighbour_is_capacity_and_window_aware():
    for case in synthetic_cases():
        result = measure(case, nearest_neighbour(case), 0.0)
        assert result["capacity_or_window_or_duplicate_violations"] == 0
        assert 0 <= result["assigned_orders"] <= len(case.orders)


def test_explicit_infeasible_case_is_never_claimed_delivered():
    case = synthetic_cases()[-1]
    result = measure(
        case,
        VehicleRoutingOptimizer(planning_time_limit_sec=1).optimize(
            case.orders,
            case.vehicles,
            case.depot,
            case.orders[0].time_window_start.date(),
        ),
        0,
    )
    assert result["unassigned_orders"] == 1
    assert result["assigned_orders"] == 0
    assert measure(case, nearest_neighbour(case), 0)["unassigned_orders"] == 1


def test_invalid_duplicate_assignment_is_detected():
    case = synthetic_cases()[0]
    order = case.orders[0]
    bogus = [
        {
            "vehicle_id": case.vehicles[0].id,
            "stops": [
                {"order_id": order.id, "planned_arrival": datetime(2030, 1, 15, 10)},
                {"order_id": order.id, "planned_arrival": datetime(2030, 1, 15, 11)},
            ],
            "metrics": {"total_duration_minutes": 90},
        }
    ]
    result = measure(case, bogus, 0)
    assert result["capacity_or_window_or_duplicate_violations"] > 0
    assert result["assigned_orders"] == 1


def test_greedy_respects_long_service_times():
    case = synthetic_cases()[0]
    for order in case.orders:
        order.service_time_minutes = 600
    assert measure(case, nearest_neighbour(case), 0)["assigned_orders"] == 0


def test_report_declares_same_inputs_and_no_extrapolated_savings():
    report = run_benchmark()
    assert report["version"] == "fleetflow_synthetic_cvrptw_benchmark_v1"
    assert "not road network" in report["assumptions"]["model"]
    assert len(report["results"]) == 3
    assert all(
        row["ortools"]["capacity_or_window_or_duplicate_violations"] == 0
        for row in report["results"]
    )
    assert all("solve_ms_single_run" in row["ortools"] for row in report["results"])

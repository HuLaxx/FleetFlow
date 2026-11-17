"""Routing benchmark must use the real solver and expose infeasibility."""

from src.optimization.benchmark import (
    _input_order,
    _simulate,
    benchmark_scenario,
    run_all,
    scenario,
)


def test_benchmark_runs_real_ortools_and_two_deterministic_heuristics():
    results = run_all(solver_seconds=1)
    assert results["dataset"] == "fixed-synthetic-fleetflow-routing-v1"
    assert len(results["results"]) == 9
    assert {row["method"] for row in results["results"]} == {
        "input_order", "nearest_neighbour", "ortools_cvrptw"
    }
    assert {row["scenario"] for row in results["results"]} == {
        "city_feasible", "window_feasible", "capacity_infeasible"
    }
    for row in results["results"]:
        assert row["orders"] == row["served"] + row["unassigned"]
        assert row["constraint_violations"] == 0
        assert row["solve_time_ms"] >= 0
        assert row["total_distance_km"] >= 0
        assert row["illustrative_cost_gbp"] is None or row["is_feasible"]
        if row["is_feasible"]:
            assert row["unassigned"] == 0
            assert row["illustrative_cost_gbp"] > 0

    for case in ("city_feasible", "window_feasible"):
        solver = next(row for row in results["results"] if
                      row["scenario"] == case and row["method"] == "ortools_cvrptw")
        assert solver["is_feasible"], solver
        assert solver["served"] == solver["orders"]


def test_capacity_infeasible_is_not_counted_as_zero_cost_success():
    cases = benchmark_scenario("capacity_infeasible", solver_seconds=1)
    assert all(not row["is_feasible"] for row in cases)
    assert all(row["illustrative_cost_gbp"] is None for row in cases)
    assert all(row["unassigned"] > 0 for row in cases)
    assert all(row["constraint_violations"] == 0 for row in cases)


def test_baseline_does_not_ignore_weight_capacity():
    depot, orders, vehicles = scenario("capacity_infeasible")
    selected = _input_order(depot, orders, vehicles)
    report = _simulate(depot, orders, vehicles, selected)
    assert report["served"] == 1
    assert report["unassigned"] == 1
    assert report["constraint_violations"] == 0


def test_all_synthetic_ids_stable_and_model_assumptions_not_road_network():
    first = scenario("city_feasible")
    second = scenario("city_feasible")
    assert [str(o.id) for o in first[1]] == [str(o.id) for o in second[1]]
    assert first[0].id == second[0].id
    assert all(o.customer.address.startswith("Synthetic") for o in first[1])
    report = run_all(solver_seconds=1)
    assert report["travel"].startswith("fixed 30 km/h")
    assert "not actual expenditure" in report["cost"]

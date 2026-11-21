"""Fail-closed optimiser output contract at the route persistence boundary."""

from datetime import datetime
from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException

from src.api.routes.optimization import _check_candidate_integrity


@pytest.mark.parametrize(
    "metrics",
    [
        {"total_distance_km": "NaN", "total_duration_minutes": 10},
        {"total_distance_km": "Infinity", "total_duration_minutes": 10},
        {"total_distance_km": -1, "total_duration_minutes": 10},
        {"total_distance_km": 1, "total_duration_minutes": -1},
        {"total_distance_km": 1},
        {"total_distance_km": None, "total_duration_minutes": 10},
        {},
        None,
    ],
)
def test_solver_rejects_unsafe_route_metrics(metrics):
    vehicle_id, driver_id, order_id = uuid4(), uuid4(), uuid4()
    vehicle = SimpleNamespace(
        id=vehicle_id, current_driver_id=driver_id, capacity_kg=Decimal("100")
    )
    order = SimpleNamespace(
        id=order_id,
        total_weight_kg=Decimal("1"),
        time_window_start=datetime(2026, 11, 21, 9),
        time_window_end=datetime(2026, 11, 21, 17),
    )
    candidate = {
        "vehicle_id": vehicle_id,
        "driver_id": driver_id,
        "metrics": metrics,
        "stops": [
            {
                "order_id": order_id,
                "sequence": 1,
                "planned_arrival": datetime(2026, 11, 21, 12),
            }
        ],
    }
    with pytest.raises(HTTPException) as error:
        _check_candidate_integrity([candidate], [vehicle], [order])
    assert error.value.status_code == 422
    assert error.value.detail == "Solver returned invalid route metrics"


def test_solver_accepts_finite_nonnegative_route_metrics():
    vehicle_id, driver_id, order_id = uuid4(), uuid4(), uuid4()
    vehicle = SimpleNamespace(
        id=vehicle_id, current_driver_id=driver_id, capacity_kg=Decimal("100")
    )
    order = SimpleNamespace(
        id=order_id,
        total_weight_kg=Decimal("1"),
        time_window_start=datetime(2026, 11, 21, 9),
        time_window_end=datetime(2026, 11, 21, 17),
    )
    candidate = {
        "vehicle_id": vehicle_id,
        "driver_id": driver_id,
        "metrics": {"total_distance_km": "0.0", "total_duration_minutes": 0},
        "stops": [
            {
                "order_id": order_id,
                "sequence": 1,
                "planned_arrival": datetime(2026, 11, 21, 12),
            }
        ],
    }
    _check_candidate_integrity([candidate], [vehicle], [order])

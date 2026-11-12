"""CPU-only numerical smoke checks for FleetFlow ML components.

This is not model accuracy evidence. It verifies implementation wiring,
unit conventions, finite outputs and a trainable computational graph.
"""
from pathlib import Path
import sys

import pytest
import torch

ML_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ML_ROOT))
sys.path.insert(0, str(ML_ROOT / "forecasting"))

from route_optimizer import VehicleRoutingOptimizer  # noqa: E402
from model import DemandForecaster  # noqa: E402


def test_ortools_distance_units_and_zero_diagonal():
    optimizer = VehicleRoutingOptimizer(planning_time_limit_sec=2)
    assert optimizer._haversine(0.0, 0.0, 0.0, 0.0) == 0
    distance_metres = optimizer._haversine(40.7128, -74.0060, 34.0522, -118.2437)
    assert 3_900_000 < distance_metres < 4_000_000


def test_forecasting_forward_pass_is_finite_and_shape_correct():
    torch.manual_seed(42)
    model = DemandForecaster(input_size=10, hidden_size=32, num_layers=1, output_size=1)
    sample = torch.randn(4, 24, 10)
    predictions = model(sample)
    assert predictions.shape == (4, 1)
    assert torch.isfinite(predictions).all()


def test_forecasting_gradient_step_changes_parameters():
    torch.manual_seed(42)
    model = DemandForecaster(input_size=10, hidden_size=16, num_layers=1, output_size=1)
    inputs = torch.randn(4, 24, 10)
    targets = torch.randn(4, 1)
    before = [parameter.detach().clone() for parameter in model.parameters()]
    optimizer = torch.optim.Adam(model.parameters(), lr=0.01)
    optimizer.zero_grad()
    loss = torch.nn.MSELoss()(model(inputs), targets)
    assert torch.isfinite(loss)
    loss.backward()
    optimizer.step()
    assert any(not torch.equal(old, new) for old, new in zip(before, model.parameters()))

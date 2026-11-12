"""Real optimizer checks and optional CPU-only forecasting smoke tests.

The route optimizer is installed with the FleetFlow backend. These tests must
fail if the optimizer import or its distance calculations are broken.
PyTorch remains an explicitly optional ML runtime in the backend CI; its
separate ML evaluation pipeline must test the forecasting model.
"""
from pathlib import Path
import sys

import pytest

# backend/tests/test_ml -> repository root -> ml
REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT / "ml"))

from route_optimizer import VehicleRoutingOptimizer  # noqa: E402


class TestVRPOptimizer:
    def test_optimizer_initialization(self):
        optimizer = VehicleRoutingOptimizer(planning_time_limit_sec=2)
        assert optimizer.time_limit_sec == 2

    def test_haversine_distance_calculation(self):
        """NYC to LA is roughly 3940 km, returned as metres by the optimizer."""
        optimizer = VehicleRoutingOptimizer(planning_time_limit_sec=2)
        distance_metres = optimizer._haversine(40.7128, -74.0060, 34.0522, -118.2437)
        assert 3_900_000 < distance_metres < 4_000_000

    def test_haversine_same_location(self):
        optimizer = VehicleRoutingOptimizer(planning_time_limit_sec=2)
        assert optimizer._haversine(40.7128, -74.0060, 40.7128, -74.0060) == 0.0


class TestDemandForecaster:
    @staticmethod
    def _model(output_size=1, hidden_size=32, num_layers=1):
        pytest.importorskip("torch", reason="CPU PyTorch is optional in backend CI")
        sys.path.insert(0, str(REPO_ROOT / "ml" / "forecasting"))
        from model import DemandForecaster
        return DemandForecaster(
            input_size=10,
            hidden_size=hidden_size,
            num_layers=num_layers,
            output_size=output_size,
        )

    def test_model_initialization(self):
        import_torch = pytest.importorskip("torch", reason="CPU PyTorch is optional in backend CI")
        model = self._model(hidden_size=64, num_layers=2)
        assert isinstance(model, import_torch.nn.Module)

    def test_forward_pass(self):
        torch = pytest.importorskip("torch", reason="CPU PyTorch is optional in backend CI")
        torch.manual_seed(42)
        model = self._model(hidden_size=64, num_layers=2)
        out = model(torch.randn(4, 24, 10))
        assert out.shape == (4, 1)
        assert torch.isfinite(out).all()

    def test_model_can_train(self):
        torch = pytest.importorskip("torch", reason="CPU PyTorch is optional in backend CI")
        torch.manual_seed(42)
        model = self._model()
        optimizer = torch.optim.Adam(model.parameters(), lr=0.01)
        criterion = torch.nn.MSELoss()
        x = torch.randn(4, 24, 10)
        y = torch.randn(4, 1)
        before = [p.detach().clone() for p in model.parameters()]
        optimizer.zero_grad()
        loss = criterion(model(x), y)
        assert torch.isfinite(loss)
        loss.backward()
        optimizer.step()
        assert any(not torch.equal(old, p) for old, p in zip(before, model.parameters()))

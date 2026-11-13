"""Packaged route-optimisation service shared by API and ML smoke tests."""

from src.optimization.route_optimizer import VehicleRoutingOptimizer

__all__ = ["VehicleRoutingOptimizer"]

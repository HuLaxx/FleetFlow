"""Compatibility entry point for historical ML smoke tests.

The API and numerical smoke tests use the same packaged OR-Tools implementation.
The repository's backend directory is added only for standalone `ml/` scripts;
production imports resolve `src.optimization` from the installed backend wheel.
"""

import sys
from pathlib import Path

_backend_root = Path(__file__).resolve().parents[1] / "backend"
if str(_backend_root) not in sys.path:
    sys.path.insert(0, str(_backend_root))

from src.optimization.route_optimizer import VehicleRoutingOptimizer  # noqa: E402

__all__ = ["VehicleRoutingOptimizer"]

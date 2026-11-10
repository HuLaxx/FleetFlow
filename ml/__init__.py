"""FleetFlow ML package.

Exports are resolved lazily so importing feature engineering or synthetic-data
utilities does not require every optional serving/forecasting dependency.
"""

from importlib import import_module

_EXPORT_MODULES = {
    **dict.fromkeys(
        ["ForecastConfig", "ProphetForecaster", "LSTMForecaster",
         "XGBoostForecaster", "EnsembleForecaster", "forecast_demand"],
        "forecasting",
    ),
    **dict.fromkeys(
        ["Location", "Order", "Vehicle", "OptimizedRoute", "OptimizationResult",
         "ORToolsOptimizer", "GeneticOptimizer", "optimize_routes"],
        "optimization",
    ),
    **dict.fromkeys(
        ["ExperimentConfig", "MLflowTracker", "ForecastingExperiment",
         "OptimizationExperiment"],
        "tracking",
    ),
    **dict.fromkeys(
        ["DriverState", "InferenceResult", "ETAPredictor",
         "ReRoutingDetector", "InferencePipeline"],
        "inference",
    ),
}

__all__ = list(_EXPORT_MODULES)
__version__ = "1.0.1"


def __getattr__(name: str):
    if name not in _EXPORT_MODULES:
        raise AttributeError(f"module 'ml' has no attribute {name!r}")
    module = import_module(f".{_EXPORT_MODULES[name]}", __name__)
    value = getattr(module, name)
    globals()[name] = value
    return value


def __dir__():
    return sorted(set(globals()) | set(__all__))

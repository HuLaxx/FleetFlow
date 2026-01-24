"""FleetFlow ML Module - Complete ML/AI Package"""

# Forecasting
from ml.forecasting import (
    ForecastConfig,
    ProphetForecaster,
    LSTMForecaster,
    XGBoostForecaster,
    EnsembleForecaster,
    forecast_demand,
)

# Optimization
from ml.optimization import (
    Location,
    Order,
    Vehicle,
    OptimizedRoute,
    OptimizationResult,
    ORToolsOptimizer,
    GeneticOptimizer,
    optimize_routes,
)

# MLflow Tracking
from ml.tracking import (
    ExperimentConfig,
    MLflowTracker,
    ForecastingExperiment,
    OptimizationExperiment,
)

# Inference
from ml.inference import (
    DriverState,
    InferenceResult,
    ETAPredictor,
    ReRoutingDetector,
    InferencePipeline,
)

__all__ = [
    # Forecasting
    "ForecastConfig",
    "ProphetForecaster",
    "LSTMForecaster",
    "XGBoostForecaster",
    "EnsembleForecaster",
    "forecast_demand",
    # Optimization
    "Location",
    "Order",
    "Vehicle",
    "OptimizedRoute",
    "OptimizationResult",
    "ORToolsOptimizer",
    "GeneticOptimizer",
    "optimize_routes",
    # Tracking
    "ExperimentConfig",
    "MLflowTracker",
    "ForecastingExperiment",
    "OptimizationExperiment",
    # Inference
    "DriverState",
    "InferenceResult",
    "ETAPredictor",
    "ReRoutingDetector",
    "InferencePipeline",
]

__version__ = "1.0.0"

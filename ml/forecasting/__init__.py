"""Demand forecasting tools: ensemble models and the separate PyTorch LSTM pipeline.

Keep this package import-compatible with `from ml.forecasting import
EnsembleForecaster` while enabling `ml.forecasting.features` and
`ml.forecasting.model` imports.
"""

from .ensemble import (
    ForecastConfig,
    ProphetForecaster,
    LSTMForecaster,
    XGBoostForecaster,
    EnsembleForecaster,
    forecast_demand,
)

__all__ = [
    "ForecastConfig",
    "ProphetForecaster",
    "LSTMForecaster",
    "XGBoostForecaster",
    "EnsembleForecaster",
    "forecast_demand",
]

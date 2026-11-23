"""Leakage-safe time-series scaling and transparent demand-forecast evaluation."""

from typing import Tuple

import numpy as np
from sklearn.preprocessing import MinMaxScaler


def scale_fold(
    x_train: np.ndarray,
    y_train: np.ndarray,
    x_valid: np.ndarray,
    y_valid: np.ndarray,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, MinMaxScaler, MinMaxScaler]:
    """Scale using TRAINING data only; never fit on a future validation period.

    Input arrays have shape (samples, lookback_steps, features).
    The target scaler is intentionally separate from the feature scaler.
    """
    x_train = np.asarray(x_train, dtype=np.float64)
    x_valid = np.asarray(x_valid, dtype=np.float64)
    y_train = np.asarray(y_train, dtype=np.float64).reshape(-1, 1)
    y_valid = np.asarray(y_valid, dtype=np.float64).reshape(-1, 1)

    if x_train.ndim != 3 or x_valid.ndim != 3:
        raise ValueError("Expected 3D (samples, sequence, features) inputs")
    if x_train.shape[1:] != x_valid.shape[1:]:
        raise ValueError("Training and validation feature dimensions differ")
    if x_train.shape[0] != y_train.shape[0] or x_valid.shape[0] != y_valid.shape[0]:
        raise ValueError("Input and target sample counts differ")
    if x_train.shape[0] == 0 or x_valid.shape[0] == 0:
        raise ValueError("Both folds must contain observations")
    for array in [x_train, x_valid, y_train, y_valid]:
        if not np.isfinite(array).all():
            raise ValueError("Non-finite values are not allowed")

    features = x_train.shape[2]
    input_scaler = MinMaxScaler()
    target_scaler = MinMaxScaler()
    input_scaler.fit(x_train.reshape(-1, features))
    target_scaler.fit(y_train)

    train_x = input_scaler.transform(x_train.reshape(-1, features)).reshape(x_train.shape)
    valid_x = input_scaler.transform(x_valid.reshape(-1, features)).reshape(x_valid.shape)
    train_y = target_scaler.transform(y_train).reshape(-1)
    valid_y = target_scaler.transform(y_valid).reshape(-1)
    return train_x, train_y, valid_x, valid_y, input_scaler, target_scaler


def forecast_metrics(actual: np.ndarray, predicted: np.ndarray, baseline: np.ndarray) -> dict:
    """Evaluate in actual order counts against a naive last-observation baseline."""
    actual = np.asarray(actual, dtype=float).reshape(-1)
    predicted = np.asarray(predicted, dtype=float).reshape(-1)
    baseline = np.asarray(baseline, dtype=float).reshape(-1)
    if not (len(actual) and len(actual) == len(predicted) == len(baseline)):
        raise ValueError("Expected equal, nonempty prediction arrays")
    if not all(np.isfinite(v).all() for v in (actual, predicted, baseline)):
        raise ValueError("Metrics require finite values")

    predicted = np.maximum(predicted, 0.0)
    baseline = np.maximum(baseline, 0.0)
    model_mae = float(np.mean(np.abs(actual - predicted)))
    naive_mae = float(np.mean(np.abs(actual - baseline)))
    model_rmse = float(np.sqrt(np.mean((actual - predicted) ** 2)))
    # When naive MAE is zero, skill would be undefined; report None.
    skill = float(1.0 - model_mae / naive_mae) if naive_mae > 0 else None
    return {
        "model_mae_orders": model_mae,
        "naive_mae_orders": naive_mae,
        "model_rmse_orders": model_rmse,
        "skill_vs_naive": skill,
        "beats_naive": model_mae < naive_mae,
    }


def serializable_scaler(scaler: MinMaxScaler) -> dict:
    """Store inference-time scaling parameters without unsafe pickled objects."""
    return {
        "data_min": scaler.data_min_.tolist(),
        "data_max": scaler.data_max_.tolist(),
        "scale": scaler.scale_.tolist(),
        "min": scaler.min_.tolist(),
    }

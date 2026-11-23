"""Regressions for leakage-safe preprocessing and forecasting evaluation."""

import numpy as np
import pandas as pd
import pytest

from ml.forecasting.features import FeatureEngineer
from ml.forecasting.validation import scale_fold, forecast_metrics


def test_features_do_not_mutate_source_or_look_at_current_target():
    n = 240
    source = pd.DataFrame({
        "timestamp": pd.date_range("2026-01-01", periods=n, freq="h"),
        "order_count": np.full(n, 8.0),
    })
    source.loc[239, "order_count"] = 9999.0
    untouched = source.copy(deep=True)

    engineered = FeatureEngineer().create_features(source)
    pd.testing.assert_frame_equal(source, untouched)
    row = engineered.iloc[-1]
    # Last observed demand must not leak into same-row rolling statistics.
    assert row["rolling_mean_24h"] == pytest.approx(8.0)
    assert row["lag_1h"] == pytest.approx(8.0)


def test_validation_outliers_do_not_change_training_scalers():
    x_train = np.array([[[1.0], [2.0]], [[2.0], [3.0]], [[3.0], [4.0]]])
    y_train = np.array([3.0, 4.0, 5.0])
    x_valid = np.array([[[1000.0], [2000.0]]])
    y_valid = np.array([4000.0])

    train_x, train_y, valid_x, valid_y, features, target = scale_fold(
        x_train, y_train, x_valid, y_valid
    )
    assert features.data_max_[0] == 4.0
    assert target.data_max_[0] == 5.0
    assert train_x.max() == pytest.approx(1.0)
    assert train_y.max() == pytest.approx(1.0)
    assert valid_x.max() > 1.0
    assert valid_y.max() > 1.0
    assert target.inverse_transform(train_y.reshape(-1, 1)).reshape(-1) == pytest.approx(y_train)


def test_raw_sequences_are_monotonic_and_not_pre_scaled():
    frame = pd.DataFrame({
        "timestamp": pd.date_range("2026-01-01", periods=250, freq="h"),
        "order_count": np.arange(250, dtype=float),
    })
    fe = FeatureEngineer()
    X, y = fe.prepare_raw_sequences(fe.create_features(frame), sequence_length=24)
    assert X.ndim == 3
    assert y.ndim == 1
    assert len(X) == len(y)
    assert y[0] > X[0, -1, fe.feature_columns.index("order_count")]
    assert X.max() > 1.0


def test_model_metrics_compare_to_naive_in_actual_count_units():
    report = forecast_metrics(
        actual=[10, 20, 30],
        predicted=[12, 21, 28],
        baseline=[9, 9, 9],
    )
    assert report["model_mae_orders"] == pytest.approx(5 / 3)
    assert report["naive_mae_orders"] == pytest.approx(33 / 3)
    assert report["beats_naive"] is True
    assert report["skill_vs_naive"] is not None
    assert report["skill_vs_naive"] > 0


def test_empty_or_nonfinite_inputs_fail_explicitly():
    with pytest.raises(ValueError):
        forecast_metrics([], [], [])
    with pytest.raises(ValueError):
        scale_fold(
            np.array([[[float("nan")]]]), np.array([1.0]),
            np.array([[[1.0]]]), np.array([1.0])
        )

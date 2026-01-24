"""
FleetFlow Demand Forecasting Module

Ensemble forecasting using:
- Prophet for trend and seasonality
- LSTM for complex patterns
- XGBoost for feature-based prediction

Target: Predict hourly order volume per zone
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional, Tuple, List, Dict, Any
from dataclasses import dataclass
import logging

# Prophet for time series
try:
    from prophet import Prophet
except ImportError:
    Prophet = None

# TensorFlow/Keras for LSTM
try:
    import tensorflow as tf
    from tensorflow.keras.models import Sequential
    from tensorflow.keras.layers import LSTM, Dense, Dropout
    from tensorflow.keras.callbacks import EarlyStopping
except ImportError:
    tf = None

# XGBoost for feature-based
try:
    import xgboost as xgb
except ImportError:
    xgb = None

logger = logging.getLogger(__name__)


@dataclass
class ForecastConfig:
    """Configuration for forecasting models."""
    # Data
    lookback_days: int = 30
    forecast_horizon_hours: int = 24
    
    # Prophet
    prophet_yearly_seasonality: bool = False
    prophet_weekly_seasonality: bool = True
    prophet_daily_seasonality: bool = True
    
    # LSTM
    lstm_sequence_length: int = 24
    lstm_units: int = 64
    lstm_epochs: int = 50
    lstm_batch_size: int = 32
    
    # Ensemble weights
    prophet_weight: float = 0.4
    lstm_weight: float = 0.35
    xgboost_weight: float = 0.25


class ProphetForecaster:
    """
    Facebook Prophet forecaster for demand prediction.
    
    Good for:
    - Capturing weekly/daily seasonality
    - Handling holidays
    - Trend changes
    """
    
    def __init__(self, config: ForecastConfig):
        self.config = config
        self.model: Optional[Prophet] = None
    
    def fit(self, df: pd.DataFrame) -> None:
        """
        Fit Prophet model.
        
        Args:
            df: DataFrame with 'ds' (datetime) and 'y' (target) columns
        """
        if Prophet is None:
            raise ImportError("Prophet not installed")
        
        self.model = Prophet(
            yearly_seasonality=self.config.prophet_yearly_seasonality,
            weekly_seasonality=self.config.prophet_weekly_seasonality,
            daily_seasonality=self.config.prophet_daily_seasonality,
            interval_width=0.95,
        )
        
        # Add regressors if available
        if 'is_holiday' in df.columns:
            self.model.add_regressor('is_holiday')
        if 'weather_score' in df.columns:
            self.model.add_regressor('weather_score')
        
        self.model.fit(df)
        logger.info("Prophet model fitted")
    
    def predict(self, periods: int = 24) -> pd.DataFrame:
        """
        Generate forecast.
        
        Args:
            periods: Number of hours to forecast
            
        Returns:
            DataFrame with yhat, yhat_lower, yhat_upper
        """
        if self.model is None:
            raise ValueError("Model not fitted")
        
        future = self.model.make_future_dataframe(periods=periods, freq='H')
        forecast = self.model.predict(future)
        
        return forecast[['ds', 'yhat', 'yhat_lower', 'yhat_upper']].tail(periods)


class LSTMForecaster:
    """
    LSTM neural network for sequence prediction.
    
    Good for:
    - Complex non-linear patterns
    - Long-term dependencies
    - Multi-step forecasting
    """
    
    def __init__(self, config: ForecastConfig):
        self.config = config
        self.model: Optional[Sequential] = None
        self.scaler_mean: float = 0
        self.scaler_std: float = 1
    
    def _prepare_sequences(
        self, data: np.ndarray
    ) -> Tuple[np.ndarray, np.ndarray]:
        """Create sequences for LSTM training."""
        X, y = [], []
        seq_len = self.config.lstm_sequence_length
        
        for i in range(len(data) - seq_len):
            X.append(data[i:i+seq_len])
            y.append(data[i+seq_len])
        
        return np.array(X), np.array(y)
    
    def _normalize(self, data: np.ndarray) -> np.ndarray:
        """Normalize data."""
        return (data - self.scaler_mean) / (self.scaler_std + 1e-8)
    
    def _denormalize(self, data: np.ndarray) -> np.ndarray:
        """Denormalize predictions."""
        return data * (self.scaler_std + 1e-8) + self.scaler_mean
    
    def fit(self, data: np.ndarray) -> Dict[str, Any]:
        """
        Fit LSTM model.
        
        Args:
            data: 1D array of hourly order counts
            
        Returns:
            Training history
        """
        if tf is None:
            raise ImportError("TensorFlow not installed")
        
        # Normalize
        self.scaler_mean = data.mean()
        self.scaler_std = data.std()
        normalized = self._normalize(data)
        
        # Create sequences
        X, y = self._prepare_sequences(normalized)
        if len(X) == 0:
            raise ValueError(
                f"Not enough data for LSTM sequences. Need > {self.config.lstm_sequence_length} points."
            )
        X = X.reshape((X.shape[0], X.shape[1], 1))
        
        # Split train/val
        split = int(len(X) * 0.8)
        X_train, X_val = X[:split], X[split:]
        y_train, y_val = y[:split], y[split:]
        
        # Build model
        self.model = Sequential([
            LSTM(self.config.lstm_units, input_shape=(self.config.lstm_sequence_length, 1),
                 return_sequences=True),
            Dropout(0.2),
            LSTM(self.config.lstm_units // 2),
            Dropout(0.2),
            Dense(1)
        ])
        
        self.model.compile(optimizer='adam', loss='mse', metrics=['mae'])
        
        # Train
        early_stop = EarlyStopping(patience=10, restore_best_weights=True)
        
        history = self.model.fit(
            X_train, y_train,
            validation_data=(X_val, y_val),
            epochs=self.config.lstm_epochs,
            batch_size=self.config.lstm_batch_size,
            callbacks=[early_stop],
            verbose=0
        )
        
        logger.info(f"LSTM model fitted, val_mae: {min(history.history['val_mae']):.4f}")
        return history.history
    
    def predict(self, recent_data: np.ndarray, steps: int = 24) -> np.ndarray:
        """
        Generate multi-step forecast.
        
        Args:
            recent_data: Last N hours of data
            steps: Number of hours to forecast
            
        Returns:
            Array of predictions
        """
        if self.model is None:
            raise ValueError("Model not fitted")
        
        normalized = self._normalize(recent_data)
        predictions = []
        
        # Use last sequence
        current_seq = normalized[-self.config.lstm_sequence_length:].reshape(1, -1, 1)
        
        for _ in range(steps):
            pred = self.model.predict(current_seq, verbose=0)[0, 0]
            predictions.append(pred)
            
            # Update sequence
            current_seq = np.roll(current_seq, -1, axis=1)
            current_seq[0, -1, 0] = pred
        
        return self._denormalize(np.array(predictions))


class XGBoostForecaster:
    """
    XGBoost for feature-based prediction.
    
    Good for:
    - Feature importance
    - Handling many input features
    - Fast inference
    """
    
    def __init__(self, config: ForecastConfig):
        self.config = config
        self.model = None
        self.feature_names: List[str] = []
    
    def _create_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Create time-based features."""
        features = pd.DataFrame()
        
        features['hour'] = df['ds'].dt.hour
        features['day_of_week'] = df['ds'].dt.dayofweek
        features['is_weekend'] = df['ds'].dt.dayofweek >= 5
        features['month'] = df['ds'].dt.month
        features['day_of_month'] = df['ds'].dt.day
        
        # Cyclical encoding
        features['hour_sin'] = np.sin(2 * np.pi * features['hour'] / 24)
        features['hour_cos'] = np.cos(2 * np.pi * features['hour'] / 24)
        features['dow_sin'] = np.sin(2 * np.pi * features['day_of_week'] / 7)
        features['dow_cos'] = np.cos(2 * np.pi * features['day_of_week'] / 7)
        
        # Lag features
        if 'y' in df.columns:
            for lag in [1, 2, 3, 24, 168]:  # 1h, 2h, 3h, 1d, 1w
                if lag < len(df):
                    features[f'lag_{lag}'] = df['y'].shift(lag)
            
            # Rolling statistics
            features['rolling_mean_24h'] = df['y'].rolling(24).mean()
            features['rolling_std_24h'] = df['y'].rolling(24).std()
        
        self.feature_names = list(features.columns)
        return features
    
    def fit(self, df: pd.DataFrame) -> None:
        """
        Fit XGBoost model.
        
        Args:
            df: DataFrame with 'ds' and 'y' columns
        """
        if xgb is None:
            raise ImportError("XGBoost not installed")
        
        features = self._create_features(df)
        features = features.dropna()
        y = df['y'].iloc[features.index]
        
        self.model = xgb.XGBRegressor(
            n_estimators=100,
            max_depth=6,
            learning_rate=0.1,
            random_state=42
        )
        
        self.model.fit(features, y)
        logger.info("XGBoost model fitted")
    
    def predict(self, df: pd.DataFrame) -> np.ndarray:
        """Generate predictions."""
        if self.model is None:
            raise ValueError("Model not fitted")
        
        features = self._create_features(df)
        return self.model.predict(features)
    
    def feature_importance(self) -> pd.DataFrame:
        """Get feature importance."""
        if self.model is None:
            return pd.DataFrame()
        
        importance = pd.DataFrame({
            'feature': self.feature_names,
            'importance': self.model.feature_importances_
        })
        return importance.sort_values('importance', ascending=False)


class EnsembleForecaster:
    """
    Ensemble of Prophet, LSTM, and XGBoost.
    
    Combines predictions using weighted average.
    """
    
    def __init__(self, config: Optional[ForecastConfig] = None):
        self.config = config or ForecastConfig()
        
        self.prophet = ProphetForecaster(self.config)
        self.lstm = LSTMForecaster(self.config)
        self.xgboost = XGBoostForecaster(self.config)
        
        self._fitted = False
    
    def fit(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Fit all models.
        
        Args:
            df: DataFrame with 'ds' (datetime) and 'y' (target) columns
            
        Returns:
            Training metrics
        """
        metrics = {}
        
        # Fit Prophet
        try:
            self.prophet.fit(df)
            metrics['prophet'] = 'fitted'
        except Exception as e:
            logger.warning(f"Prophet fitting failed: {e}")
            metrics['prophet'] = str(e)
        
        # Fit LSTM
        try:
            history = self.lstm.fit(df['y'].values)
            metrics['lstm'] = {
                'final_val_mae': history['val_mae'][-1],
                'epochs': len(history['loss'])
            }
        except Exception as e:
            logger.warning(f"LSTM fitting failed: {e}")
            metrics['lstm'] = str(e)
        
        # Fit XGBoost
        try:
            self.xgboost.fit(df)
            metrics['xgboost'] = 'fitted'
        except Exception as e:
            logger.warning(f"XGBoost fitting failed: {e}")
            metrics['xgboost'] = str(e)
        
        self._fitted = True
        return metrics
    
    def predict(
        self,
        df: pd.DataFrame,
        periods: int = 24
    ) -> pd.DataFrame:
        """
        Generate ensemble forecast.
        
        Returns:
            DataFrame with predictions from each model and ensemble
        """
        if not self._fitted:
            raise ValueError("Models not fitted")
        
        results = pd.DataFrame()
        results['ds'] = pd.date_range(
            start=df['ds'].max() + pd.Timedelta(hours=1),
            periods=periods,
            freq='H'
        )
        
        # Prophet predictions
        try:
            prophet_pred = self.prophet.predict(periods)
            results['prophet'] = prophet_pred['yhat'].values
        except Exception:
            results['prophet'] = np.nan
        
        # LSTM predictions
        try:
            lstm_pred = self.lstm.predict(df['y'].values, periods)
            results['lstm'] = lstm_pred
        except Exception:
            results['lstm'] = np.nan
        
        # XGBoost predictions (use future dates)
        try:
            future_df = pd.DataFrame({'ds': results['ds']})
            future_df['y'] = df['y'].iloc[-1]  # Use last known value for lags
            xgb_pred = self.xgboost.predict(future_df)
            results['xgboost'] = xgb_pred
        except Exception:
            results['xgboost'] = np.nan
        
        # Ensemble (weighted average)
        weights = [self.config.prophet_weight, self.config.lstm_weight, self.config.xgboost_weight]
        preds = results[['prophet', 'lstm', 'xgboost']].values
        
        # Handle NaN by adjusting weights
        valid_mask = ~np.isnan(preds)
        adjusted_weights = np.where(valid_mask, weights, 0)
        weight_sum = adjusted_weights.sum(axis=1, keepdims=True)
        weight_sum[weight_sum == 0] = 1  # Avoid division by zero
        
        ensemble = np.nansum(preds * adjusted_weights, axis=1) / weight_sum.flatten()
        results['ensemble'] = ensemble
        
        return results


# Convenience function
def forecast_demand(
    historical_data: pd.DataFrame,
    forecast_hours: int = 24,
    config: Optional[ForecastConfig] = None
) -> pd.DataFrame:
    """
    High-level function to forecast demand.
    
    Args:
        historical_data: DataFrame with 'ds' and 'y' columns
        forecast_hours: Number of hours to forecast
        config: Optional configuration
        
    Returns:
        DataFrame with forecasts
    """
    forecaster = EnsembleForecaster(config)
    forecaster.fit(historical_data)
    return forecaster.predict(historical_data, forecast_hours)

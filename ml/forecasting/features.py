"""
Feature Engineering for Demand Forecasting.
"""

import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler, MinMaxScaler

class FeatureEngineer:
    """
    Handles feature creation and scaling for the LSTM model.
    """
    
    def __init__(self):
        self.scaler = MinMaxScaler(feature_range=(0, 1))
        self.feature_columns = None
        
    def create_features(self, df: pd.DataFrame, target_col: str = 'order_count') -> pd.DataFrame:
        """
        Creates time-series features from raw data.
        Expected columns: timestamp, order_count, zone (optional if pre-filtered)
        """
        # Avoid mutating upstream training data and keep chronological order.
        df = df.copy()
        # Ensure timestamp is datetime
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df = df.sort_values('timestamp').reset_index(drop=True)
        
        # 1. Time-based features (Cyclical encoding)
        df['hour_sin'] = np.sin(2 * np.pi * df['timestamp'].dt.hour / 24)
        df['hour_cos'] = np.cos(2 * np.pi * df['timestamp'].dt.hour / 24)
        df['day_sin'] = np.sin(2 * np.pi * df['timestamp'].dt.dayofweek / 7)
        df['day_cos'] = np.cos(2 * np.pi * df['timestamp'].dt.dayofweek / 7)
        df['month_sin'] = np.sin(2 * np.pi * df['timestamp'].dt.month / 12)
        df['month_cos'] = np.cos(2 * np.pi * df['timestamp'].dt.month / 12)
        
        # 2. Lag features (Previous values)
        # Lag 1 hour, 24 hours (previous day), 168 hours (previous week)
        df['lag_1h'] = df[target_col].shift(1)
        df['lag_24h'] = df[target_col].shift(24)
        df['lag_168h'] = df[target_col].shift(168)
        
        # 3. Rolling Statistics
        df['rolling_mean_24h'] = df[target_col].shift(1).rolling(window=24).mean()
        df['rolling_std_24h'] = df[target_col].shift(1).rolling(window=24).std()
        
        # Drop NaNs created by lags
        df = df.dropna()
        
        return df

    def prepare_raw_sequences(
        self, df: pd.DataFrame, target_col: str = 'order_count', sequence_length: int = 24
    ):
        """Return chronological, UN-SCALED X/y sequences for leakage-safe CV.

        Split sequences by time first, then fit feature/target scalers using only
        each fold's training observations. Never fit scalers on held-out periods.
        """
        if sequence_length < 1:
            raise ValueError("sequence_length must be positive")
        numeric_df = df.select_dtypes(include=[np.number])
        if target_col not in numeric_df:
            raise ValueError(f"Missing numeric target column: {target_col}")
        if len(numeric_df) <= sequence_length:
            raise ValueError("Not enough observations to create sequences")
        if not np.isfinite(numeric_df.to_numpy(dtype=float)).all():
            raise ValueError("Training data contains non-finite numeric values")

        self.feature_columns = numeric_df.columns.tolist()
        data = numeric_df.to_numpy(dtype=np.float64)
        target_index = self.feature_columns.index(target_col)
        X = np.stack([
            data[index:index + sequence_length]
            for index in range(len(data) - sequence_length)
        ])
        y = data[sequence_length:, target_index].copy()
        return X, y

    def prepare_data(self, df: pd.DataFrame, target_col: str = 'order_count', sequence_length: int = 24):
        """
        Prepares data for LSTM (samples, sequence_length, features).
        Returns X, y and the scaler.
        """
        # Select feature columns (exclude timestamp, zone categorical for now or one-hot encode them before)
        # Assuming we train one model per zone or have one-hot encoded zones. 
        # For simplicity, let's assume we are training for a single zone or global model.
        # Let's drop non-numeric columns for now.
        
        numeric_df = df.select_dtypes(include=[np.number])
        self.feature_columns = [c for c in numeric_df.columns if c != target_col] # all except target? OR include target as feature?
        # Usually LSTM uses past target values as features.
        self.feature_columns = numeric_df.columns.tolist()
        
        # Scale data
        scaled_data = self.scaler.fit_transform(numeric_df[self.feature_columns])
        scaled_df = pd.DataFrame(scaled_data, columns=self.feature_columns)
        
        # Create sequences
        X, y = [], []
        target_idx = self.feature_columns.index(target_col)
        
        data_array = scaled_df.values
        
        for i in range(len(data_array) - sequence_length):
            # Input: sequence_length steps of all features
            X.append(data_array[i:(i + sequence_length)])
            # Target: The NEXT step's target value (single step forecasting)
            # Or sequence? Let's do next step 
            y.append(data_array[i + sequence_length, target_idx])
            
        return np.array(X), np.array(y)

    def inverse_transform(self, y_scaled):
        """Convert the target feature back from the legacy combined scaler."""
        if not self.feature_columns or not hasattr(self.scaler, 'scale_'):
            raise ValueError("Prepare scaled data before inverse transforming")
        target_index = self.feature_columns.index('order_count')
        scaled = np.asarray(y_scaled, dtype=np.float64)
        # MinMaxScaler transforms as X_scaled = X * scale_ + min_.
        return (scaled - self.scaler.min_[target_index]) / self.scaler.scale_[target_index]

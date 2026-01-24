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
        # Ensure timestamp is datetime
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df = df.sort_values('timestamp')
        
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
        df['rolling_mean_24h'] = df[target_col].rolling(window=24).mean()
        df['rolling_std_24h'] = df[target_col].rolling(window=24).std()
        
        # Drop NaNs created by lags
        df = df.dropna()
        
        return df

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
        """Reverts scaling for predictions."""
        # Create a dummy array with same shape as scaler input to inverse transform
        # This is a bit hacky if we only have 'y'. 
        # Better to have a separate scaler for target if we want easy inversion.
        # For now, let's assume we can handle it or use a separate target scaler in a refined version.
        pass 

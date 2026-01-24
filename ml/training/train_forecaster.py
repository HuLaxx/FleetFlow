"""
Training pipeline for Demand Forecasting model.
Refined for rigorous, unbiased evaluation using TimeSeriesSplit.
"""

import os
import torch
import torch.nn as nn
import torch.optim as optim
import pandas as pd
import numpy as np
from torch.utils.data import DataLoader, TensorDataset
from sklearn.model_selection import TimeSeriesSplit
import structlog
import mlflow

from ml.forecasting.model import DemandForecaster
from ml.forecasting.features import FeatureEngineer
from ml.data.generate_synthetic import generate_synthetic_orders

logger = structlog.get_logger()

def train_model_fold(
    X_train, y_train, X_val, y_val,
    input_size,
    params,
    fold_idx
):
    """
    Trains a single fold.
    """
    # Create DataLoaders
    train_data = TensorDataset(torch.FloatTensor(X_train), torch.FloatTensor(y_train))
    val_data = TensorDataset(torch.FloatTensor(X_val), torch.FloatTensor(y_val))
    
    train_loader = DataLoader(train_data, batch_size=params['batch_size'], shuffle=False) # Shuffle False for time series? Actually within train set it's arguably okay if stateless, but safer False.
    val_loader = DataLoader(val_data, batch_size=params['batch_size'], shuffle=False)
    
    model = DemandForecaster(
        input_size=input_size, 
        hidden_size=params['hidden_size'], 
        num_layers=params['num_layers'], 
        output_size=1,
        dropout=params['dropout']
    )
    
    criterion = nn.MSELoss()
    # Add weight_decay for L2 regularization
    optimizer = optim.Adam(model.parameters(), lr=params['lr'], weight_decay=params['weight_decay'])
    
    best_val_loss = float('inf')
    patience_counter = 0
    patience_limit = 10 # Strict early stopping
    
    for epoch in range(params['epochs']):
        model.train()
        train_loss = 0
        for X_batch, y_batch in train_loader:
            optimizer.zero_grad()
            output = model(X_batch)
            loss = criterion(output.squeeze(), y_batch)
            loss.backward()
            optimizer.step()
            train_loss += loss.item()
        
        # Validation
        model.eval()
        val_loss = 0
        with torch.no_grad():
            for X_batch, y_batch in val_loader:
                output = model(X_batch)
                loss = criterion(output.squeeze(), y_batch)
                val_loss += loss.item()
        
        avg_train_loss = train_loss / len(train_loader)
        avg_val_loss = val_loss / len(val_loader)
        
        # Log to MLflow nested run
        mlflow.log_metrics({
            f"fold_{fold_idx}_train_loss": avg_train_loss,
            f"fold_{fold_idx}_val_loss": avg_val_loss
        }, step=epoch)
        
        # Early Stopping check
        if avg_val_loss < best_val_loss:
            best_val_loss = avg_val_loss
            patience_counter = 0
            # Save refined model (overwrite best)
            # In cross-validation, usually we retrain on full data or ensemble.
            # For now, we save the best model from the LAST fold (most data).
        else:
            patience_counter += 1
            if patience_counter >= patience_limit:
                break
                
    return best_val_loss, model

def train_pipeline(
    data_path: str = None, 
    epochs: int = 100, 
    batch_size: int = 32, 
    lr: float = 0.001,
    hidden_size: int = 64,
    num_layers: int = 2,
    dropout: float = 0.2,
    weight_decay: float = 1e-4
):
    """
    Main training pipeline with TimeSeriesSplit CV.
    """
    logger.info("Starting rigorous training pipeline...")
    
    # 1. Load Data
    if data_path and os.path.exists(data_path):
        df = pd.read_csv(data_path)
    else:
        logger.info("Generating synthetic data...")
        df = generate_synthetic_orders()
    
    df = df[df['zone'] == 'downtown'].copy()
    
    # 2. Feature Engineering
    fe = FeatureEngineer()
    df_features = fe.create_features(df)
    X, y = fe.prepare_data(df_features, sequence_length=24)
    
    # 3. Time Series Cross-Validation
    tscv = TimeSeriesSplit(n_splits=5)
    
    input_size = X.shape[2]
    params = {
        'epochs': epochs,
        'batch_size': batch_size,
        'lr': lr,
        'hidden_size': hidden_size,
        'num_layers': num_layers,
        'dropout': dropout,
        'weight_decay': weight_decay
    }
    
    mlflow.set_experiment("demand_forecasting_rigorous")
    
    with mlflow.start_run():
        mlflow.log_params(params)
        
        fold_scores = []
        
        for i, (train_index, val_index) in enumerate(tscv.split(X)):
            logger.info(f"Starting Fold {i+1}/5...")
            
            X_train, X_val = X[train_index], X[val_index]
            y_train, y_val = y[train_index], y[val_index]
            
            val_loss, model = train_model_fold(
                X_train, y_train, X_val, y_val,
                input_size, params, i+1
            )
            
            fold_scores.append(val_loss)
            logger.info(f"Fold {i+1} Best Val Loss: {val_loss:.4f}")
            
            # Save the model from the last split (trained on most recent data)
            if i == 4:
                torch.save(model.state_dict(), "ml/training/best_models_refined.pth")
                logger.info("Saved refined model checkpoint")

        avg_cv_score = np.mean(fold_scores)
        std_cv_score = np.std(fold_scores)
        
        mlflow.log_metric("avg_cv_val_loss", avg_cv_score)
        mlflow.log_metric("std_cv_val_loss", std_cv_score)
        
        logger.info(f"Cross-Validation Complete. Mean Val Loss: {avg_cv_score:.4f} (+/- {std_cv_score:.4f})")

if __name__ == "__main__":
    train_pipeline()

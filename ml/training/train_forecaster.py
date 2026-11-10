"""
Training pipeline for Demand Forecasting model.
Refined for rigorous, unbiased evaluation using TimeSeriesSplit.
"""

import argparse
import copy
import hashlib
import json
import os
import random
import time
from pathlib import Path
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
from ml.forecasting.validation import scale_fold, forecast_metrics, serializable_scaler
from ml.data.generate_synthetic import generate_synthetic_orders

logger = structlog.get_logger()

def set_determinism(seed: int) -> None:
    """Set random seeds and deterministic flags for reproducible training."""
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False
    try:
        torch.use_deterministic_algorithms(True)
    except Exception:
        pass


def hash_dataframe(df: pd.DataFrame) -> str:
    """Hash a DataFrame for reproducibility tracking."""
    data_bytes = df.to_csv(index=False).encode("utf-8")
    return hashlib.sha256(data_bytes).hexdigest()

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
    best_state = copy.deepcopy(model.state_dict())
    patience_counter = 0
    patience_limit = 10 # Strict early stopping
    
    for epoch in range(params['epochs']):
        model.train()
        train_loss = 0
        for X_batch, y_batch in train_loader:
            optimizer.zero_grad()
            output = model(X_batch)
            loss = criterion(output.squeeze(-1), y_batch)
            loss.backward()
            optimizer.step()
            train_loss += loss.item()
        
        # Validation
        model.eval()
        val_loss = 0
        with torch.no_grad():
            for X_batch, y_batch in val_loader:
                output = model(X_batch)
                loss = criterion(output.squeeze(-1), y_batch)
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
            best_state = copy.deepcopy(model.state_dict())
            patience_counter = 0
            # Save refined model (overwrite best)
            # In cross-validation, usually we retrain on full data or ensemble.
            # For now, we save the best model from the LAST fold (most data).
        else:
            patience_counter += 1
            if patience_counter >= patience_limit:
                break
                
    # Restore the best epoch rather than returning the final epoch.
    model.load_state_dict(best_state)
    return best_val_loss, model

def train_pipeline(
    data_path: str = None, 
    synthetic_start_date: str = "2023-01-01",
    synthetic_end_date: str = "2023-12-31",
    epochs: int = 100, 
    batch_size: int = 32, 
    lr: float = 0.001,
    hidden_size: int = 64,
    num_layers: int = 2,
    dropout: float = 0.2,
    weight_decay: float = 1e-4,
    seed: int = 42,
):
    """
    Main training pipeline with TimeSeriesSplit CV.
    """
    logger.info("Starting rigorous training pipeline...")
    set_determinism(seed)
    start_ts = time.time()
    
    # 1. Load Data
    if data_path and os.path.exists(data_path):
        df = pd.read_csv(data_path)
    else:
        logger.info("Generating synthetic data...")
        df = generate_synthetic_orders(
            start_date=synthetic_start_date,
            end_date=synthetic_end_date,
            seed=seed,
        )
    
    df = df[df['zone'] == 'downtown'].copy()
    data_hash = hash_dataframe(df)
    
    # 2. Feature Engineering
    fe = FeatureEngineer()
    df_features = fe.create_features(df)
    # Split raw chronological sequences before fitting ANY preprocessing.
    X, y = fe.prepare_raw_sequences(df_features, sequence_length=24)
    
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
    
    tracking_uri = os.getenv("MLFLOW_TRACKING_URI")
    if tracking_uri:
        mlflow.set_tracking_uri(tracking_uri)

    experiment_name = os.getenv("MLFLOW_EXPERIMENT", "demand_forecasting_rigorous")
    mlflow.set_experiment(experiment_name)
    
    with mlflow.start_run():
        mlflow.log_params({**params, "seed": seed})
        mlflow.set_tag("data_hash", data_hash)
        
        fold_scores = []
        fold_evaluations = []
        
        for i, (train_index, val_index) in enumerate(tscv.split(X)):
            logger.info(f"Starting Fold {i+1}/5...")
            
            X_train_raw, X_val_raw = X[train_index], X[val_index]
            y_train_raw, y_val_raw = y[train_index], y[val_index]
            X_train, y_train, X_val, y_val, feature_scaler, target_scaler = scale_fold(
                X_train_raw, y_train_raw, X_val_raw, y_val_raw
            )

            val_loss, model = train_model_fold(
                X_train, y_train, X_val, y_val,
                input_size, params, i+1
            )
            
            fold_scores.append(val_loss)
            model.eval()
            with torch.no_grad():
                scaled_predictions = model(
                    torch.as_tensor(X_val, dtype=torch.float32)
                ).squeeze(-1).cpu().numpy()
            predictions_orders = target_scaler.inverse_transform(
                scaled_predictions.reshape(-1, 1)
            ).reshape(-1)
            target_index = fe.feature_columns.index("order_count")
            naive_orders = X_val_raw[:, -1, target_index]
            quality = forecast_metrics(y_val_raw, predictions_orders, naive_orders)
            fold_evaluations.append(quality)
            fold_mlflow_metrics = {
                f"fold_{i+1}_model_mae_orders": quality["model_mae_orders"],
                f"fold_{i+1}_naive_mae_orders": quality["naive_mae_orders"],
                f"fold_{i+1}_model_rmse_orders": quality["model_rmse_orders"],
            }
            if quality["skill_vs_naive"] is not None:
                fold_mlflow_metrics[f"fold_{i+1}_skill_vs_naive"] = quality["skill_vs_naive"]
            mlflow.log_metrics(fold_mlflow_metrics)
            logger.info(
                "Fold evaluated against naive baseline",
                fold=i + 1,
                **quality
            )
            
            # Save the model from the last split (trained on most recent data)
            if i == 4:
                artifact_dir = Path("ml/training/artifacts")
                artifact_dir.mkdir(parents=True, exist_ok=True)
                artifact_path = artifact_dir / f"best_model_seed{seed}.pth"
                torch.save(model.state_dict(), artifact_path)
                mlflow.log_artifact(str(artifact_path))
                logger.info("Saved refined model checkpoint", path=str(artifact_path))

        avg_cv_score = np.mean(fold_scores)
        std_cv_score = np.std(fold_scores)
        
        mlflow.log_metric("avg_cv_val_loss", avg_cv_score)
        mlflow.log_metric("std_cv_val_loss", std_cv_score)
        mlflow.log_metric("training_time_sec", time.time() - start_ts)
        
        logger.info(f"Cross-Validation Complete. Mean Val Loss: {avg_cv_score:.4f} (+/- {std_cv_score:.4f})")

        metrics_summary = {
            "run_id": mlflow.active_run().info.run_id,
            "experiment": experiment_name,
            "seed": seed,
            "data_path": data_path or "synthetic",
            "synthetic_start_date": synthetic_start_date,
            "synthetic_end_date": synthetic_end_date,
            "data_hash": data_hash,
            "params": params,
            "fold_scores": [float(score) for score in fold_scores],
            "avg_cv_val_loss": float(avg_cv_score),
            "std_cv_val_loss": float(std_cv_score),
            "training_time_sec": float(time.time() - start_ts),
        }

        default_dir = Path(__file__).resolve().parent / "metrics"
        metrics_dir = Path(os.getenv("ML_METRICS_DIR", str(default_dir)))
        metrics_dir.mkdir(parents=True, exist_ok=True)
        metrics_path = metrics_dir / f"metrics_seed{seed}_{data_hash[:8]}.json"
        metrics_path.write_text(json.dumps(metrics_summary, indent=2), encoding="utf-8")
        mlflow.log_artifact(str(metrics_path))

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train demand forecasting model")
    parser.add_argument("--data-path", default=None)
    parser.add_argument("--start-date", default="2023-01-01")
    parser.add_argument("--end-date", default="2023-12-31")
    parser.add_argument("--epochs", type=int, default=100)
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument("--lr", type=float, default=0.001)
    parser.add_argument("--hidden-size", type=int, default=64)
    parser.add_argument("--num-layers", type=int, default=2)
    parser.add_argument("--dropout", type=float, default=0.2)
    parser.add_argument("--weight-decay", type=float, default=1e-4)
    parser.add_argument("--seed", type=int, default=42)
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    train_pipeline(
        data_path=args.data_path,
        synthetic_start_date=args.start_date,
        synthetic_end_date=args.end_date,
        epochs=args.epochs,
        batch_size=args.batch_size,
        lr=args.lr,
        hidden_size=args.hidden_size,
        num_layers=args.num_layers,
        dropout=args.dropout,
        weight_decay=args.weight_decay,
        seed=args.seed,
    )

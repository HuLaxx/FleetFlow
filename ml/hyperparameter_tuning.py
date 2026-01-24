"""
Rigorous Hyperparameter Tuning using Optuna.
Extended search space and TimeSeriesSplit validation.
"""

import optuna
import torch
import torch.nn as nn
from sklearn.model_selection import TimeSeriesSplit
import numpy as np

from ml.forecasting.model import DemandForecaster
from ml.forecasting.features import FeatureEngineer
from ml.data.generate_synthetic import generate_synthetic_orders

def objective(trial):
    # Extended Hyperparameter Search Space
    hidden_size = trial.suggest_int('hidden_size', 32, 256)
    num_layers = trial.suggest_int('num_layers', 1, 4)
    lr = trial.suggest_loguniform('lr', 1e-5, 1e-2)
    dropout = trial.suggest_float('dropout', 0.0, 0.5)
    weight_decay = trial.suggest_loguniform('weight_decay', 1e-6, 1e-3)
    batch_size = trial.suggest_categorical('batch_size', [16, 32, 64])
    
    # Load Data
    df = generate_synthetic_orders()
    df = df[df['zone'] == 'downtown']
    
    fe = FeatureEngineer()
    df_features = fe.create_features(df)
    X, y = fe.prepare_data(df_features)
    
    # Rigorous TimeSeriesSplit (3 splits for speed during tuning, 5 for final)
    tscv = TimeSeriesSplit(n_splits=3)
    fold_scores = []
    
    input_size = X.shape[2]
    
    for train_index, val_index in tscv.split(X):
        # Data prep
        X_train, X_val = X[train_index], X[val_index]
        y_train, y_val = y[train_index], y[val_index]
        
        X_train_t = torch.FloatTensor(X_train)
        y_train_t = torch.FloatTensor(y_train)
        X_val_t = torch.FloatTensor(X_val)
        y_val_t = torch.FloatTensor(y_val)
        
        # Model initialization
        model = DemandForecaster(
            input_size=input_size, 
            hidden_size=hidden_size, 
            num_layers=num_layers, 
            output_size=1, 
            dropout=dropout
        )
        
        criterion = nn.MSELoss()
        optimizer = torch.optim.Adam(model.parameters(), lr=lr, weight_decay=weight_decay)
        
        # Short training loop for tuning
        epochs = 15 # Reduced epochs for faster trials
        
        for epoch in range(epochs):
            model.train()
            optimizer.zero_grad()
            output = model(X_train_t)
            loss = criterion(output.squeeze(), y_train_t)
            loss.backward()
            optimizer.step()
            
        # Validation
        model.eval()
        with torch.no_grad():
            val_output = model(X_val_t)
            val_loss = criterion(val_output.squeeze(), y_val_t)
            fold_scores.append(val_loss.item())
            
    # Return mean validation loss across folds
    return np.mean(fold_scores)

if __name__ == "__main__":
    # Increased trials for thorough search
    study = optuna.create_study(direction='minimize')
    print("Starting extensive hyperparameter search (50 trials)...")
    study.optimize(objective, n_trials=50) 
    
    print("Best trial:")
    trial = study.best_trial
    print(f"  Value (Mean MSE): {trial.value:.6f}")
    print("  Params: ")
    for key, value in trial.params.items():
        print(f"    {key}: {value}")

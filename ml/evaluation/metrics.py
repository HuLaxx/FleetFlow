"""
Evaluation Metrics and Reporting.
"""

import numpy as np
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
import matplotlib.pyplot as plt
import seaborn as sns

def evaluate_predictions(y_true, y_pred):
    """
    Calculates regression metrics.
    """
    mae = mean_absolute_error(y_true, y_pred)
    mse = mean_squared_error(y_true, y_pred)
    rmse = np.sqrt(mse)
    r2 = r2_score(y_true, y_pred)
    
    # MAPE (Mean Absolute Percentage Error) - careful with zeros
    mask = y_true != 0
    mape = np.mean(np.abs((y_true[mask] - y_pred[mask]) / y_true[mask])) * 100
    
    return {
        "mae": mae,
        "rmse": rmse,
        "r2": r2,
        "mape": mape
    }

def plot_results(y_true, y_pred, save_path="ml/evaluation/results.png"):
    """
    Plots actual vs predicted values.
    """
    plt.figure(figsize=(12, 6))
    plt.plot(y_true, label='Actual')
    plt.plot(y_pred, label='Predicted', alpha=0.7)
    plt.title("Demand Forecast: Actual vs Predicted")
    plt.xlabel("Time Steps")
    plt.ylabel("Order Volume")
    plt.legend()
    plt.grid(True)
    plt.savefig(save_path)
    plt.close()

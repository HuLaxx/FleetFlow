"""
FleetFlow MLflow Integration

Experiment tracking and model registry for:
- Demand forecasting models
- Route optimization benchmarks
- Model versioning and deployment
"""

import os
import json
import pickle
from datetime import datetime
from typing import Any, Dict, Optional, List
from dataclasses import dataclass, asdict
import logging

try:
    import mlflow
    from mlflow.tracking import MlflowClient
    from mlflow.models.signature import infer_signature
except ImportError:
    mlflow = None

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


@dataclass
class ExperimentConfig:
    """MLflow experiment configuration."""
    tracking_uri: str = "sqlite:///mlflow.db"
    artifact_location: str = "./mlflow-artifacts"
    experiment_name: str = "fleetflow"


class MLflowTracker:
    """
    MLflow experiment tracker for FleetFlow models.
    
    Features:
    - Automatic experiment creation
    - Model logging with signatures
    - Metric and parameter tracking
    - Artifact storage
    - Model registry integration
    """
    
    def __init__(self, config: Optional[ExperimentConfig] = None):
        if mlflow is None:
            raise ImportError("MLflow not installed. Run: pip install mlflow")
        
        self.config = config or ExperimentConfig()
        self._setup_mlflow()
        self.client = MlflowClient()
    
    def _setup_mlflow(self) -> None:
        """Initialize MLflow tracking."""
        mlflow.set_tracking_uri(self.config.tracking_uri)
        
        # Create or get experiment
        experiment = mlflow.get_experiment_by_name(self.config.experiment_name)
        if experiment is None:
            mlflow.create_experiment(
                self.config.experiment_name,
                artifact_location=self.config.artifact_location
            )
        mlflow.set_experiment(self.config.experiment_name)
        
        logger.info(f"MLflow tracking URI: {self.config.tracking_uri}")
    
    def start_run(
        self,
        run_name: Optional[str] = None,
        tags: Optional[Dict[str, str]] = None
    ) -> str:
        """
        Start a new MLflow run.
        
        Returns:
            Run ID
        """
        run = mlflow.start_run(run_name=run_name, tags=tags)
        return run.info.run_id
    
    def end_run(self) -> None:
        """End the current run."""
        mlflow.end_run()
    
    def log_params(self, params: Dict[str, Any]) -> None:
        """Log parameters."""
        for key, value in params.items():
            mlflow.log_param(key, value)
    
    def log_metrics(self, metrics: Dict[str, float], step: Optional[int] = None) -> None:
        """Log metrics."""
        for key, value in metrics.items():
            mlflow.log_metric(key, value, step=step)
    
    def log_model(
        self,
        model: Any,
        artifact_path: str,
        model_type: str = "sklearn",
        input_example: Optional[Any] = None,
        signature: Optional[Any] = None,
        registered_model_name: Optional[str] = None
    ) -> str:
        """
        Log a model to MLflow.
        
        Args:
            model: The model object
            artifact_path: Path within artifacts
            model_type: 'sklearn', 'tensorflow', 'pytorch', 'prophet'
            input_example: Example input for signature
            signature: Model signature
            registered_model_name: Name for model registry
            
        Returns:
            Model URI
        """
        if model_type == "sklearn":
            model_info = mlflow.sklearn.log_model(
                model,
                artifact_path,
                input_example=input_example,
                signature=signature,
                registered_model_name=registered_model_name
            )
        elif model_type == "tensorflow":
            model_info = mlflow.tensorflow.log_model(
                model,
                artifact_path,
                input_example=input_example,
                signature=signature,
                registered_model_name=registered_model_name
            )
        elif model_type == "prophet":
            # Prophet uses pyfunc
            model_info = mlflow.pyfunc.log_model(
                artifact_path,
                python_model=ProphetWrapper(model),
                registered_model_name=registered_model_name
            )
        else:
            # Generic pickle
            mlflow.log_artifact(self._save_pickle(model, artifact_path))
            model_info = None
        
        return model_info.model_uri if model_info else artifact_path
    
    def _save_pickle(self, obj: Any, name: str) -> str:
        """Save object as pickle and return path."""
        path = f"/tmp/{name}.pkl"
        with open(path, 'wb') as f:
            pickle.dump(obj, f)
        return path
    
    def log_artifact(self, local_path: str, artifact_path: Optional[str] = None) -> None:
        """Log an artifact file."""
        mlflow.log_artifact(local_path, artifact_path)
    
    def log_dict(self, data: Dict, artifact_file: str) -> None:
        """Log a dictionary as JSON artifact."""
        mlflow.log_dict(data, artifact_file)
    
    def log_figure(self, figure: Any, artifact_file: str) -> None:
        """Log a matplotlib figure."""
        mlflow.log_figure(figure, artifact_file)
    
    def get_best_run(
        self,
        metric: str,
        maximize: bool = False
    ) -> Optional[Dict[str, Any]]:
        """
        Get the best run based on a metric.
        
        Args:
            metric: Metric name
            maximize: True for higher is better
            
        Returns:
            Best run info
        """
        experiment = mlflow.get_experiment_by_name(self.config.experiment_name)
        if experiment is None:
            return None
        
        order = "DESC" if maximize else "ASC"
        runs = self.client.search_runs(
            experiment_ids=[experiment.experiment_id],
            order_by=[f"metrics.{metric} {order}"],
            max_results=1
        )
        
        if not runs:
            return None
        
        run = runs[0]
        return {
            "run_id": run.info.run_id,
            "metrics": run.data.metrics,
            "params": run.data.params,
        }
    
    def load_model(self, model_uri: str) -> Any:
        """Load a model from MLflow."""
        return mlflow.pyfunc.load_model(model_uri)
    
    def register_model(
        self,
        model_uri: str,
        name: str,
        tags: Optional[Dict[str, str]] = None
    ) -> str:
        """
        Register a model in the model registry.
        
        Returns:
            Model version
        """
        result = mlflow.register_model(model_uri, name)
        
        if tags:
            for key, value in tags.items():
                self.client.set_model_version_tag(
                    name, result.version, key, value
                )
        
        return result.version
    
    def transition_model_stage(
        self,
        name: str,
        version: str,
        stage: str  # "Staging", "Production", "Archived"
    ) -> None:
        """Transition model to a new stage."""
        self.client.transition_model_version_stage(
            name=name,
            version=version,
            stage=stage
        )


if mlflow is not None:
    class ProphetWrapper(mlflow.pyfunc.PythonModel):
        """Wrapper for Prophet models in MLflow."""
        
        def __init__(self, model):
            self.model = model
        
        def predict(self, context, model_input):
            if isinstance(model_input, pd.DataFrame):
                future = model_input
            else:
                future = self.model.make_future_dataframe(periods=24, freq='H')
            
            forecast = self.model.predict(future)
            return forecast[['ds', 'yhat', 'yhat_lower', 'yhat_upper']]
else:
    class ProphetWrapper:
        """Placeholder when MLflow is not installed."""
        
        def __init__(self, *args, **kwargs):
            raise ImportError("MLflow not installed. Run: pip install mlflow")
        
        def predict(self, *args, **kwargs):
            raise ImportError("MLflow not installed. Run: pip install mlflow")


class ForecastingExperiment:
    """
    MLflow experiment runner for forecasting models.
    """
    
    def __init__(self, tracker: Optional[MLflowTracker] = None):
        self.tracker = tracker or MLflowTracker()
    
    def run_prophet_experiment(
        self,
        train_data: pd.DataFrame,
        test_data: pd.DataFrame,
        params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Run a Prophet forecasting experiment.
        
        Args:
            train_data: Training data with 'ds' and 'y' columns
            test_data: Test data for evaluation
            params: Prophet parameters
            
        Returns:
            Experiment results
        """
        from prophet import Prophet
        
        run_name = f"prophet_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.tracker.start_run(
            run_name=run_name,
            tags={"model_type": "prophet", "task": "forecasting"}
        )
        
        try:
            # Log parameters
            self.tracker.log_params(params)
            
            # Train model
            model = Prophet(**params)
            model.fit(train_data)
            
            # Predict on test
            forecast = model.predict(test_data[['ds']])
            
            # Calculate metrics
            y_true = test_data['y'].values
            y_pred = forecast['yhat'].values[:len(y_true)]
            
            mae = np.mean(np.abs(y_true - y_pred))
            rmse = np.sqrt(np.mean((y_true - y_pred) ** 2))
            mape = np.mean(np.abs((y_true - y_pred) / (y_true + 1e-8))) * 100
            
            metrics = {
                "mae": mae,
                "rmse": rmse,
                "mape": mape,
            }
            self.tracker.log_metrics(metrics)
            
            # Log model
            model_uri = self.tracker.log_model(
                model,
                "prophet_model",
                model_type="prophet",
                registered_model_name="fleetflow-demand-prophet"
            )
            
            return {
                "run_id": mlflow.active_run().info.run_id,
                "metrics": metrics,
                "model_uri": model_uri
            }
        
        finally:
            self.tracker.end_run()
    
    def run_lstm_experiment(
        self,
        train_data: np.ndarray,
        test_data: np.ndarray,
        params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Run an LSTM forecasting experiment.
        """
        import tensorflow as tf
        from tensorflow.keras.models import Sequential
        from tensorflow.keras.layers import LSTM, Dense, Dropout
        from tensorflow.keras.callbacks import EarlyStopping
        
        run_name = f"lstm_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.tracker.start_run(
            run_name=run_name,
            tags={"model_type": "lstm", "task": "forecasting"}
        )
        
        try:
            self.tracker.log_params(params)
            
            seq_len = params.get("sequence_length", 24)
            units = params.get("units", 64)
            epochs = params.get("epochs", 50)
            
            # Normalize
            mean, std = train_data.mean(), train_data.std()
            train_norm = (train_data - mean) / (std + 1e-8)
            test_norm = (test_data - mean) / (std + 1e-8)
            
            # Create sequences
            def create_sequences(data, seq_len):
                X, y = [], []
                for i in range(len(data) - seq_len):
                    X.append(data[i:i+seq_len])
                    y.append(data[i+seq_len])
                return np.array(X), np.array(y)
            
            X_train, y_train = create_sequences(train_norm, seq_len)
            X_train = X_train.reshape(-1, seq_len, 1)
            
            # Build model
            model = Sequential([
                LSTM(units, input_shape=(seq_len, 1), return_sequences=True),
                Dropout(0.2),
                LSTM(units // 2),
                Dropout(0.2),
                Dense(1)
            ])
            model.compile(optimizer='adam', loss='mse', metrics=['mae'])
            
            # Train with MLflow autolog
            mlflow.tensorflow.autolog()
            
            history = model.fit(
                X_train, y_train,
                epochs=epochs,
                batch_size=32,
                validation_split=0.2,
                callbacks=[EarlyStopping(patience=10, restore_best_weights=True)],
                verbose=0
            )
            
            # Evaluate
            X_test, y_test = create_sequences(test_norm, seq_len)
            X_test = X_test.reshape(-1, seq_len, 1)
            y_pred = model.predict(X_test, verbose=0)
            
            # Denormalize
            y_test_orig = y_test * std + mean
            y_pred_orig = y_pred.flatten() * std + mean
            
            mae = np.mean(np.abs(y_test_orig - y_pred_orig))
            rmse = np.sqrt(np.mean((y_test_orig - y_pred_orig) ** 2))
            
            metrics = {"test_mae": mae, "test_rmse": rmse}
            self.tracker.log_metrics(metrics)
            
            return {
                "run_id": mlflow.active_run().info.run_id,
                "metrics": metrics,
                "final_train_loss": history.history['loss'][-1]
            }
        
        finally:
            self.tracker.end_run()


class OptimizationExperiment:
    """
    MLflow experiment runner for route optimization.
    """
    
    def __init__(self, tracker: Optional[MLflowTracker] = None):
        self.tracker = tracker or MLflowTracker()
    
    def benchmark_algorithms(
        self,
        problem_sizes: List[int],
        algorithms: List[str]
    ) -> pd.DataFrame:
        """
        Benchmark optimization algorithms across problem sizes.
        
        Returns:
            DataFrame with benchmark results
        """
        from ml.optimization import Location, Order, Vehicle, optimize_routes
        import time
        
        results = []
        
        for n_orders in problem_sizes:
            # Generate random problem
            depot = Location(id="depot", latitude=40.7128, longitude=-74.0060)
            
            orders = [
                Order(
                    id=f"order_{i}",
                    location=Location(
                        id=f"loc_{i}",
                        latitude=40.7128 + np.random.uniform(-0.1, 0.1),
                        longitude=-74.0060 + np.random.uniform(-0.1, 0.1)
                    ),
                    demand_kg=np.random.uniform(5, 50)
                )
                for i in range(n_orders)
            ]
            
            vehicles = [
                Vehicle(id=f"vehicle_{i}", capacity_kg=500)
                for i in range(max(1, n_orders // 10))
            ]
            
            for algorithm in algorithms:
                run_name = f"benchmark_{algorithm}_{n_orders}orders"
                self.tracker.start_run(
                    run_name=run_name,
                    tags={"task": "optimization_benchmark", "algorithm": algorithm}
                )
                
                try:
                    self.tracker.log_params({
                        "algorithm": algorithm,
                        "n_orders": n_orders,
                        "n_vehicles": len(vehicles),
                    })
                    
                    start = time.time()
                    result = optimize_routes(depot, orders, vehicles, algorithm=algorithm)
                    elapsed = (time.time() - start) * 1000
                    
                    metrics = {
                        "total_distance_km": result.total_distance_km,
                        "computation_time_ms": elapsed,
                        "routes_created": len(result.routes),
                        "orders_assigned": len(orders) - len(result.unassigned_orders),
                        "assignment_rate": result.score,
                    }
                    self.tracker.log_metrics(metrics)
                    
                    results.append({
                        "algorithm": algorithm,
                        "n_orders": n_orders,
                        **metrics
                    })
                
                finally:
                    self.tracker.end_run()
        
        return pd.DataFrame(results)

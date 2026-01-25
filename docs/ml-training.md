# ML Training Metrics

FleetFlow training runs log metrics to MLflow and write a local metrics summary JSON for deterministic runs.

## Metrics Output
- Local summary file: `ml/training/metrics/metrics_seed<SEED>_<HASH>.json`
- MLflow tracking (default): `http://localhost:5001`

## Example Command
```bash
python ml/training/train_forecaster.py --seed 42 --epochs 5
```

## Metrics Captured
- `fold_*_train_loss`, `fold_*_val_loss` (per epoch)
- `avg_cv_val_loss`, `std_cv_val_loss`
- `training_time_sec`
- `data_hash` (dataset fingerprint)

## Configure
```
MLFLOW_TRACKING_URI=http://localhost:5001
MLFLOW_EXPERIMENT=demand_forecasting_rigorous
ML_METRICS_DIR=ml/training/metrics
```
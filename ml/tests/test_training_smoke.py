import pytest

pytest.importorskip("mlflow")
pytest.importorskip("torch")

from ml.data.generate_synthetic import generate_synthetic_orders
from ml.training.train_forecaster import train_pipeline, hash_dataframe


@pytest.mark.slow
def test_training_pipeline_smoke(tmp_path, monkeypatch):
    df = generate_synthetic_orders(
        start_date="2023-01-01",
        end_date="2023-01-15",
        seed=7,
    )
    data_path = tmp_path / "training_data.csv"
    df.to_csv(data_path, index=False)

    monkeypatch.setenv("MLFLOW_TRACKING_URI", tmp_path.as_uri())
    monkeypatch.setenv("MLFLOW_EXPERIMENT", "test_deterministic")
    monkeypatch.setenv("ML_METRICS_DIR", str(tmp_path))

    train_pipeline(
        data_path=str(data_path),
        epochs=1,
        batch_size=8,
        lr=0.001,
        hidden_size=4,
        num_layers=1,
        dropout=0.0,
        weight_decay=0.0,
        seed=7,
    )

    filtered = df[df["zone"] == "downtown"].copy()
    data_hash = hash_dataframe(filtered)
    metrics_file = tmp_path / f"metrics_seed7_{data_hash[:8]}.json"
    assert metrics_file.exists()
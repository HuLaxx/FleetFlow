import pandas as pd

from ml.data.generate_synthetic import generate_synthetic_orders


def test_generate_synthetic_orders_deterministic():
    df_a = generate_synthetic_orders(seed=123)
    df_b = generate_synthetic_orders(seed=123)

    assert df_a.shape == df_b.shape
    assert df_a.head(10).equals(df_b.head(10))

    summary_a = df_a.groupby("zone")["order_count"].sum().sort_index()
    summary_b = df_b.groupby("zone")["order_count"].sum().sort_index()
    pd.testing.assert_series_equal(summary_a, summary_b)
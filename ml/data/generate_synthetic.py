"""
Synthetic Data Generation for training ML models.
"""

import argparse
from datetime import datetime, timedelta
from typing import Optional

import numpy as np
import pandas as pd

def generate_synthetic_orders(
    start_date: str = '2023-01-01',
    end_date: str = '2023-12-31',
    zones: list = ['downtown', 'suburbs_north', 'suburbs_south', 'industrial'],
    seed: Optional[int] = None,
):
    """
    Generates synthetic hourly order volume data.
    """
    np_rng = np.random.default_rng(seed)
    date_range = pd.date_range(start=start_date, end=end_date, freq='H')
    data = []
    
    for date in date_range:
        for zone in zones:
            # Base volume depends on zone
            base_volume = {
                'downtown': 50,
                'suburbs_north': 30,
                'suburbs_south': 25,
                'industrial': 15
            }[zone]
            
            # Seasonality and Trends
            
            # 1. Daily Seasonality (Hour of day)
            hour = date.hour
            if zone == 'downtown':
                # Peak at lunch (11-13) and dinner (18-20)
                if 11 <= hour <= 13: hour_factor = 1.5
                elif 18 <= hour <= 20: hour_factor = 1.4
                elif 1 <= hour <= 5: hour_factor = 0.1
                else: hour_factor = 0.8
            else: 
                # Suburbs peak in evening
                if 17 <= hour <= 21: hour_factor = 1.6
                elif 1 <= hour <= 6: hour_factor = 0.05
                else: hour_factor = 0.6
                
            # 2. Weekly Seasonality (Day of week)
            dow = date.dayofweek
            if zone == 'industrial':
                # Weekdays high, weekends low
                dow_factor = 1.2 if dow < 5 else 0.2
            else:
                # Weekends high for residential
                dow_factor = 1.3 if dow >= 5 else 0.9
                
            # 3. Yearly Trend + Noise
            day_of_year = date.dayofyear
            trend = 1 + (day_of_year / 365) * 0.2 # 20% growth over year
            
            noise = np_rng.normal(1, 0.2)
            
            volume = max(0, int(base_volume * hour_factor * dow_factor * trend * noise))
            
            data.append({
                'timestamp': date,
                'zone': zone,
                'order_count': volume,
                'hour': hour,
                'day_of_week': dow,
                'month': date.month,
                'is_weekend': 1 if dow >= 5 else 0
            })
            
    return pd.DataFrame(data)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate synthetic orders dataset")
    parser.add_argument("--start-date", default="2023-01-01")
    parser.add_argument("--end-date", default="2023-12-31")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    print("Generating synthetic data...")
    df = generate_synthetic_orders(
        start_date=args.start_date,
        end_date=args.end_date,
        seed=args.seed,
    )
    df.to_csv("ml/data/synthetic_orders.csv", index=False)
    print(f"Generated {len(df)} rows. Saved to ml/data/synthetic_orders.csv")

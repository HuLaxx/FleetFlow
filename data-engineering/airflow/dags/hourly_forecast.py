"""
FleetFlow - Hourly Demand Forecasting DAG

Runs hourly to:
1. Aggregate recent order data
2. Update demand forecasting model
3. Generate predictions for next 24 hours
4. Update driver positioning recommendations
"""

from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.bash import BashOperator
from airflow.sensors.time_delta import TimeDeltaSensor
import json


default_args = {
    'owner': 'fleetflow',
    'depends_on_past': False,
    'retries': 2,
    'retry_delay': timedelta(minutes=2),
}


def aggregate_order_patterns(**context):
    """Aggregate order patterns by zone and hour."""
    from sqlalchemy import create_engine, text
    import os
    
    engine = create_engine(os.environ.get('DATABASE_URL'))
    
    with engine.connect() as conn:
        # Get order patterns from last 7 days
        result = conn.execute(text("""
            SELECT 
                (EXTRACT(ISODOW FROM delivery_date) - 1) as day_of_week,
                EXTRACT(HOUR FROM time_window_start) as hour,
                COUNT(*) as order_count,
                AVG(total_weight_kg) as avg_weight,
                AVG(priority) as avg_priority
            FROM orders
            WHERE created_at >= NOW() - INTERVAL '7 days'
            GROUP BY 
                EXTRACT(DOW FROM delivery_date),
                EXTRACT(HOUR FROM time_window_start)
            ORDER BY day_of_week, hour
        """))
        
        patterns = [dict(row) for row in result]
    
    context['ti'].xcom_push(key='order_patterns', value=patterns)
    return len(patterns)


def generate_forecast(**context):
    """Generate demand forecast for next 24 hours."""
    import numpy as np
    
    patterns = context['ti'].xcom_pull(key='order_patterns')
    
    if not patterns:
        return {'status': 'no_data'}
    
    # Simple moving average forecast (production would use Prophet/LSTM)
    now = datetime.now()
    predictions = []
    
    for hour_offset in range(24):
        target_time = now + timedelta(hours=hour_offset)
        day_of_week = target_time.weekday()
        hour = target_time.hour
        
        # Find matching patterns
        matching = [
            p for p in patterns 
            if p['day_of_week'] == day_of_week and p['hour'] == hour
        ]
        
        if matching:
            avg_orders = np.mean([p['order_count'] for p in matching])
        else:
            avg_orders = 5  # Default
        
        predictions.append({
            'timestamp': target_time.isoformat(),
            'hour': hour,
            'predicted_orders': round(avg_orders, 1),
            'confidence': 0.8,
        })
    
    context['ti'].xcom_push(key='forecast', value=predictions)
    return {'predictions': len(predictions)}


def update_positioning(**context):
    """Generate driver positioning recommendations."""
    forecast = context['ti'].xcom_pull(key='forecast')
    
    if not forecast:
        return {'status': 'no_forecast'}
    
    # Identify peak hours (>10 predicted orders)
    peak_hours = [
        p for p in forecast 
        if p['predicted_orders'] > 10
    ]
    
    recommendations = []
    for peak in peak_hours[:5]:  # Top 5 peaks
        recommendations.append({
            'time': peak['timestamp'],
            'predicted_demand': peak['predicted_orders'],
            'recommended_drivers': int(peak['predicted_orders'] / 5) + 1,
            'zone': 'high_demand',
        })
    
    # Log recommendations
    print(f"Generated {len(recommendations)} positioning recommendations")
    
    return {'recommendations': len(recommendations)}


# Create DAG
with DAG(
    dag_id='hourly_demand_forecast',
    default_args=default_args,
    description='Hourly demand forecasting and driver positioning',
    schedule_interval='0 * * * *',  # Every hour
    start_date=datetime(2024, 1, 1),
    catchup=False,
    tags=['fleetflow', 'forecasting', 'ml'],
) as dag:
    
    # Aggregate patterns
    aggregate = PythonOperator(
        task_id='aggregate_order_patterns',
        python_callable=aggregate_order_patterns,
    )
    
    # Generate forecast
    forecast = PythonOperator(
        task_id='generate_forecast',
        python_callable=generate_forecast,
    )
    
    # Update positioning
    positioning = PythonOperator(
        task_id='update_positioning',
        python_callable=update_positioning,
    )
    
    aggregate >> forecast >> positioning

"""
FleetFlow - Daily Route Optimization DAG

Runs daily to:
1. Extract pending orders for the next day
2. Run dbt transformations
3. Execute route optimization
4. Assign routes to drivers
"""

from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.bash import BashOperator
from airflow.providers.http.operators.http import SimpleHttpOperator
from airflow.providers.postgres.operators.postgres import PostgresOperator
from airflow.utils.task_group import TaskGroup
import json


# Default arguments
default_args = {
    'owner': 'fleetflow',
    'depends_on_past': False,
    'email_on_failure': True,
    'email_on_retry': False,
    'retries': 3,
    'retry_delay': timedelta(minutes=5),
    'execution_timeout': timedelta(hours=2),
}


def extract_pending_orders(**context):
    """Extract orders pending for tomorrow."""
    from sqlalchemy import create_engine, text
    import os
    
    engine = create_engine(os.environ.get('DATABASE_URL'))
    
    tomorrow = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
    
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT 
                o.id,
                o.order_number,
                o.customer_id,
                o.depot_id,
                o.total_weight_kg,
                o.time_window_start,
                o.time_window_end,
                c.address,
                ST_Y(c.location::geometry) AS latitude,
                ST_X(c.location::geometry) AS longitude,
                o.priority
            FROM orders o
            JOIN customers c ON o.customer_id = c.id
            WHERE o.delivery_date = :tomorrow
              AND o.status = 'pending'
            ORDER BY o.priority DESC, o.time_window_start
        """), {'tomorrow': tomorrow})
        
        orders = [dict(row) for row in result]
    
    context['ti'].xcom_push(key='pending_orders', value=orders)
    return len(orders)


def get_available_drivers(**context):
    """Get drivers available for tomorrow's routes."""
    from sqlalchemy import create_engine, text
    import os
    
    engine = create_engine(os.environ.get('DATABASE_URL'))
    
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT 
                d.id as driver_id,
                d.employee_id,
                d.first_name || ' ' || d.last_name as name,
                v.id as vehicle_id,
                v.capacity_kg
            FROM drivers d
            JOIN vehicles v ON v.current_driver_id = d.id
            WHERE d.status != 'offline'
              AND v.status = 'available'
        """))
        
        drivers = [dict(row) for row in result]
    
    context['ti'].xcom_push(key='available_drivers', value=drivers)
    return len(drivers)


def run_optimization(**context):
    """Run route optimization via API."""
    import requests
    
    orders = context['ti'].xcom_pull(key='pending_orders')
    drivers = context['ti'].xcom_pull(key='available_drivers')
    
    if not orders:
        return {'status': 'no_orders', 'routes': []}
    
    # Call optimization API
    response = requests.post(
        'http://backend:8000/api/v1/optimization/optimize',
        json={
            'orders': [
                {
                    'id': str(o['id']),
                    'latitude': o['latitude'],
                    'longitude': o['longitude'],
                    'weight_kg': float(o['total_weight_kg']),
                    'priority': o['priority'],
                }
                for o in orders
            ],
            'vehicles': [
                {
                    'id': str(d['vehicle_id']),
                    'capacity_kg': float(d['capacity_kg']),
                }
                for d in drivers
            ],
            'depot': {
                'id': '00000000-0000-0000-0000-000000000001',
                'latitude': 40.7128,
                'longitude': -74.0060,
                'name': 'NYC Main Hub',
            },
            'optimization_objective': 'minimize_distance',
            'time_budget_seconds': 60,
        },
        timeout=120
    )
    response.raise_for_status()
    result = response.json()
    context['ti'].xcom_push(key='optimization_result', value=result)
    
    return {
        'routes_created': len(result.get('routes', [])),
        'unassigned': len(result.get('unassigned_orders', [])),
        'total_distance_km': result.get('total_distance_km', 0),
    }


def assign_routes(**context):
    """Assign optimized routes to database."""
    from sqlalchemy import create_engine, text
    import os
    from uuid import uuid4
    
    result = context['ti'].xcom_pull(key='optimization_result')
    drivers = context['ti'].xcom_pull(key='available_drivers')
    orders = context['ti'].xcom_pull(key='pending_orders') or []
    
    if not result or not result.get('routes'):
        return 0
    
    order_lookup = {str(order['id']): order for order in orders}
    engine = create_engine(os.environ.get('DATABASE_URL'))
    tomorrow = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
    
    routes_created = 0
    
    with engine.begin() as conn:
        for i, route in enumerate(result['routes']):
            if i >= len(drivers):
                break
            
            driver = drivers[i]
            route_id = str(uuid4())
            
            # Insert route
            conn.execute(text("""
                INSERT INTO routes (
                    id, route_date, driver_id, vehicle_id,
                    planned_distance_km, planned_duration_minutes, planned_stops,
                    algorithm_used, optimization_score, computation_time_ms, status
                ) VALUES (
                    :id, :date, :driver_id, :vehicle_id,
                    :distance, :duration, :stops, :algorithm, :score, :computation_time_ms, 'planned'
                )
            """), {
                'id': route_id,
                'date': tomorrow,
                'driver_id': driver['driver_id'],
                'vehicle_id': driver['vehicle_id'],
                'distance': route['total_distance_km'],
                'duration': route.get('total_duration_minutes'),
                'stops': len(route['stops']),
                'algorithm': result.get('algorithm_used', 'greedy'),
                'score': result.get('optimization_score', 0.8),
                'computation_time_ms': result.get('computation_time_ms'),
            })
            
            # Insert stops
            for stop in route['stops']:
                order_info = order_lookup.get(stop['order_id'], {})
                latitude = stop.get('latitude', order_info.get('latitude'))
                longitude = stop.get('longitude', order_info.get('longitude'))
                if latitude is None or longitude is None:
                    raise ValueError(f"Missing coordinates for stop {stop.get('order_id')}")
                
                conn.execute(text("""
                    INSERT INTO route_stops (
                        id, route_id, order_id, stop_sequence,
                        location, address, status
                    ) VALUES (
                        :id, :route_id, :order_id, :sequence,
                        ST_SetSRID(ST_MakePoint(:longitude, :latitude), 4326)::geography,
                        :address, 'pending'
                    )
                """), {
                    'id': str(uuid4()),
                    'route_id': route_id,
                    'order_id': stop['order_id'],
                    'sequence': stop['sequence'],
                    'latitude': latitude,
                    'longitude': longitude,
                    'address': order_info.get('address', 'Unknown address'),
                })
            
            routes_created += 1
    
    return routes_created


# Create DAG
with DAG(
    dag_id='daily_route_optimization',
    default_args=default_args,
    description='Daily route optimization pipeline',
    schedule_interval='0 18 * * *',  # Run at 6 PM daily
    start_date=datetime(2024, 1, 1),
    catchup=False,
    tags=['fleetflow', 'optimization'],
) as dag:
    
    # Task 1: Extract pending orders
    extract_orders = PythonOperator(
        task_id='extract_pending_orders',
        python_callable=extract_pending_orders,
    )
    
    # Task 2: Get available drivers
    get_drivers = PythonOperator(
        task_id='get_available_drivers',
        python_callable=get_available_drivers,
    )
    
    # Task 3: Run dbt models
    with TaskGroup(group_id='dbt_transformations') as dbt_group:
        dbt_run = BashOperator(
            task_id='dbt_run',
            bash_command='cd /opt/dbt && dbt run --select staging marts',
        )
        
        dbt_test = BashOperator(
            task_id='dbt_test',
            bash_command='cd /opt/dbt && dbt test',
        )
        
        dbt_run >> dbt_test
    
    # Task 4: Run optimization
    optimize = PythonOperator(
        task_id='run_optimization',
        python_callable=run_optimization,
    )
    
    # Task 5: Assign routes
    assign = PythonOperator(
        task_id='assign_routes',
        python_callable=assign_routes,
    )
    
    # Task 6: Send notifications
    notify = BashOperator(
        task_id='send_notifications',
        bash_command='echo "Routes optimized for tomorrow. Check dashboard for details."',
    )
    
    # Define dependencies
    [extract_orders, get_drivers] >> dbt_group >> optimize >> assign >> notify

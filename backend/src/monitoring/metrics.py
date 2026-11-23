"""
Prometheus metrics for API monitoring.
"""

from prometheus_client import Counter, Gauge, Histogram, Info

# API Request Metrics
http_requests_total = Counter(
    "http_requests_total", "Total HTTP requests", ["method", "endpoint", "status"]
)

http_request_duration_seconds = Histogram(
    "http_request_duration_seconds", "HTTP request latency", ["method", "endpoint"]
)

http_requests_in_progress = Gauge(
    "http_requests_in_progress", "Number of HTTP requests in progress", ["method", "endpoint"]
)

# Business Metrics
orders_total = Counter("orders_total", "Total orders created", ["status"])

routes_optimized_total = Counter("routes_optimized_total", "Total routes optimized", ["depot"])

optimization_duration_seconds = Histogram(
    "optimization_duration_seconds", "Route optimization duration", ["depot", "num_orders"]
)

# Driver Metrics
active_drivers = Gauge("active_drivers", "Number of active drivers", ["status"])

# Vehicle Metrics
active_vehicles = Gauge("active_vehicles", "Number of active vehicles", ["status"])

# Kafka Metrics
kafka_messages_produced_total = Counter(
    "kafka_messages_produced_total", "Total Kafka messages produced", ["topic"]
)

kafka_messages_consumed_total = Counter(
    "kafka_messages_consumed_total", "Total Kafka messages consumed", ["topic", "consumer_group"]
)

kafka_consumer_lag = Gauge(
    "kafka_consumer_lag", "Kafka consumer lag", ["topic", "partition", "consumer_group"]
)

# Database Metrics
db_connections_active = Gauge("db_connections_active", "Number of active database connections")

db_query_duration_seconds = Histogram(
    "db_query_duration_seconds", "Database query duration", ["query_type"]
)

# ML Model Metrics
ml_predictions_total = Counter(
    "ml_predictions_total", "Total ML predictions made", ["model_name", "model_version"]
)

ml_prediction_duration_seconds = Histogram(
    "ml_prediction_duration_seconds", "ML prediction duration", ["model_name"]
)

ml_model_accuracy = Gauge("ml_model_accuracy", "ML model accuracy score", ["model_name", "metric"])

# Application Info
app_info = Info("fleetflow_app", "FleetFlow application information")

# System Health
system_health = Gauge(
    "system_health", "System health status (1=healthy, 0=degraded)", ["component"]
)

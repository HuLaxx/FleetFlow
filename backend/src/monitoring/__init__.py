"""
Monitoring package.
"""

from src.monitoring.metrics import (
    http_requests_total,
    http_request_duration_seconds,
    orders_total,
    routes_optimized_total,
    optimization_duration_seconds,
    kafka_messages_produced_total,
    kafka_messages_consumed_total,
    app_info,
    system_health,
)

from src.monitoring.prometheus_middleware import PrometheusMiddleware
from src.monitoring.sentry_config import configure_sentry, capture_exception, set_user_context

__all__ = [
    # Metrics
    "http_requests_total",
    "http_request_duration_seconds",
    "orders_total",
    "routes_optimized_total",
    "optimization_duration_seconds",
    "kafka_messages_produced_total",
    "kafka_messages_consumed_total",
    "app_info",
    "system_health",
    # Middleware
    "PrometheusMiddleware",
    # Sentry
    "configure_sentry",
    "capture_exception",
    "set_user_context",
]

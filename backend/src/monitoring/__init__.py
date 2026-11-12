"""
Monitoring package.
"""

from src.monitoring.metrics import (
    app_info,
    http_request_duration_seconds,
    http_requests_total,
    kafka_messages_consumed_total,
    kafka_messages_produced_total,
    optimization_duration_seconds,
    orders_total,
    routes_optimized_total,
    system_health,
)
from src.monitoring.prometheus_middleware import PrometheusMiddleware
from src.monitoring.sentry_config import capture_exception, configure_sentry, set_user_context

__all__ = [
    "app_info",
    "capture_exception",
    "configure_sentry",
    "http_request_duration_seconds",
    "http_requests_total",
    "kafka_messages_consumed_total",
    "kafka_messages_produced_total",
    "optimization_duration_seconds",
    "orders_total",
    "PrometheusMiddleware",
    "routes_optimized_total",
    "set_user_context",
    "system_health",
]

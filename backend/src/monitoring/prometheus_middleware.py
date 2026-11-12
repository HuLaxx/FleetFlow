"""
Prometheus metrics middleware for FastAPI.
"""

import time

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.status import HTTP_500_INTERNAL_SERVER_ERROR

from src.monitoring.metrics import (
    http_request_duration_seconds,
    http_requests_in_progress,
    http_requests_total,
)


class PrometheusMiddleware(BaseHTTPMiddleware):
    """Middleware to collect Prometheus metrics for HTTP requests."""

    async def dispatch(self, request: Request, call_next):
        # Skip metrics endpoint itself
        if request.url.path == "/metrics":
            return await call_next(request)

        method = request.method
        endpoint = request.url.path

        # Track in-progress requests
        http_requests_in_progress.labels(method=method, endpoint=endpoint).inc()

        start_time = time.time()
        status_code = HTTP_500_INTERNAL_SERVER_ERROR

        try:
            response: Response = await call_next(request)
            status_code = response.status_code
            return response
        except Exception:
            # Re-raise but still record metrics
            raise
        finally:
            # Record metrics
            duration = time.time() - start_time

            http_requests_total.labels(method=method, endpoint=endpoint, status=status_code).inc()

            http_request_duration_seconds.labels(method=method, endpoint=endpoint).observe(duration)

            http_requests_in_progress.labels(method=method, endpoint=endpoint).dec()

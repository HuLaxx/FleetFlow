"""
Metrics API endpoint.
"""

from fastapi import APIRouter, Response
from fastapi.responses import JSONResponse
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from src.config import get_settings
from src.monitoring.metrics import app_info, system_health
from src.monitoring.readiness import probe_readiness

router = APIRouter(tags=["Monitoring"])

settings = get_settings()


@router.get("/metrics")
async def metrics():
    """
    Prometheus metrics endpoint.

    Exposes metrics in Prometheus format for scraping.
    """
    # Update app info
    app_info.info(
        {
            "version": settings.app_version,
            "name": settings.app_name,
            "environment": settings.environment,
        }
    )

    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


@router.get("/health/live")
async def liveness():
    """
    Kubernetes liveness probe.

    Returns 200 if the application is running.
    """
    return {"status": "alive"}


@router.get("/health/ready")
async def readiness():
    """Return HTTP 503 if PostGIS or Kafka is unavailable, 200 otherwise.

    A running app or instantiated producer does NOT prove a usable broker.
    This is an operational readiness probe, not an end-to-end delivery SLA.
    """
    result = await probe_readiness()
    for component, status in result["components"].items():
        system_health.labels(component=component).set(
            1 if status["status"] == "healthy" else 0
        )
    return JSONResponse(
        status_code=200 if result["status"] == "ready" else 503, content=result
    )

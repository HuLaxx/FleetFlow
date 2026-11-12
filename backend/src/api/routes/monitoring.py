"""
Metrics API endpoint.
"""

from fastapi import APIRouter, Response
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from src.config import get_settings
from src.monitoring.metrics import app_info, system_health

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
    """
    Kubernetes readiness probe.

    Returns 200 if the application is ready to serve traffic.
    Checks database, Kafka, and other dependencies.
    """
    from src.database import check_db_health
    from src.events import get_kafka_producer

    db_health = await check_db_health()
    kafka_producer = get_kafka_producer()

    all_healthy = db_health["status"] == "healthy"

    # Update system health metrics
    system_health.labels(component="database").set(1 if db_health["status"] == "healthy" else 0)
    system_health.labels(component="kafka").set(1 if kafka_producer else 0)

    if not all_healthy:
        return {
            "status": "not_ready",
            "components": {
                "database": db_health,
                "kafka": {"status": "healthy" if kafka_producer else "unavailable"},
            },
        }, 503

    return {
        "status": "ready",
        "components": {"database": db_health, "kafka": {"status": "healthy"}},
    }

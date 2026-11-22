"""Fail-closed operational readiness checks for PostGIS and Kafka.

Liveness only proves that the HTTP process is running. Readiness checks the
database *and a real Kafka metadata request*; a producer singleton existing
does not imply that its broker can be reached. No credentials or bootstrap
addresses are returned by the endpoint.
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from typing import Any

from confluent_kafka.admin import AdminClient

from src.config import get_settings
from src.database import check_db_health


def _kafka_metadata_available() -> bool:
    admin = AdminClient(
        {
            "bootstrap.servers": get_settings().kafka_bootstrap_servers,
            "socket.timeout.ms": 2000,
            "request.timeout.ms": 2000,
        }
    )
    metadata = admin.list_topics(timeout=2)
    return bool(metadata.brokers)


async def check_kafka_readiness() -> bool:
    """A bounded, nonblocking broker metadata request, not a delivery guarantee."""
    try:
        return await asyncio.wait_for(
            asyncio.to_thread(_kafka_metadata_available), timeout=4
        )
    except Exception:
        # Deliberately return no raw broker hostname, credentials or exception.
        return False


async def probe_readiness(
    db_probe: Callable[[], Awaitable[dict[str, Any]]] | None = None,
    kafka_probe: Callable[[], Awaitable[bool]] | None = None,
) -> dict[str, Any]:
    """Return a minimal status object; false on any failing dependency."""
    check_db = db_probe or check_db_health
    check_kafka = kafka_probe or check_kafka_readiness
    try:
        db_result = await check_db()
        db_ready = isinstance(db_result, dict) and db_result.get("status") == "healthy"
    except Exception:
        db_ready = False
    try:
        kafka_ready = bool(await check_kafka())
    except Exception:
        kafka_ready = False
    ready = db_ready and kafka_ready
    return {
        "status": "ready" if ready else "not_ready",
        "components": {
            "database": {"status": "healthy" if db_ready else "unavailable"},
            "kafka": {"status": "healthy" if kafka_ready else "unavailable"},
        },
    }

"""Readiness must fail closed for either dependency and send true HTTP 503."""

from unittest.mock import AsyncMock

import pytest

from src.monitoring.readiness import probe_readiness


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "db_ok,kafka_ok,expected_status",
    [
        (True, True, "ready"),
        (False, True, "not_ready"),
        (True, False, "not_ready"),
        (False, False, "not_ready"),
    ],
)
async def test_readiness_requires_both_real_dependencies(db_ok, kafka_ok, expected_status):
    db = AsyncMock(return_value={"status": "healthy" if db_ok else "unhealthy"})
    kafka = AsyncMock(return_value=kafka_ok)
    data = await probe_readiness(db_probe=db, kafka_probe=kafka)
    assert data["status"] == expected_status
    assert data["components"]["database"]["status"] == (
        "healthy" if db_ok else "unavailable"
    )
    assert data["components"]["kafka"]["status"] == (
        "healthy" if kafka_ok else "unavailable"
    )
    assert set(data) == {"status", "components"}
    db.assert_awaited_once()
    kafka.assert_awaited_once()


@pytest.mark.asyncio
async def test_readiness_rejects_broker_error_and_does_not_disclose_credentials():
    async def db():
        return {"status": "healthy", "database": "postgres", "password": "private"}

    async def kafka():
        raise RuntimeError("broker unavailable: private-host:9092?password=private")

    data = await probe_readiness(db_probe=db, kafka_probe=kafka)
    assert data["status"] == "not_ready"
    assert data["components"]["kafka"]["status"] == "unavailable"
    assert "private" not in str(data)


@pytest.mark.asyncio
async def test_database_probe_exception_is_not_ready_even_with_kafka():
    async def db():
        raise ConnectionError("private-database-host")

    data = await probe_readiness(db_probe=db, kafka_probe=AsyncMock(return_value=True))
    assert data["status"] == "not_ready"
    assert data["components"]["database"]["status"] == "unavailable"
    assert "private-database-host" not in str(data)


@pytest.mark.asyncio
async def test_readiness_route_uses_actual_http_503(client, monkeypatch):
    import src.api.routes.monitoring as monitoring_routes

    monkeypatch.setattr(
        monitoring_routes,
        "probe_readiness",
        AsyncMock(
            return_value={
                "status": "not_ready",
                "components": {
                    "database": {"status": "healthy"},
                    "kafka": {"status": "unavailable"},
                },
            }
        ),
    )
    response = await client.get("/health/ready")
    assert response.status_code == 503
    assert response.json()["status"] == "not_ready"
    assert response.json()["components"]["kafka"]["status"] == "unavailable"


@pytest.mark.asyncio
async def test_readiness_route_returns_200_when_both_healthy(client, monkeypatch):
    import src.api.routes.monitoring as monitoring_routes

    monkeypatch.setattr(
        monitoring_routes,
        "probe_readiness",
        AsyncMock(
            return_value={
                "status": "ready",
                "components": {
                    "database": {"status": "healthy"},
                    "kafka": {"status": "healthy"},
                },
            }
        ),
    )
    response = await client.get("/health/ready")
    assert response.status_code == 200
    assert response.json()["status"] == "ready"

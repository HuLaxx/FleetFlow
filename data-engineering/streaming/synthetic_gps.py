"""Deterministic synthetic GPS v1 events, published to Kafka with Spark (no extra client)."""
from __future__ import annotations

import json
import random
import uuid
from datetime import datetime, timedelta, timezone

T0 = datetime(2026, 11, 1, 8, 0, tzinfo=timezone.utc)
NS = uuid.UUID("6f0c3e2a-58b1-4c1e-9a43-0f2b5c6d7e81")


def event_id(i: int) -> str:
    return str(uuid.uuid5(NS, f"gps-{i}"))


def gps_event(i: int, minute: float, *, vehicles: int = 10, rng: random.Random | None = None) -> dict:
    rng = rng or random.Random(i)
    v = i % vehicles
    return {
        "event_type": "driver.location_updated",
        "schema_version": 1,
        "event_id": event_id(i),
        "timestamp": (T0 + timedelta(minutes=minute)).isoformat(),
        "driver_id": str(uuid.uuid5(NS, f"driver-{v}")),
        "vehicle_id": str(uuid.uuid5(NS, f"vehicle-{v}")),
        "route_id": None,
        "location": {"latitude": 55.86 + rng.uniform(-0.05, 0.05), "longitude": -4.25 + rng.uniform(-0.05, 0.05)},
        "speed_kmh": round(rng.uniform(0, 70), 2),
        "heading": round(rng.uniform(0, 359), 1),
        "accuracy_m": round(rng.uniform(2, 15), 1),
        "is_moving": True,
    }


def invalid_events(start: int, n: int) -> list[dict]:
    out = []
    for k in range(n):
        e = gps_event(start + k, 5)
        kind = k % 4
        if kind == 0:
            e["schema_version"] = 2
        elif kind == 1:
            e["location"]["latitude"] = 123.0
        elif kind == 2:
            e["timestamp"] = (T0 + timedelta(minutes=5)).replace(tzinfo=None).isoformat()
        else:
            e.pop("event_id")
        out.append(e)
    return out


def publish(spark, bootstrap: str, topic: str, events: list[dict]) -> None:
    rows = [(e.get("vehicle_id"), json.dumps(e)) for e in events]
    (
        spark.createDataFrame(rows, "key string, value string")
        .write.format("kafka")
        .option("kafka.bootstrap.servers", bootstrap)
        .option("topic", topic)
        .save()
    )

"""Offline negative cases for the source-order/GPS/dbt lineage verifier."""
from copy import deepcopy
from uuid import UUID

import pytest

from scripts.verify_order_gps_lineage import LineageError, verify


def _id(number):
    return str(UUID(int=number))


def receipts():
    route = dict(
        algorithm_used="ortools-cvrptw-haversine",
        approval_status="approved",
        dispatch_status="in_progress",
        broker_ack=True,
        order_id=_id(1),
        route_id=_id(2),
        driver_id=_id(3),
        vehicle_id=_id(4),
    )
    gps = dict(
        route_id=_id(2),
        driver_id=_id(3),
        vehicle_id=_id(4),
        event_id=_id(5),
        broker_ack=True,
        database_accepted=True,
    )
    analytics = dict(
        order_id=_id(1),
        route_id=_id(2),
        raw_event_id=_id(5),
        clean_event_id=_id(5),
        curated_event_id=_id(5),
        dbt_event_id=_id(5),
        dbt_row_count=1,
        duplicate_count=0,
        source_sha256="a" * 64,
    )
    return route, gps, analytics


def test_complete_explicit_lineage():
    assert verify(*receipts())["status"] == "verified"


@pytest.mark.parametrize(
    "index,key,value",
    [
        (0, "algorithm_used", "fixture"),
        (0, "approval_status", "planned"),
        (0, "dispatch_status", "planned"),
        (0, "broker_ack", False),
        (1, "broker_ack", False),
        (1, "database_accepted", False),
        (1, "vehicle_id", _id(99)),
        (1, "driver_id", _id(99)),
        (1, "route_id", _id(99)),
        (2, "order_id", _id(99)),
        (2, "route_id", _id(99)),
        (2, "raw_event_id", _id(99)),
        (2, "clean_event_id", _id(99)),
        (2, "curated_event_id", _id(99)),
        (2, "dbt_event_id", _id(99)),
        (2, "dbt_row_count", 0),
        (2, "duplicate_count", 1),
        (2, "source_sha256", "invalid"),
    ],
)
def test_mismatched_or_unverified_boundary_rejected(index, key, value):
    data = list(deepcopy(receipts()))
    data[index][key] = value
    with pytest.raises(LineageError):
        verify(*data)


@pytest.mark.parametrize("index,key", [(0, "order_id"), (0, "route_id"), (1, "event_id"), (2, "dbt_event_id")])
def test_missing_identity_rejected(index, key):
    data = list(deepcopy(receipts()))
    del data[index][key]
    with pytest.raises(LineageError):
        verify(*data)

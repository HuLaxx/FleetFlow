"""PostGIS-backed approval durability and inbox/outbox failure tests.

Broker delivery is simulated; this proves transaction/retry logic rather than
an operating Kafka cluster or a true end-to-end browser journey.
"""

from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from sqlalchemy import func, select, text
from sqlalchemy.exc import DBAPIError

from src.models import DispatchConsumerInbox, DispatchOutboxEvent, RouteApprovalAudit
from src.reliability.dispatch import apply_once, dispatch_outbox_batch
from tests.test_api.test_dispatch_approval import seed_dispatch, token_for
from src.models.user import UserRole


async def _approve(
    client, db_session, sample_depot, sample_driver, sample_vehicle, sample_order
):
    route, _, _, _ = await seed_dispatch(
        db_session, sample_depot, sample_driver, sample_vehicle, sample_order
    )
    headers = await token_for(db_session, UserRole.DISPATCHER)
    response = await client.post(f"/api/v1/routes/{route.id}/approve", headers=headers)
    assert response.status_code == 200, response.text
    return route, response.json(), headers


@pytest.mark.asyncio
async def test_approval_writes_audit_and_pending_event_with_one_transaction(
    client, db_session, sample_depot, sample_driver, sample_vehicle, sample_order
):
    route, result, headers = await _approve(
        client, db_session, sample_depot, sample_driver, sample_vehicle, sample_order
    )
    audit = await db_session.scalar(
        select(RouteApprovalAudit).where(RouteApprovalAudit.route_id == route.id)
    )
    assert audit is not None
    assert audit.previous_status == "planned"
    assert audit.new_status == "approved"
    assert audit.approved_by_user_id is not None
    assert str(audit.event_id) == result["approval_event_id"]

    outbox = await db_session.get(DispatchOutboxEvent, audit.event_id)
    assert outbox is not None
    assert outbox.topic == "routes.approved"
    assert outbox.status == "pending"
    assert result["delivery_status"] == "pending"
    assert outbox.payload["route_id"] == str(route.id)
    assert outbox.payload["event_id"] == str(outbox.id)
    assert outbox.payload["schema_version"] == 1
    assert "email" not in outbox.payload

    again = await client.post(f"/api/v1/routes/{route.id}/approve", headers=headers)
    assert again.status_code == 409
    count = await db_session.scalar(select(func.count(RouteApprovalAudit.id)))
    assert count == 1


@pytest.mark.asyncio
async def test_retry_after_acknowledgement_failure_keeps_event_pending(
    client, db_session, sample_depot, sample_driver, sample_vehicle, sample_order
):
    route, result, _ = await _approve(
        client, db_session, sample_depot, sample_driver, sample_vehicle, sample_order
    )
    event_id = UUID(result["approval_event_id"])

    async def broker_unavailable(topic, payload, key):
        raise TimeoutError("Intentionally simulated transport outage")

    first = await dispatch_outbox_batch(db_session, broker_unavailable)
    assert first == {"selected": 1, "published": 0, "failed": 1}
    event = await db_session.get(DispatchOutboxEvent, event_id)
    assert event.status == "pending"
    assert event.attempts == 1
    assert event.last_error == "TimeoutError"
    assert event.next_attempt_at > datetime.now(UTC)

    # Time advancing is simulated by making the retry eligible again.
    event.next_attempt_at = datetime.now(UTC) - timedelta(seconds=1)
    await db_session.flush()
    seen = []

    async def confirmed(topic, payload, key):
        seen.append((topic, payload["event_id"], key))

    second = await dispatch_outbox_batch(db_session, confirmed)
    assert second == {"selected": 1, "published": 1, "failed": 0}
    assert seen == [("routes.approved", str(event_id), str(route.id))]
    assert event.status == "published"
    assert event.attempts == 2
    assert event.published_at is not None
    assert event.last_error is None


@pytest.mark.asyncio
async def test_inbox_deduplicates_same_event_but_not_distinct_event(
    db_session,
):
    event_id = uuid4()
    another = uuid4()
    calls = []

    async def handle():
        calls.append("business-side-effect")

    first = await apply_once(db_session, "route-approval-v1", event_id, handle)
    second = await apply_once(db_session, "route-approval-v1", event_id, handle)
    third = await apply_once(db_session, "route-approval-v1", another, handle)
    assert (first, second, third) == (True, False, True)
    assert len(calls) == 2
    receipts = (
        await db_session.scalars(
            select(DispatchConsumerInbox).where(
                DispatchConsumerInbox.consumer_name == "route-approval-v1"
            )
        )
    ).all()
    assert len(receipts) == 2


@pytest.mark.asyncio
async def test_inbox_receipt_rollback_on_handler_failure(db_session):
    event_id = uuid4()

    async def handler_crashes():
        raise RuntimeError("Simulated crash before applying DB business effects")

    with pytest.raises(RuntimeError):
        async with db_session.begin_nested():
            await apply_once(db_session, "route-approval-v1", event_id, handler_crashes)

    receipt = await db_session.get(
        DispatchConsumerInbox, ("route-approval-v1", event_id)
    )
    assert receipt is None


@pytest.mark.asyncio
async def test_audit_triggers_reject_both_update_and_delete(
    client, db_session, sample_depot, sample_driver, sample_vehicle, sample_order
):
    route, _, _ = await _approve(
        client, db_session, sample_depot, sample_driver, sample_vehicle, sample_order
    )
    # Exercise the same trigger logic as db/init/03_dispatch_reliability.sql.
    await db_session.execute(
        text(
            """CREATE OR REPLACE FUNCTION reject_route_approval_audit_mutation()
               RETURNS TRIGGER AS $$
               BEGIN
                   RAISE EXCEPTION 'Route approval audit is append-only';
               END;
               $$ LANGUAGE plpgsql"""
        )
    )
    await db_session.execute(
        text(
            """CREATE TRIGGER route_approval_audit_immutable
               BEFORE UPDATE OR DELETE ON route_approval_audit
               FOR EACH ROW EXECUTE FUNCTION reject_route_approval_audit_mutation()"""
        )
    )

    with pytest.raises(DBAPIError):
        async with db_session.begin_nested():
            await db_session.execute(
                text(
                    "UPDATE route_approval_audit SET previous_status = 'cancelled' "
                    "WHERE route_id = :route_id"
                ),
                {"route_id": route.id},
            )

    with pytest.raises(DBAPIError):
        async with db_session.begin_nested():
            await db_session.execute(
                text("DELETE FROM route_approval_audit WHERE route_id = :route_id"),
                {"route_id": route.id},
            )

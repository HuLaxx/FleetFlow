"""Transactional outbox and inbox operations.

A row is selected FOR UPDATE SKIP LOCKED before a *confirmed* broker
publication. A process crash after Kafka acknowledgement but before DB commit
can replay the event: downstream consumers MUST deduplicate by event_id.
"""

from collections.abc import Awaitable, Callable
from datetime import UTC, datetime, timedelta
from uuid import UUID

from confluent_kafka import KafkaException
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.models import DispatchConsumerInbox, DispatchOutboxEvent

Publisher = Callable[[str, dict, str], Awaitable[None]]
InboxHandler = Callable[[], Awaitable[None]]


async def dispatch_outbox_batch(
    session: AsyncSession,
    publish: Publisher,
    *,
    max_messages: int = 10,
) -> dict[str, int]:
    """Attempt due events with row locking; never claim exactly-once Kafka delivery."""
    if not 1 <= max_messages <= 100:
        raise ValueError("max_messages must be between 1 and 100")

    now = datetime.now(UTC)
    rows = (
        await session.scalars(
            select(DispatchOutboxEvent)
            .where(
                DispatchOutboxEvent.status == "pending",
                DispatchOutboxEvent.next_attempt_at <= now,
            )
            .order_by(
                DispatchOutboxEvent.next_attempt_at,
                DispatchOutboxEvent.created_at,
                DispatchOutboxEvent.id,
            )
            .limit(max_messages)
            .with_for_update(skip_locked=True)
        )
    ).all()

    published = 0
    failed = 0
    for event in rows:
        event.attempts += 1
        try:
            await publish(event.topic, event.payload, event.message_key)
        except (KafkaException, BufferError, TimeoutError, RuntimeError, OSError) as exc:
            # Store only the exception class, never secrets, payloads or broker URLs.
            event.last_error = type(exc).__name__[:150]
            backoff = min(300, 2 ** min(event.attempts, 8))
            event.next_attempt_at = datetime.now(UTC) + timedelta(seconds=backoff)
            failed += 1
        else:
            event.status = "published"
            event.published_at = datetime.now(UTC)
            event.last_error = None
            published += 1

    # The commit is separate from broker ACKs. Replays are therefore possible.
    await session.commit()
    return {"selected": len(rows), "published": published, "failed": failed}


async def apply_once(
    session: AsyncSession,
    consumer_name: str,
    event_id: UUID,
    handler: InboxHandler,
) -> bool:
    """Claim and apply a DB side effect in the caller's transaction.

    Caller must commit on success or roll back on failure. The inbox receipt
    and DB business effect are atomic only when the handler shares *session*.
    External WebSocket sends or other service calls are NOT covered.
    """
    if not consumer_name or len(consumer_name) > 100:
        raise ValueError("consumer_name must be 1 to 100 characters")

    statement = (
        insert(DispatchConsumerInbox)
        .values(consumer_name=consumer_name, event_id=event_id)
        .on_conflict_do_nothing(
            index_elements=[
                DispatchConsumerInbox.consumer_name,
                DispatchConsumerInbox.event_id,
            ]
        )
        .returning(DispatchConsumerInbox.event_id)
    )
    result = await session.scalar(statement)
    if result is None:
        return False
    await handler()
    return True

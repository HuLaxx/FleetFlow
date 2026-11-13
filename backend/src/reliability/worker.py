"""Explicit, opt-in outbox drainer for local/container operations.

Run: python -m src.reliability.worker --once
Run under a supervised process and monitoring before using --forever.
No background publisher starts automatically in the FastAPI process.
"""

import argparse
import asyncio

import structlog

from src.database import AsyncSessionLocal
from src.events.producer import get_kafka_producer
from src.reliability.dispatch import dispatch_outbox_batch

logger = structlog.get_logger()


async def run_once() -> dict[str, int]:
    producer = get_kafka_producer()
    async with AsyncSessionLocal() as session:
        return await dispatch_outbox_batch(session, producer.publish_confirmed_async)


async def _main(forever: bool, interval: float) -> None:
    while True:
        result = await run_once()
        logger.info("Outbox batch completed", **result)
        if not forever:
            return
        await asyncio.sleep(interval)


def main() -> None:
    parser = argparse.ArgumentParser(description="FleetFlow explicit outbox worker")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--once", action="store_true", help="Process one bounded batch")
    group.add_argument("--forever", action="store_true", help="Supervised polling loop")
    parser.add_argument("--interval", type=float, default=2.0)
    args = parser.parse_args()
    if args.interval <= 0:
        parser.error("--interval must be greater than zero")
    asyncio.run(_main(args.forever, args.interval))


if __name__ == "__main__":
    main()

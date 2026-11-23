"""Build only the isolated fleetflow_test schema for dbt CI."""
import asyncio

import src.models  # noqa: F401 - register ORM metadata
from sqlalchemy import text

from src.database import Base, engine


async def main() -> None:
    if engine.url.database != "fleetflow_test" or engine.url.host not in (
        "127.0.0.1",
        "localhost",
    ):
        raise RuntimeError("Refusing to create analytics fixtures outside local fleetflow_test")
    try:
        async with engine.begin() as connection:
            await connection.execute(text("CREATE EXTENSION IF NOT EXISTS postgis"))
            await connection.run_sync(Base.metadata.create_all)
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())

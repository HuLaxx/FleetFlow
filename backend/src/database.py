"""
Database connection and session management.

Provides async SQLAlchemy engine and session dependency injection for FastAPI.
"""

from collections.abc import AsyncGenerator

import structlog
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import NullPool

from src.config import get_settings

logger = structlog.get_logger()
settings = get_settings()


# Base class for all ORM models
class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models."""


# Create async engine
engine = create_async_engine(
    settings.database_url,
    echo=settings.debug,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
    poolclass=NullPool if settings.debug else None,
)

# Session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency that provides a database session.

    Usage in FastAPI:
        @router.get("/items")
        async def list_items(db: AsyncSession = Depends(get_db)):
            result = await db.execute(select(Item))
            return result.scalars().all()
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db() -> None:
    """Initialize database connection pool."""
    try:
        async with engine.begin() as conn:
            # Test connection
            await conn.execute(text("SELECT 1"))
        logger.info("Database connection pool initialized", url=settings.postgres_host)
    except Exception as e:
        logger.error("Failed to initialize database", error=str(e))
        raise


async def close_db() -> None:
    """Close database connection pool."""
    await engine.dispose()
    logger.info("Database connection pool closed")


async def check_db_health() -> dict:
    """
    Check database health.

    Returns:
        dict: Health status with connection info
    """
    try:
        async with AsyncSessionLocal() as session:
            from sqlalchemy import text

            result = await session.execute(text("SELECT version()"))
            version = result.scalar()
            return {
                "status": "healthy",
                "database": "postgresql",
                "version": version,
            }
    except (SQLAlchemyError, OSError) as e:
        logger.error("Database health check failed", error=str(e))
        return {
            "status": "unhealthy",
            "error": str(e),
        }

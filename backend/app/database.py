"""
Async SQLAlchemy engine + session factory wired to PostgreSQL + pgvector.

⚠️ CAPACITY FLAG: pool_size=20 handles ~50 concurrent users with
   typical query patterns (< 50ms/query). Monitor pg_stat_activity
   if you see connection-wait latency at load.
"""
import logging
from typing import AsyncGenerator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from .config import settings

logger = logging.getLogger(__name__)

# ── Engine ─────────────────────────────────────────────────────────────────
engine = create_async_engine(
    settings.DATABASE_URL,
    pool_size=settings.DB_POOL_SIZE,
    max_overflow=settings.DB_MAX_OVERFLOW,
    pool_pre_ping=settings.DB_POOL_PRE_PING,
    echo=settings.DEBUG,
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)


class Base(DeclarativeBase):
    """Shared declarative base for all ORM models."""
    pass


# ── Dependency ─────────────────────────────────────────────────────────────
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise


# ── Startup initialisation ─────────────────────────────────────────────────
async def init_db() -> None:
    """
    Enable the pgvector extension and create all tables.
    Called once during application startup (lifespan event).
    """
    async with engine.begin() as conn:
        # Enable pgvector — idempotent
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        logger.info("pgvector extension enabled.")

        # Create tables (Alembic handles schema migrations in production)
        await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables initialised.")


async def close_db() -> None:
    """Dispose the connection pool cleanly on shutdown."""
    await engine.dispose()
    logger.info("Database connection pool closed.")

"""
Alembic environment — async-aware for SQLAlchemy asyncpg driver.

Supports both offline mode (generate SQL script without DB connection)
and online mode (connect to DB and apply migration).

Import path:
  Run from project root: alembic upgrade head
  Working directory must be project root so Python can resolve backend.app.*
"""
import asyncio
import os
import sys
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context

# ── Make sure project root is on sys.path ──────────────────────────────────
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ── Import app models so Alembic can detect schema ─────────────────────────
from backend.app.database import Base           # noqa: F401 — registers all models
from backend.app.models.skills_gap import (     # noqa: F401 — explicit import
    RoleRequirement,
    UserSkill,
)
from backend.app.models.user import User        # noqa: F401 — explicit import

# ── Import settings for DATABASE_URL ───────────────────────────────────────
from backend.app.config import settings

# Alembic Config object (alembic.ini)
config = context.config

# Logging setup from alembic.ini
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Override DATABASE_URL with the one from pydantic settings
# (allows docker-compose to inject DATABASE_URL via environment variable)
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """
    Run migrations in 'offline' mode — generates SQL script without connecting.
    Useful for: generating migration scripts for DBA review before applying.
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Run migrations against a live async database connection."""
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    """Entry point for online migration mode."""
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

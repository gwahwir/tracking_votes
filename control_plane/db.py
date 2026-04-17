"""Database connection and initialization for control plane."""
from __future__ import annotations

from typing import Optional

import structlog
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from agents.base.models import Base

log = structlog.get_logger(__name__)

_engine: Optional[AsyncEngine] = None
_session_maker: Optional[sessionmaker] = None


async def init_database(database_url: str) -> AsyncEngine:
    """Initialize database engine and create all tables."""
    global _engine, _session_maker

    # Convert postgresql:// to postgresql+asyncpg:// for async driver
    if database_url.startswith("postgresql://"):
        database_url = database_url.replace("postgresql://", "postgresql+asyncpg://", 1)

    _engine = create_async_engine(
        database_url,
        echo=False,
        pool_size=20,
        max_overflow=0,
        pool_pre_ping=True,  # Verify connections before use
    )

    # Create all tables
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Create session maker
    _session_maker = sessionmaker(_engine, class_=AsyncSession, expire_on_commit=False)

    log.info("database.initialized", database_url=database_url)
    return _engine


async def close_database():
    """Close database connection."""
    global _engine
    if _engine:
        await _engine.dispose()
        log.info("database.closed")


def get_engine() -> Optional[AsyncEngine]:
    """Get the current database engine."""
    return _engine


def get_session_maker() -> Optional[sessionmaker]:
    """Get the session maker."""
    return _session_maker


async def get_session() -> AsyncSession:
    """Get a new database session."""
    if _session_maker is None:
        raise RuntimeError("Database not initialized. Call init_database() first.")
    async with _session_maker() as session:
        yield session

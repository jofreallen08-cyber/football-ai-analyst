"""Database engine and session management (SQLAlchemy 2.0, psycopg 3)."""

from __future__ import annotations

from collections.abc import Iterator
from functools import lru_cache

from sqlalchemy import Engine, create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from football_ai.core.config import get_settings


@lru_cache
def get_engine() -> Engine:
    """Create (once) the application engine from settings."""
    settings = get_settings()
    return create_engine(
        settings.database_url,
        echo=settings.database_echo,
        pool_pre_ping=True,
        connect_args={"connect_timeout": 5}
        if settings.database_url.startswith("postgresql")
        else {},
    )


@lru_cache
def get_sessionmaker() -> sessionmaker[Session]:
    return sessionmaker(bind=get_engine(), expire_on_commit=False)


def get_session() -> Iterator[Session]:
    """FastAPI dependency yielding a session that is always closed."""
    session = get_sessionmaker()()
    try:
        yield session
    finally:
        session.close()


def check_database(engine: Engine | None = None) -> bool:
    """Return True if the database answers a trivial query."""
    try:
        with (engine or get_engine()).connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception:
        return False
    return True


def get_session_factory() -> sessionmaker[Session]:
    """FastAPI dependency for code that opens its own sessions (background work)."""
    return get_sessionmaker()

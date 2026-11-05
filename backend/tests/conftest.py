"""Shared fixtures.

Database tests are marked ``db`` and run only when ``TEST_DATABASE_URL`` points to a
PostgreSQL database dedicated to tests (it is migrated up and down by the suite).
"""

from __future__ import annotations

import os
from collections.abc import AsyncIterator, Iterator
from datetime import UTC, datetime

import pytest
from alembic import command
from alembic.config import Config
from httpx import ASGITransport, AsyncClient
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session

from football_ai.core.config import Settings
from football_ai.main import create_app

TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL")
BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


@pytest.fixture
def settings() -> Settings:
    return Settings(app_env="test", log_json=True, _env_file=None)  # type: ignore[call-arg]


@pytest.fixture
async def client(settings: Settings) -> AsyncIterator[AsyncClient]:
    app = create_app(settings)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


def _alembic_config(url: str) -> Config:
    cfg = Config(os.path.join(BACKEND_DIR, "alembic.ini"))
    cfg.set_main_option("script_location", os.path.join(BACKEND_DIR, "alembic"))
    cfg.set_main_option("sqlalchemy.url", url)
    return cfg


@pytest.fixture(scope="session")
def db_engine() -> Iterator[Engine]:
    if not TEST_DATABASE_URL:
        pytest.skip("TEST_DATABASE_URL non impostata: test di database saltati")
    cfg = _alembic_config(TEST_DATABASE_URL)
    command.downgrade(cfg, "base")
    command.upgrade(cfg, "head")
    engine = create_engine(TEST_DATABASE_URL)
    yield engine
    engine.dispose()
    command.downgrade(cfg, "base")


@pytest.fixture
def db_session(db_engine: Engine) -> Iterator[Session]:
    """Session wrapped in a transaction that is always rolled back."""
    with db_engine.connect() as conn:
        trans = conn.begin()
        session = Session(bind=conn, join_transaction_mode="create_savepoint")
        try:
            yield session
        finally:
            session.close()
            trans.rollback()


@pytest.fixture
def now() -> datetime:
    return datetime(2026, 1, 1, 12, 0, tzinfo=UTC)


@pytest.fixture(scope="session")
def seeded_engine(db_engine: Engine) -> Engine:
    """Test database populated (committed) with the demo league and Serie A 2025/26."""
    import asyncio

    from football_ai.core.config import Settings
    from football_ai.providers.registry import build_providers
    from football_ai.services.ingestion import IngestionService

    providers = build_providers(Settings(_env_file=None))  # type: ignore[call-arg]

    async def run() -> None:
        with Session(db_engine) as s:
            svc = IngestionService(s)
            await svc.ingest(providers["local_sample"], "DEMO", "2026/27")
            await svc.ingest(providers["openfootball"], "SA", "2025/26")

    asyncio.run(run())
    return db_engine


@pytest.fixture
async def api_client(settings: Settings, seeded_engine: Engine) -> AsyncIterator[AsyncClient]:
    from football_ai.core.db import get_session

    app = create_app(settings)

    def _session() -> Iterator[Session]:
        with Session(seeded_engine) as s:
            yield s

    app.dependency_overrides[get_session] = _session
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac

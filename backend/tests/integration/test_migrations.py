"""The Alembic migrations must produce exactly the schema described by the ORM models."""

from __future__ import annotations

import pytest
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from sqlalchemy import Engine

from football_ai.models import Base

pytestmark = pytest.mark.db


def test_models_and_migrations_in_sync(db_engine: Engine) -> None:
    with db_engine.connect() as conn:
        ctx = MigrationContext.configure(conn, opts={"compare_type": True})
        diff = compare_metadata(ctx, Base.metadata)
    assert diff == [], f"Schema drift between models and migrations: {diff}"

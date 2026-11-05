"""Data sources and ingestion audit tables."""

from __future__ import annotations

import enum
from datetime import datetime
from typing import Any

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from football_ai.models.base import Base, IdMixin, TimestampMixin


class IngestionStatus(enum.StrEnum):
    RUNNING = "running"
    SUCCESS = "success"
    PARTIAL = "partial"
    FAILED = "failed"


class IssueSeverity(enum.StrEnum):
    WARNING = "warning"
    ERROR = "error"


class DataSource(IdMixin, TimestampMixin, Base):
    """A registered data provider together with its license and attribution."""

    __tablename__ = "data_sources"

    key: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    license_name: Mapped[str | None] = mapped_column(String(200))
    license_url: Mapped[str | None] = mapped_column(String(500))
    attribution_text: Mapped[str | None] = mapped_column(Text)
    commercial_use_allowed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class IngestionRun(IdMixin, TimestampMixin, Base):
    __tablename__ = "ingestion_runs"

    source_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("data_sources.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    scope: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[IngestionStatus] = mapped_column(
        Enum(
            IngestionStatus, name="ingestion_status", values_callable=lambda e: [m.value for m in e]
        ),
        nullable=False,
    )
    records_upserted: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    records_rejected: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error: Mapped[str | None] = mapped_column(Text)


class IngestionIssue(IdMixin, TimestampMixin, Base):
    """A record rejected or flagged during validation — never dropped silently."""

    __tablename__ = "ingestion_issues"

    ingestion_run_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("ingestion_runs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    entity_type: Mapped[str] = mapped_column(String(64), nullable=False)
    external_id: Mapped[str | None] = mapped_column(String(128))
    severity: Mapped[IssueSeverity] = mapped_column(
        Enum(IssueSeverity, name="issue_severity", values_callable=lambda e: [m.value for m in e]),
        nullable=False,
    )
    message: Mapped[str] = mapped_column(Text, nullable=False)
    payload: Mapped[dict[str, Any] | None] = mapped_column(JSONB)


class ExternalRef(IdMixin, TimestampMixin, Base):
    """Maps a provider-specific identifier to an internal entity id."""

    __tablename__ = "external_refs"
    __table_args__ = (UniqueConstraint("source_id", "entity_type", "external_id"),)

    source_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("data_sources.id", ondelete="CASCADE"), nullable=False
    )
    entity_type: Mapped[str] = mapped_column(String(64), nullable=False)
    external_id: Mapped[str] = mapped_column(String(128), nullable=False)
    internal_id: Mapped[int] = mapped_column(BigInteger, nullable=False)

"""Helpers to validate raw records one by one, collecting issues instead of failing."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ValidationError

from football_ai.providers.base import RecordIssue


def format_validation_error(err: ValidationError) -> str:
    parts = []
    for e in err.errors():
        loc = ".".join(str(p) for p in e.get("loc", ())) or "record"
        parts.append(f"{loc}: {e.get('msg')}")
    return "; ".join(parts)


def validate_records[M: BaseModel](
    model: type[M],
    raw_items: list[dict[str, Any]],
    entity_type: str,
    issues: list[RecordIssue],
) -> list[M]:
    """Validate each raw dict; invalid ones are appended to ``issues`` and skipped."""
    valid: list[M] = []
    for raw in raw_items:
        try:
            valid.append(model.model_validate(raw))
        except ValidationError as err:
            issues.append(
                RecordIssue(
                    entity_type=entity_type,
                    external_id=str(raw.get("external_id")) if isinstance(raw, dict) else None,
                    message=format_validation_error(err),
                    payload=raw if isinstance(raw, dict) else None,
                )
            )
    return valid

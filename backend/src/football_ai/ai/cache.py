"""AI response cache: identical inputs never trigger a second provider call."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from football_ai.models import AICache


def canonical_json(data: Any) -> str:
    return json.dumps(data, sort_keys=True, ensure_ascii=False, default=str, separators=(",", ":"))


def make_cache_key(
    *, agent: str, prompt_version: str, provider: str, model: str, effort: str, payload: Any
) -> str:
    raw = canonical_json(
        {"a": agent, "v": prompt_version, "p": provider, "m": model, "e": effort, "d": payload}
    )
    return hashlib.sha256(raw.encode()).hexdigest()


def cache_get(session: Session, key: str) -> dict[str, Any] | None:
    row = session.get(AICache, key)
    if row is None:
        return None
    row.hit_count += 1
    row.last_hit_at = datetime.now(UTC)
    return row.response


def cache_put(
    session: Session,
    key: str,
    *,
    agent: str,
    prompt_version: str,
    provider: str,
    model: str,
    response: dict[str, Any],
) -> None:
    row = session.get(AICache, key)
    if row is None:
        session.add(
            AICache(
                cache_key=key,
                agent=agent,
                prompt_version=prompt_version,
                provider=provider,
                model=model,
                response=response,
            )
        )
    else:
        row.response = response

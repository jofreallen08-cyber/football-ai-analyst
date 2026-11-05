"""Hard limits on billable AI calls (daily and per analysis)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, time

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from football_ai.core.config import Settings
from football_ai.models import AIUsage

BILLABLE_STATUSES = ("ok", "error", "refusal", "invalid")


class BudgetExceededError(Exception):
    pass


def check_budget(
    session: Session, settings: Settings, provider: str, analysis_run_id: uuid.UUID | None
) -> None:
    """Raise :class:`BudgetExceededError` if one more billable call would exceed a limit."""
    day_start = datetime.combine(datetime.now(UTC).date(), time.min, UTC)
    base = select(
        func.count(AIUsage.id),
        func.coalesce(func.sum(AIUsage.input_tokens + AIUsage.output_tokens), 0),
    ).where(
        AIUsage.provider == provider,
        AIUsage.status.in_(BILLABLE_STATUSES),
    )
    calls, tokens = session.execute(base.where(AIUsage.created_at >= day_start)).one()
    if calls >= settings.ai_daily_call_limit:
        raise BudgetExceededError(f"limite giornaliero di chiamate AI raggiunto ({calls})")
    if tokens >= settings.ai_daily_token_limit:
        raise BudgetExceededError(f"limite giornaliero di token AI raggiunto ({tokens})")
    if analysis_run_id is not None:
        run_calls = (
            session.scalar(
                select(func.count(AIUsage.id)).where(
                    AIUsage.analysis_run_id == analysis_run_id,
                    AIUsage.provider == provider,
                    AIUsage.status.in_(BILLABLE_STATUSES),
                )
            )
            or 0
        )
        if run_calls >= settings.ai_max_calls_per_analysis:
            raise BudgetExceededError("limite di chiamate AI per analisi raggiunto")

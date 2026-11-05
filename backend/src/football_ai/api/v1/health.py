"""Health endpoint: reports application and database status (no secrets)."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.concurrency import run_in_threadpool

from football_ai import __version__
from football_ai.core.config import Settings, get_settings
from football_ai.core.db import check_database
from football_ai.schemas.health import HealthResponse

router = APIRouter(tags=["sistema"])


@router.get("/health", response_model=HealthResponse, summary="Stato del servizio")
async def health(settings: Annotated[Settings, Depends(get_settings)]) -> HealthResponse:
    db_ok = await run_in_threadpool(check_database)
    return HealthResponse(
        status="ok" if db_ok else "degraded",
        version=__version__,
        environment=settings.app_env,
        database="ok" if db_ok else "unavailable",
        ai_provider=settings.ai_provider,
    )

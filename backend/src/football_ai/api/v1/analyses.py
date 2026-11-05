"""Multi-agent analyses: start (background), poll, list, export; agent catalogue; AI usage."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, Query, Response
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session, sessionmaker

from football_ai.ai.llm.base import LLMProvider
from football_ai.api.deps import Limit, SessionDep
from football_ai.api.v1.agents import get_llm
from football_ai.core.config import Settings, get_settings
from football_ai.core.db import get_session_factory
from football_ai.orchestration.orchestrator import ai_usage_summary, create_run, execute_run
from football_ai.schemas.analysis import (
    AgentInfo,
    AIUsageOut,
    AnalysisOut,
    AnalysisRequest,
    AnalysisSummary,
)
from football_ai.services import analyses as svc

router = APIRouter(tags=["analisi AI"])
SettingsDep = Annotated[Settings, Depends(get_settings)]
LLMDep = Annotated[LLMProvider, Depends(get_llm)]


@router.get("/agents", response_model=list[AgentInfo], summary="Catalogo degli agenti")
def agents() -> list[AgentInfo]:
    return svc.agent_catalogue()


@router.post(
    "/analyses",
    response_model=AnalysisOut,
    status_code=202,
    summary="Avvia l'analisi multi-agente di una partita (riusa analisi identiche)",
)
def start_analysis(
    req: AnalysisRequest,
    response: Response,
    background: BackgroundTasks,
    session: SessionDep,
    settings: SettingsDep,
    llm: LLMDep,
    factory: Annotated[sessionmaker[Session], Depends(get_session_factory)],
) -> AnalysisOut:
    run, reused = create_run(session, settings, llm, req.match_id, force=req.force)
    if reused:
        response.status_code = 200
        return svc.get_analysis(session, run.id, reused=True)
    out = svc.get_analysis(session, run.id)
    background.add_task(execute_run, factory, settings, llm, run.id)
    return out


@router.get("/analyses", response_model=list[AnalysisSummary], summary="Storico analisi e report")
def list_analyses(
    session: SessionDep,
    match_id: Annotated[int | None, Query(ge=1, le=2**62)] = None,
    limit: Limit = 20,
) -> list[AnalysisSummary]:
    return svc.list_analyses(session, match_id, limit)


@router.get(
    "/analyses/{run_id}", response_model=AnalysisOut, summary="Stato e risultati di un'analisi"
)
def get_analysis(session: SessionDep, run_id: uuid.UUID) -> AnalysisOut:
    return svc.get_analysis(session, run_id)


@router.get(
    "/analyses/{run_id}/report.md",
    response_class=PlainTextResponse,
    summary="Esporta il report finale in Markdown",
)
def export(session: SessionDep, run_id: uuid.UUID) -> PlainTextResponse:
    text = svc.export_markdown(session, run_id)
    return PlainTextResponse(
        text,
        media_type="text/markdown; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="report-{run_id}.md"'},
    )


@router.get("/ai/usage", response_model=AIUsageOut, summary="Utilizzo AI di oggi e limiti")
def usage(session: SessionDep, settings: SettingsDep, llm: LLMDep) -> AIUsageOut:
    u = ai_usage_summary(session)
    entries, hits = svc.cache_stats(session)
    return AIUsageOut(
        provider=llm.name,
        model=llm.model,
        effort=settings.ai_effort,
        billable=llm.billable,
        today_calls=u["calls"],
        today_tokens=u["tokens"],
        by_agent=u["by_agent"],
        limits={
            "daily_calls": settings.ai_daily_call_limit,
            "daily_tokens": settings.ai_daily_token_limit,
            "calls_per_analysis": settings.ai_max_calls_per_analysis,
        },
        cache_entries=entries,
        cache_hits=hits,
    )

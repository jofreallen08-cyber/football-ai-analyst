"""Run a single agent on a match (the full multi-agent analysis comes with the orchestrator)."""

from __future__ import annotations

from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Path

from football_ai.agents.registry import AGENTS
from football_ai.ai.factory import build_llm
from football_ai.ai.llm.base import LLMProvider
from football_ai.ai.schemas import AgentReport
from football_ai.api.deps import SessionDep
from football_ai.core.config import Settings, get_settings
from football_ai.services.agents import run_agent
from football_ai.services.analytics import match_context

router = APIRouter(tags=["agenti AI"])


def get_llm(settings: Annotated[Settings, Depends(get_settings)]) -> LLMProvider:
    return build_llm(settings)


AgentName = Literal["match_analyst", "statistics", "team_intelligence", "simulation"]


@router.post(
    "/matches/{match_id}/agents/{agent}",
    response_model=AgentReport,
    summary="Esegue un singolo agente sulla partita (con cache)",
)
async def run_single_agent(
    session: SessionDep,
    settings: Annotated[Settings, Depends(get_settings)],
    llm: Annotated[LLMProvider, Depends(get_llm)],
    match_id: Annotated[int, Path(ge=1, le=2**62)],
    agent: AgentName,
) -> AgentReport:
    ctx = match_context(session, match_id)
    return await run_agent(session, settings, llm, AGENTS[agent], ctx)

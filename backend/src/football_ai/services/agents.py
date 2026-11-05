"""Runs one agent end-to-end: evidence → cache → budget → LLM → validation → storage."""

from __future__ import annotations

import json
import time
import uuid
from dataclasses import dataclass
from typing import Any

from pydantic import ValidationError
from sqlalchemy.orm import Session

from football_ai.agents.base import BaseAgent
from football_ai.ai.budget import BudgetExceededError, check_budget
from football_ai.ai.cache import cache_get, cache_put, make_cache_key
from football_ai.ai.guard import GuardViolationError, agent_texts, check_no_betting, ground_findings
from football_ai.ai.llm.base import LLMError, LLMProvider, LLMRefusalError
from football_ai.ai.prompts import load_prompt
from football_ai.ai.schemas import AGENT_OUTPUT_SCHEMA, AgentOutput, AgentReport
from football_ai.core.config import Settings
from football_ai.core.logging import get_logger
from football_ai.models import AgentReportRow, AgentStatus, AIUsage
from football_ai.schemas.analytics import MatchContext

log = get_logger(__name__)
INSTRUCTION = "Analizza i dati verificati seguenti e rispondi esclusivamente con il JSON richiesto."


def build_user_message(agent: BaseAgent, evidence: dict[str, Any], missing: list[str]) -> str:
    payload = {"agent": agent.name, "evidence": evidence, "known_missing": missing}
    return INSTRUCTION + "\n" + json.dumps(payload, ensure_ascii=False, default=str)


@dataclass(frozen=True)
class _Target:
    match_id: int
    cache_key: str
    analysis_run_id: uuid.UUID | None


def _store(
    session: Session, report: AgentReport, target: _Target, latency_ms: int | None
) -> AgentReport:
    session.add(
        AgentReportRow(
            analysis_run_id=target.analysis_run_id,
            match_id=target.match_id,
            agent=report.agent,
            status=AgentStatus(report.status),
            prompt_version=report.prompt_version,
            provider=report.provider,
            model=report.model,
            cache_key=target.cache_key,
            output=report.model_dump(mode="json"),
            confidence=report.confidence,
            latency_ms=latency_ms,
            error=report.error,
        )
    )
    session.commit()
    return report


def _usage(
    session: Session,
    llm: LLMProvider,
    agent: str,
    status: str,
    analysis_run_id: uuid.UUID | None,
    *,
    input_tokens: int = 0,
    output_tokens: int = 0,
    error: str | None = None,
    request_id: str | None = None,
) -> None:
    session.add(
        AIUsage(
            analysis_run_id=analysis_run_id,
            agent=agent,
            provider=llm.name,
            model=llm.model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            status=status,
            error=error,
            request_id=request_id,
        )
    )
    session.commit()


def _empty_report(
    agent: BaseAgent, llm: LLMProvider, ctx: MatchContext, status: str, reason: str
) -> AgentReport:
    return AgentReport(
        agent=agent.name,
        status=status,
        headline=(
            "Analisi non eseguita: dati insufficienti"
            if status == "skipped"
            else "Analisi non disponibile"
        ),
        findings=[],
        missing_information=agent.known_missing(ctx),
        confidence="low",
        limitations=[reason],
        sources=agent.sources(ctx),
        provider=llm.name,
        model=llm.model,
        prompt_version=agent.prompt_version,
        error=reason if status == "failed" else None,
        is_simulation=agent.is_simulation,
    )


async def run_agent(
    session: Session,
    settings: Settings,
    llm: LLMProvider,
    agent: BaseAgent,
    ctx: MatchContext,
    *,
    analysis_run_id: uuid.UUID | None = None,
) -> AgentReport:
    extra = agent.prepare(session, ctx)
    evidence = agent.build_evidence(ctx, extra)
    missing = agent.known_missing(ctx)
    key = make_cache_key(
        agent=agent.name,
        prompt_version=agent.prompt_version,
        provider=llm.name,
        model=llm.model,
        effort=settings.ai_effort,
        payload={"evidence": evidence, "missing": missing},
    )
    store = _Target(ctx.match.id, key, analysis_run_id)

    reason = agent.skip_reason(ctx, evidence, extra)
    if reason:
        log.info("agent_skipped", agent=agent.name, reason=reason)
        return _store(session, _empty_report(agent, llm, ctx, "skipped", reason), store, 0)

    cached = cache_get(session, key)
    if cached is not None:
        report = AgentReport.model_validate({**cached, "status": "cached"})
        log.info("agent_cache_hit", agent=agent.name)
        return _store(session, report, store, 0)

    if llm.billable:
        try:
            check_budget(session, settings, llm.name, analysis_run_id)
        except BudgetExceededError as exc:
            _usage(session, llm, agent.name, "blocked", analysis_run_id, error=str(exc))
            return _store(session, _empty_report(agent, llm, ctx, "failed", str(exc)), store, 0)

    system = load_prompt(agent.name, agent.prompt_version)
    user = build_user_message(agent, evidence, missing)
    start = time.perf_counter()
    last_error = ""
    for attempt in range(2):
        prompt = (
            user
            if attempt == 0
            else (
                f"{user}\n\nLa risposta precedente non era valida ({last_error}). "
                "Correggila rispettando tutte le regole."
            )
        )
        try:
            result = await llm.complete(
                agent=agent.name,
                system=system,
                user=prompt,
                schema=AGENT_OUTPUT_SCHEMA,
                max_tokens=settings.ai_max_output_tokens,
            )
        except LLMRefusalError as exc:
            _usage(session, llm, agent.name, "refusal", analysis_run_id, error=str(exc))
            return _store(
                session,
                _empty_report(agent, llm, ctx, "failed", str(exc)),
                store,
                None,
            )
        except LLMError as exc:
            _usage(session, llm, agent.name, "error", analysis_run_id, error=str(exc))
            return _store(
                session,
                _empty_report(agent, llm, ctx, "failed", str(exc)),
                store,
                None,
            )

        try:
            output = AgentOutput.model_validate(result.data)
            check_no_betting(agent_texts(output))
            kept, rejected = ground_findings(output, set(evidence))
            if not kept:
                raise GuardViolationError(
                    "nessuna affermazione supportata dalle chiavi di evidenza"
                )
        except (ValidationError, GuardViolationError) as exc:
            last_error = str(exc)[:300]
            _usage(
                session,
                llm,
                agent.name,
                "invalid",
                analysis_run_id,
                input_tokens=result.input_tokens,
                output_tokens=result.output_tokens,
                error=last_error,
                request_id=result.request_id,
            )
            log.warning("agent_output_invalid", agent=agent.name, attempt=attempt, error=last_error)
            continue

        _usage(
            session,
            llm,
            agent.name,
            "ok",
            analysis_run_id,
            input_tokens=result.input_tokens,
            output_tokens=result.output_tokens,
            request_id=result.request_id,
        )
        headline = output.headline
        if agent.is_simulation and not headline.upper().startswith("SIMULAZIONE"):
            headline = f"SIMULAZIONE — {headline}"
        report = AgentReport(
            agent=agent.name,
            status="completed",
            headline=headline,
            findings=kept,
            missing_information=sorted(set(output.missing_information) | set(missing)),
            confidence=output.confidence,
            limitations=output.limitations,
            sources=agent.sources(ctx),
            provider=llm.name,
            model=result.model,
            prompt_version=agent.prompt_version,
            rejected_findings=rejected,
            is_simulation=agent.is_simulation,
        )
        cache_put(
            session,
            key,
            agent=agent.name,
            prompt_version=agent.prompt_version,
            provider=llm.name,
            model=llm.model,
            response=report.model_dump(mode="json"),
        )
        latency = int((time.perf_counter() - start) * 1000)
        return _store(session, report, store, latency)

    return _store(
        session,
        _empty_report(agent, llm, ctx, "failed", f"risposta del modello non valida: {last_error}"),
        store,
        None,
    )

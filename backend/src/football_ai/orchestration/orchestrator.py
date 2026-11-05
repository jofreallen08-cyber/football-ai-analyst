"""Orchestrator: verified data → agents 1-4 (parallel) → contradictions → master → report.

Workflow (see docs/01-architecture.md §6):
1. receive a match; 2. build the verified context (data before kick-off);
3. reuse a previous run when data, prompts and model are unchanged (no AI calls);
4. run agents 1-4 concurrently, each in its own DB session and with a timeout;
5. detect contradictions deterministically; 6. master synthesis (or automatic fallback);
7. store the final report; 8. mark the run completed / partial / failed.
"""

from __future__ import annotations

import asyncio
import hashlib
import re
import uuid
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

from pydantic import ValidationError
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from football_ai.agents.registry import AGENTS
from football_ai.ai.budget import BudgetExceededError, check_budget
from football_ai.ai.cache import cache_get, cache_put, canonical_json, make_cache_key
from football_ai.ai.guard import GuardViolationError, check_no_betting
from football_ai.ai.llm.base import LLMError, LLMProvider
from football_ai.ai.prompts import load_prompt
from football_ai.ai.schemas import MASTER_OUTPUT_SCHEMA, AgentReport, MasterOutput
from football_ai.core.config import Settings
from football_ai.core.errors import NotFoundError
from football_ai.core.logging import get_logger
from football_ai.models import (
    AgentReportRow,
    AgentStatus,
    AIUsage,
    AnalysisRun,
    FinalReport,
    Match,
    RunStatus,
)
from football_ai.orchestration.contradictions import Contradiction, detect
from football_ai.schemas.analytics import MatchContext
from football_ai.services.agents import run_agent
from football_ai.services.analytics import match_context

log = get_logger(__name__)
AGENT_ORDER = ["match_analyst", "statistics", "team_intelligence", "simulation"]
MASTER_PROMPT_VERSION = "v1"
DISCLAIMER = (
    "Report a scopo educativo e di analisi sportiva. Non costituisce un pronostico garantito né un "
    "consiglio di scommessa. Le simulazioni sono scenari ipotetici e non risultati reali."
)
_NUM_RE = re.compile(r"\d+(?:[.,]\d+)?")
SessionFactory = Callable[[], Session]


def prompt_versions() -> dict[str, str]:
    return {**{n: AGENTS[n].prompt_version for n in AGENT_ORDER}, "master": MASTER_PROMPT_VERSION}


def data_hash(ctx: MatchContext) -> str:
    return hashlib.sha256(canonical_json(ctx.model_dump(mode="json")).encode()).hexdigest()


def find_reusable(
    session: Session, match_id: int, dhash: str, llm: LLMProvider, settings: Settings
) -> AnalysisRun | None:
    rows = session.scalars(
        select(AnalysisRun)
        .where(
            AnalysisRun.match_id == match_id,
            AnalysisRun.data_hash == dhash,
            AnalysisRun.provider == llm.name,
            AnalysisRun.model == llm.model,
            AnalysisRun.status.in_([RunStatus.COMPLETED, RunStatus.PARTIAL]),
        )
        .order_by(AnalysisRun.requested_at.desc())
    ).all()
    for r in rows:
        meta = r.context_snapshot.get("_meta", {})
        if (
            meta.get("prompt_versions") == prompt_versions()
            and meta.get("effort") == settings.ai_effort
        ):
            return r
    return None


def create_run(
    session: Session, settings: Settings, llm: LLMProvider, match_id: int, *, force: bool = False
) -> tuple[AnalysisRun, bool]:
    """Create a queued run, or return a reusable one (``reused=True``)."""
    if session.get(Match, match_id) is None:
        raise NotFoundError("Partita non trovata")
    ctx = match_context(session, match_id)
    dhash = data_hash(ctx)
    if not force:
        existing = find_reusable(session, match_id, dhash, llm, settings)
        if existing is not None:
            log.info("analysis_reused", run_id=str(existing.id))
            return existing, True
    snapshot = ctx.model_dump(mode="json")
    snapshot["_meta"] = {"prompt_versions": prompt_versions(), "effort": settings.ai_effort}
    run = AnalysisRun(
        match_id=match_id,
        status=RunStatus.QUEUED,
        data_hash=dhash,
        provider=llm.name,
        model=llm.model,
        context_snapshot=snapshot,
        requested_at=datetime.now(UTC),
    )
    session.add(run)
    session.commit()
    return run, False


# ----------------------------------------------------------------------------- master


def _report_payload(reports: dict[str, AgentReport]) -> dict[str, Any]:
    return {
        name: (
            {
                # "cached" and "completed" carry the same content: keep the master cache key stable
                "status": "completed",
                "headline": r.headline,
                "findings": [f.claim for f in r.findings],
                "missing_information": r.missing_information,
                "confidence": r.confidence,
                "is_simulation": r.is_simulation,
            }
            if r.status in ("completed", "cached")
            else {"status": r.status, "reason": r.limitations[:1] or [r.error]}
        )
        for name, r in reports.items()
    }


def _numbers(text: str) -> set[str]:
    return {n.replace(",", ".") for n in _NUM_RE.findall(text)}


def validate_master(
    out: MasterOutput,
    reports: dict[str, AgentReport],
    contradictions: list[Contradiction],
    ctx: MatchContext,
) -> None:
    usable = {n for n, r in reports.items() if r.status in ("completed", "cached")}
    for kf in out.key_findings:
        if kf.agent not in usable:
            raise GuardViolationError(
                f"key_finding attribuito a un agente senza report: {kf.agent}"
            )
    texts = [
        out.summary,
        *(k.finding for k in out.key_findings),
        *out.agreements,
        *(c.description + " " + c.assessment for c in out.contradictions),
        *out.missing_information,
    ]
    check_no_betting(texts)
    corpus = canonical_json(_report_payload(reports)) + " ".join(
        c.description for c in contradictions
    )
    corpus += f" {ctx.match.home_team.name} {ctx.match.away_team.name} {ctx.match.season_label}"
    allowed = _numbers(corpus) | {str(i) for i in range(11)}
    unknown = sorted({n for t in texts for n in _numbers(t)} - allowed)
    if unknown:
        raise GuardViolationError(f"numeri non presenti nei report: {unknown[:5]}")


def automatic_synthesis(
    reports: dict[str, AgentReport], contradictions: list[Contradiction], missing: list[str]
) -> MasterOutput:
    """Deterministic assembly used when the master model is unavailable (no new content)."""
    usable = [(n, r) for n, r in reports.items() if r.status in ("completed", "cached")]
    key_findings = [{"agent": n, "finding": r.findings[0].claim} for n, r in usable if r.findings]
    return MasterOutput.model_validate(
        {
            "summary": " ".join(r.headline for _, r in usable)
            or "Nessun agente ha prodotto un report con i dati disponibili.",
            "key_findings": key_findings,
            "agreements": [],
            "contradictions": [
                {
                    "description": c.description,
                    "agents": c.agents,
                    "assessment": "Non valutata (sintesi automatica).",
                }
                for c in contradictions
            ],
            "missing_information": sorted(set(missing)),
            "overall_confidence": "low",
        }
    )


async def run_master(
    session: Session,
    settings: Settings,
    llm: LLMProvider,
    ctx: MatchContext,
    reports: dict[str, AgentReport],
    contradictions: list[Contradiction],
    run_id: uuid.UUID,
) -> tuple[MasterOutput, str, str | None]:
    """Return (output, generated_by, error)."""
    missing = sorted(
        {m for r in reports.values() for m in r.missing_information} | set(ctx.missing)
    )
    if not any(r.status in ("completed", "cached") for r in reports.values()):
        return (
            automatic_synthesis(reports, contradictions, missing),
            "automatic",
            "nessun report disponibile",
        )
    m = ctx.match
    payload = {
        "match": f"{m.home_team.name} - {m.away_team.name} ({m.competition_name} {m.season_label})",
        "reports": _report_payload(reports),
        "detected_contradictions": [c.as_dict() for c in contradictions],
        "known_missing": missing,
    }
    key = make_cache_key(
        agent="master",
        prompt_version=MASTER_PROMPT_VERSION,
        provider=llm.name,
        model=llm.model,
        effort=settings.ai_effort,
        payload=payload,
    )
    cached = cache_get(session, key)
    if cached is not None:
        session.commit()
        return MasterOutput.model_validate(cached), "ai", None

    def usage(status: str, **kw: Any) -> None:
        session.add(
            AIUsage(
                analysis_run_id=run_id,
                agent="master",
                provider=llm.name,
                model=llm.model,
                status=status,
                **kw,
            )
        )
        session.commit()

    if llm.billable:
        try:
            check_budget(session, settings, llm.name, run_id)
        except BudgetExceededError as exc:
            usage("blocked", error=str(exc))
            return automatic_synthesis(reports, contradictions, missing), "automatic", str(exc)

    user = (
        "Sintetizza i report seguenti e rispondi esclusivamente con il JSON richiesto.\n"
        + canonical_json(payload)
    )
    error = ""
    for attempt in range(2):
        prompt = (
            user
            if attempt == 0
            else f"{user}\n\nLa risposta precedente non era valida ({error}). Correggila."
        )
        try:
            res = await llm.complete(
                agent="master",
                system=load_prompt("master", MASTER_PROMPT_VERSION),
                user=prompt,
                schema=MASTER_OUTPUT_SCHEMA,
                max_tokens=settings.ai_max_output_tokens * 2,
            )
        except LLMError as exc:
            usage("error", error=str(exc))
            return automatic_synthesis(reports, contradictions, missing), "automatic", str(exc)
        try:
            out = MasterOutput.model_validate(res.data)
            validate_master(out, reports, contradictions, ctx)
        except (ValidationError, GuardViolationError) as exc:
            error = str(exc)[:300]
            usage(
                "invalid",
                input_tokens=res.input_tokens,
                output_tokens=res.output_tokens,
                error=error,
            )
            continue
        usage(
            "ok",
            input_tokens=res.input_tokens,
            output_tokens=res.output_tokens,
            request_id=res.request_id,
        )
        cache_put(
            session,
            key,
            agent="master",
            prompt_version=MASTER_PROMPT_VERSION,
            provider=llm.name,
            model=llm.model,
            response=out.model_dump(mode="json"),
        )
        session.commit()
        return out, "ai", None
    return (
        automatic_synthesis(reports, contradictions, missing),
        "automatic",
        f"output non valido: {error}",
    )


def _cap_confidence(
    value: str, reports: dict[str, AgentReport], contradictions: list[Contradiction]
) -> str:
    order = ["low", "medium", "high"]
    problems = sum(1 for r in reports.values() if r.status in ("failed", "skipped"))
    warnings = sum(1 for c in contradictions if c.severity == "warning")
    cap = "high"
    if problems >= 2 or warnings >= 2:
        cap = "low"
    elif problems == 1 or warnings == 1:
        cap = "medium"
    return order[min(order.index(value), order.index(cap))]


# ----------------------------------------------------------------------------- execution


async def execute_run(
    factory: SessionFactory, settings: Settings, llm: LLMProvider, run_id: uuid.UUID
) -> None:
    with factory() as session:
        run = session.get_one(AnalysisRun, run_id)
        run.status = RunStatus.RUNNING
        run.started_at = datetime.now(UTC)
        session.commit()
        match_id = run.match_id
        try:
            ctx = match_context(session, match_id)
            sim_extra = AGENTS["simulation"].prepare(session, ctx)
        except Exception as exc:
            log.exception("analysis_context_failed", run_id=str(run_id))
            run.status, run.error, run.finished_at = RunStatus.FAILED, str(exc), datetime.now(UTC)
            session.commit()
            return

    async def one(name: str) -> AgentReport:
        with factory() as s:
            try:
                return await asyncio.wait_for(
                    run_agent(
                        s,
                        settings,
                        llm,
                        AGENTS[name],
                        ctx,
                        analysis_run_id=run_id,
                        extra=sim_extra if name == "simulation" else None,
                    ),
                    timeout=settings.ai_timeout_seconds,
                )
            except Exception as exc:  # timeout or unexpected error: record, never crash the run
                log.exception("agent_crashed", agent=name)
                s.rollback()
                rep = AgentReport(
                    agent=name,
                    status="failed",
                    headline="Analisi non disponibile",
                    findings=[],
                    missing_information=[],
                    confidence="low",
                    limitations=[f"Errore: {type(exc).__name__}"],
                    sources=[],
                    provider=llm.name,
                    model=llm.model,
                    prompt_version=AGENTS[name].prompt_version,
                    error=str(exc) or type(exc).__name__,
                    is_simulation=AGENTS[name].is_simulation,
                )
                s.add(
                    AgentReportRow(
                        analysis_run_id=run_id,
                        match_id=match_id,
                        agent=name,
                        status=AgentStatus.FAILED,
                        prompt_version=rep.prompt_version,
                        provider=llm.name,
                        model=llm.model,
                        cache_key="-",
                        output=rep.model_dump(mode="json"),
                        confidence="low",
                        error=rep.error,
                    )
                )
                s.commit()
                return rep

    results = await asyncio.gather(*(one(n) for n in AGENT_ORDER))
    reports = dict(zip(AGENT_ORDER, results, strict=True))
    sim_result = (sim_extra or {}).get("simulation")
    sim_dict = sim_result.model_dump(mode="json") if sim_result is not None else None
    contradictions = detect(ctx, reports, sim_dict)

    with factory() as session:
        output, generated_by, master_error = await run_master(
            session, settings, llm, ctx, reports, contradictions, run_id
        )
        confidence = _cap_confidence(output.overall_confidence, reports, contradictions)
        content = {
            **output.model_dump(mode="json"),
            "overall_confidence": confidence,
            "generated_by": generated_by,
            "master_error": master_error,
            "detected_contradictions": [c.as_dict() for c in contradictions],
            "agent_statuses": {n: r.status for n, r in reports.items()},
            "sources": [s.model_dump(mode="json") for s in ctx.sources],
            "data_as_of": ctx.as_of.isoformat(),
            "disclaimer": DISCLAIMER,
            "provider": llm.name,
            "model": llm.model,
        }
        session.add(
            FinalReport(
                analysis_run_id=run_id,
                match_id=match_id,
                summary=output.summary,
                content=content,
                confidence=confidence,
            )
        )
        run = session.get_one(AnalysisRun, run_id)
        failed = [n for n, r in reports.items() if r.status == "failed"]
        if len(failed) == len(reports):
            run.status = RunStatus.FAILED
        elif failed or (
            generated_by == "automatic" and master_error and "nessun report" not in master_error
        ):
            run.status = RunStatus.PARTIAL
        else:
            run.status = RunStatus.COMPLETED
        run.error = (
            "; ".join(
                filter(
                    None,
                    [f"agenti non riusciti: {', '.join(failed)}" if failed else None, master_error],
                )
            )[:2000]
            or None
        )
        run.finished_at = datetime.now(UTC)
        session.commit()
        log.info(
            "analysis_done", run_id=str(run_id), status=run.status.value, confidence=confidence
        )


def ai_usage_summary(session: Session) -> dict[str, Any]:
    day_start = datetime.combine(datetime.now(UTC).date(), datetime.min.time(), UTC)
    rows = session.execute(
        select(
            AIUsage.agent,
            func.count(AIUsage.id),
            func.coalesce(func.sum(AIUsage.input_tokens + AIUsage.output_tokens), 0),
        )
        .where(AIUsage.created_at >= day_start, AIUsage.status != "blocked")
        .group_by(AIUsage.agent)
    ).all()
    return {
        "by_agent": {a: int(c) for a, c, _ in rows},
        "calls": sum(int(c) for _, c, _ in rows),
        "tokens": sum(int(t) for _, _, t in rows),
    }

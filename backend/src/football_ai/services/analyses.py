"""Read side of analyses: status polling, final reports, history and Markdown export."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from football_ai.agents.registry import AGENTS
from football_ai.ai.schemas import AgentReport
from football_ai.core.errors import NotFoundError
from football_ai.models import AgentReportRow, AICache, AnalysisRun, FinalReport, RunStatus
from football_ai.orchestration.orchestrator import AGENT_ORDER
from football_ai.repositories import football as frepo
from football_ai.schemas.analysis import (
    AgentInfo,
    AgentSlot,
    AnalysisOut,
    AnalysisSummary,
    DetectedContradiction,
    FinalReportOut,
)

AGENT_INFO = {
    "match_analyst": (
        "Analizza forma recente, rendimento casa/trasferta, classifica e scontri diretti.",
        ["risultati", "classifica"],
    ),
    "statistics": (
        "Interpreta xG, tiri, possesso, calci d'angolo, disciplina e giocatori chiave.",
        ["statistiche di squadra", "xG", "statistiche giocatori"],
    ),
    "team_intelligence": (
        "Riassume indisponibilità verificate, formazioni e moduli.",
        ["indisponibilità", "formazioni"],
    ),
    "simulation": (
        "Spiega simulazioni Monte Carlo riproducibili (scenari ipotetici, non risultati reali).",
        ["risultati", "xG (opzionale)", "statistiche giocatori (per le assenze)"],
    ),
    "master": (
        "Confronta i report, individua accordi, contraddizioni e lacune e produce il report finale.",
        ["report degli altri agenti"],
    ),
}


def agent_catalogue() -> list[AgentInfo]:
    out = []
    for name in [*AGENT_ORDER, "master"]:
        desc, needs = AGENT_INFO[name]
        agent = AGENTS.get(name)
        out.append(
            AgentInfo(
                name=name,
                title=agent.title if agent else "Master Analyst",
                description=desc,
                data_needs=needs,
                is_simulation=bool(agent and agent.is_simulation),
            )
        )
    return out


def _final(session: Session, run: AnalysisRun) -> FinalReportOut | None:
    fr = session.scalar(select(FinalReport).where(FinalReport.analysis_run_id == run.id))
    if fr is None:
        return None
    c = fr.content
    return FinalReportOut(
        id=fr.id,
        analysis_run_id=run.id,
        match=frepo.get_match(session, run.match_id),
        created_at=fr.created_at,
        generated_by=c.get("generated_by", "ai"),
        provider=c.get("provider", run.provider),
        model=c.get("model", run.model),
        summary=fr.summary,
        key_findings=c.get("key_findings", []),
        agreements=c.get("agreements", []),
        contradictions=c.get("contradictions", []),
        detected_contradictions=[
            DetectedContradiction(**d) for d in c.get("detected_contradictions", [])
        ],
        missing_information=c.get("missing_information", []),
        confidence=fr.confidence,
        agent_statuses=c.get("agent_statuses", {}),
        sources=c.get("sources", []),
        data_as_of=datetime.fromisoformat(c["data_as_of"]),
        disclaimer=c.get("disclaimer", ""),
    )


def get_analysis(session: Session, run_id: uuid.UUID, reused: bool = False) -> AnalysisOut:
    run = session.get(AnalysisRun, run_id)
    if run is None:
        raise NotFoundError("Analisi non trovata")
    rows = {
        r.agent: r
        for r in session.scalars(
            select(AgentReportRow)
            .where(AgentReportRow.analysis_run_id == run_id)
            .order_by(AgentReportRow.id)
        )
    }
    slots = []
    for name in AGENT_ORDER:
        row = rows.get(name)
        if row is not None and row.output:
            report = AgentReport.model_validate(row.output)
            slots.append(
                AgentSlot(agent=name, title=AGENTS[name].title, status=report.status, report=report)
            )
        else:
            status = "running" if run.status == RunStatus.RUNNING else "pending"
            if run.status in (RunStatus.FAILED, RunStatus.COMPLETED, RunStatus.PARTIAL):
                status = "failed"
            slots.append(
                AgentSlot(agent=name, title=AGENTS[name].title, status=status, report=None)
            )
    return AnalysisOut(
        id=run.id,
        match=frepo.get_match(session, run.match_id),
        status=run.status.value,
        reused=reused,
        provider=run.provider,
        model=run.model,
        requested_at=run.requested_at,
        started_at=run.started_at,
        finished_at=run.finished_at,
        error=run.error,
        agents=slots,
        final_report=_final(session, run),
    )


def list_analyses(session: Session, match_id: int | None, limit: int) -> list[AnalysisSummary]:
    stmt = (
        select(AnalysisRun, FinalReport)
        .outerjoin(FinalReport, FinalReport.analysis_run_id == AnalysisRun.id)
        .order_by(AnalysisRun.requested_at.desc())
        .limit(limit)
    )
    if match_id is not None:
        stmt = stmt.where(AnalysisRun.match_id == match_id)
    out = []
    for run, fr in session.execute(stmt):
        out.append(
            AnalysisSummary(
                id=run.id,
                match=frepo.get_match(session, run.match_id),
                status=run.status.value,
                requested_at=run.requested_at,
                finished_at=run.finished_at,
                confidence=fr.confidence if fr else None,
                summary=(fr.summary[:280] if fr else None),
                generated_by=fr.content.get("generated_by") if fr else None,
            )
        )
    return out


CONF = {"low": "bassa", "medium": "media", "high": "alta"}
STATUS = {
    "completed": "completato",
    "cached": "da cache",
    "skipped": "saltato (dati insufficienti)",
    "failed": "non riuscito",
    "pending": "in attesa",
    "running": "in corso",
}


def export_markdown(session: Session, run_id: uuid.UUID) -> str:
    a = get_analysis(session, run_id)
    fr = a.final_report
    if fr is None:
        raise NotFoundError("Report finale non ancora disponibile")
    m = fr.match
    synthetic = " (DATI SINTETICI)" if m.is_synthetic else ""
    lines = [
        f"# Report di analisi: {m.home_team.name} – {m.away_team.name}{synthetic}",
        "",
        f"- Competizione: {m.competition_name} {m.season_label}"
        + (f", giornata {m.matchday}" if m.matchday else ""),
        f"- Calcio d'inizio: {m.kickoff_at:%d/%m/%Y %H:%M} UTC",
        f"- Dati aggiornati al: {fr.data_as_of:%d/%m/%Y %H:%M} UTC",
        f"- Confidenza complessiva: {CONF.get(fr.confidence, fr.confidence)}",
        f"- Generato da: {'AI' if fr.generated_by == 'ai' else 'sintesi automatica (senza AI)'} "
        f"({fr.provider} / {fr.model})",
        "",
        "## Sintesi",
        "",
        fr.summary,
        "",
        "## Punti chiave",
        "",
        *[
            f"- **{AGENTS[k['agent']].title if k['agent'] in AGENTS else k['agent']}**: {k['finding']}"
            for k in fr.key_findings
        ],
    ]
    if fr.agreements:
        lines += ["", "## Accordi tra agenti", "", *[f"- {x}" for x in fr.agreements]]
    if fr.contradictions:
        lines += ["", "## Contraddizioni", ""]
        lines += [
            f"- {c.get('description')} — *{c.get('assessment', '')}*" for c in fr.contradictions
        ]
    lines += [
        "",
        "## Informazioni mancanti",
        "",
        *[f"- {x}" for x in fr.missing_information or ["Nessuna"]],
    ]
    lines += ["", "## Report dei singoli agenti", ""]
    for slot in a.agents:
        lines.append(f"### {slot.title} — {STATUS.get(slot.status, slot.status)}")
        if slot.report:
            lines += ["", slot.report.headline, ""]
            lines += [
                f"- {f.claim} _(fonte dati: {', '.join(f.evidence_keys)})_"
                for f in slot.report.findings
            ]
        lines.append("")
    lines += ["## Fonti", ""]
    lines += [f"- {s.get('name')}: {s.get('attribution_text') or ''}" for s in fr.sources]
    lines += ["", "---", "", f"_{fr.disclaimer}_", ""]
    return "\n".join(lines)


def cache_stats(session: Session) -> tuple[int, int]:
    entries, hits = session.execute(
        select(func.count(AICache.cache_key), func.coalesce(func.sum(AICache.hit_count), 0))
    ).one()
    return int(entries), int(hits)

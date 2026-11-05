"""Agent runner against the seeded DB with mock / scripted providers (no network)."""

from __future__ import annotations

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from football_ai.agents.registry import AGENTS
from football_ai.ai.llm.base import LLMResult
from football_ai.ai.llm.mock import MockLLMProvider
from football_ai.core.config import Settings
from football_ai.models import AgentReportRow, AIUsage, Competition, Match, MatchStatus, Season
from football_ai.services.agents import run_agent
from football_ai.services.analytics import match_context

pytestmark = pytest.mark.db


def _settings(**kw) -> Settings:
    return Settings(_env_file=None, **kw)  # type: ignore[call-arg]


def _match(s: Session, code: str, status: MatchStatus) -> int:
    return s.scalar(
        select(Match.id)
        .join(Season, Season.id == Match.season_id)
        .join(Competition, Competition.id == Season.competition_id)
        .where(Competition.code == code, Match.status == status)
        .order_by(Match.kickoff_at.desc() if status == MatchStatus.FINISHED else Match.kickoff_at)
        .limit(1)
    )


class Scripted:
    """Billable fake provider returning queued outputs."""

    name = "scripted"
    model = "scripted-1"
    billable = True

    def __init__(self, outputs: list[dict]) -> None:
        self.outputs = outputs
        self.calls = 0

    async def complete(self, **kw) -> LLMResult:
        self.calls += 1
        return LLMResult(
            data=self.outputs.pop(0), input_tokens=100, output_tokens=50, model=self.model
        )


def _out(claim: str, keys: list[str]) -> dict:
    return {
        "headline": "Titolo",
        "confidence": "medium",
        "limitations": [],
        "missing_information": [],
        "findings": [{"claim": claim, "evidence_keys": keys, "strength": "medium"}],
    }


async def test_mock_run_then_cache_hit(seeded_engine) -> None:
    llm = MockLLMProvider()
    with Session(seeded_engine) as s:
        ctx = match_context(s, _match(s, "DEMO", MatchStatus.SCHEDULED))
        first = await run_agent(s, _settings(), llm, AGENTS["match_analyst"], ctx)
        second = await run_agent(s, _settings(), llm, AGENTS["match_analyst"], ctx)
    assert first.status == "completed" and second.status == "cached"
    assert llm.calls == ["match_analyst"]  # one provider call only
    assert first.findings == second.findings
    assert all(
        set(f.evidence_keys) <= set(AGENTS["match_analyst"].build_evidence(ctx))
        for f in first.findings
    )


async def test_real_league_skips_agents_without_data(seeded_engine) -> None:
    llm = MockLLMProvider()
    with Session(seeded_engine) as s:
        ctx = match_context(s, _match(s, "SA", MatchStatus.FINISHED))
        stats = await run_agent(s, _settings(), llm, AGENTS["statistics"], ctx)
        intel = await run_agent(s, _settings(), llm, AGENTS["team_intelligence"], ctx)
        analyst = await run_agent(s, _settings(), llm, AGENTS["match_analyst"], ctx)
    assert stats.status == "skipped" and intel.status == "skipped"
    assert analyst.status in ("completed", "cached")
    assert llm.calls.count("statistics") == 0 and llm.calls.count("team_intelligence") == 0
    assert any("xG" in m for m in stats.missing_information)


async def test_invalid_output_is_repaired_once(seeded_engine) -> None:
    with Session(seeded_engine) as s:
        ctx = match_context(s, _match(s, "DEMO", MatchStatus.SCHEDULED))
        llm = Scripted(
            [
                _out("Una scommessa sicura sulla squadra di casa", ["home.points"]),
                _out("La squadra di casa ha più punti", ["home.points"]),
            ]
        )
        rep = await run_agent(s, _settings(), llm, AGENTS["match_analyst"], ctx)
        statuses = s.scalars(select(AIUsage.status).where(AIUsage.provider == "scripted")).all()
    assert rep.status == "completed" and llm.calls == 2
    assert rep.findings[0].claim == "La squadra di casa ha più punti"
    assert sorted(statuses)[-2:] == ["invalid", "ok"]


async def test_ungrounded_output_fails_after_retry(seeded_engine) -> None:
    with Session(seeded_engine) as s:
        ctx = match_context(s, _match(s, "DEMO", MatchStatus.FINISHED))
        llm = Scripted([_out("Fatto inventato", ["nope"]), _out("Ancora inventato", ["nope2"])])
        rep = await run_agent(s, _settings(), llm, AGENTS["team_intelligence"], ctx)
    assert rep.status == "failed" and rep.findings == [] and llm.calls == 2
    assert "non valida" in (rep.error or "")


async def test_partially_grounded_output_keeps_valid_findings(seeded_engine) -> None:
    with Session(seeded_engine) as s:
        ctx = match_context(s, _match(s, "DEMO", MatchStatus.FINISHED))
        out = _out("Ok", ["home.matches"])
        out["findings"].append(
            {"claim": "Inventato", "evidence_keys": ["fake"], "strength": "high"}
        )
        rep = await run_agent(s, _settings(), Scripted([out]), AGENTS["statistics"], ctx)
    assert rep.status == "completed" and rep.rejected_findings == 1 and len(rep.findings) == 1


async def test_budget_blocks_billable_calls(seeded_engine) -> None:
    with Session(seeded_engine) as s:
        ctx = match_context(s, _match(s, "DEMO", MatchStatus.FINISHED))
        llm = Scripted([])
        rep = await run_agent(
            s, _settings(ai_daily_call_limit=0), llm, AGENTS["match_analyst"], ctx
        )
        blocked = s.scalar(select(func.count(AIUsage.id)).where(AIUsage.status == "blocked"))
        stored = s.scalar(
            select(func.count(AgentReportRow.id)).where(AgentReportRow.status == "failed")
        )
    assert rep.status == "failed" and llm.calls == 0
    assert "limite giornaliero" in (rep.error or "")
    assert blocked >= 1 and stored >= 1


async def test_single_agent_endpoint(api_client) -> None:
    comps = (await api_client.get("/api/v1/competitions")).json()
    demo = next(c for c in comps if c["code"] == "DEMO")["seasons"][0]["id"]
    m = (await api_client.get(f"/api/v1/matches?season_id={demo}&status=scheduled&limit=1")).json()
    mid = m["items"][0]["id"]
    r = await api_client.post(f"/api/v1/matches/{mid}/agents/statistics")
    assert r.status_code == 200
    body = r.json()
    assert body["agent"] == "statistics" and body["provider"] == "mock"
    assert body["status"] in ("completed", "cached")
    assert (await api_client.post(f"/api/v1/matches/{mid}/agents/master")).status_code == 422

"""End-to-end orchestration on the seeded DB with the offline provider (no network)."""

from __future__ import annotations

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from football_ai.ai.guard import GuardViolationError
from football_ai.ai.schemas import MasterOutput
from football_ai.models import AIUsage, Competition, Match, MatchStatus, Season
from football_ai.orchestration.orchestrator import validate_master
from football_ai.services.analytics import match_context

pytestmark = pytest.mark.db


async def _match(c, code: str, status: str) -> int:
    comps = (await c.get("/api/v1/competitions")).json()
    season = next(x for x in comps if x["code"] == code)["seasons"][0]["id"]
    order = "asc" if status == "scheduled" else "desc"
    page = (
        await c.get(f"/api/v1/matches?season_id={season}&status={status}&order={order}&limit=1")
    ).json()
    return page["items"][0]["id"]


def _usage_count(engine) -> int:
    with Session(engine) as s:
        return s.scalar(select(func.count(AIUsage.id))) or 0


async def test_full_analysis_reuse_and_force(api_client, seeded_engine) -> None:
    mid = await _match(api_client, "DEMO", "scheduled")
    r = await api_client.post("/api/v1/analyses", json={"match_id": mid})
    assert r.status_code == 202
    run_id = r.json()["id"]
    a = (await api_client.get(f"/api/v1/analyses/{run_id}")).json()
    assert a["status"] == "completed", a["error"]
    assert [s["agent"] for s in a["agents"]] == [
        "match_analyst",
        "statistics",
        "team_intelligence",
        "simulation",
    ]
    assert all(s["status"] in ("completed", "cached") for s in a["agents"])
    sim_slot = a["agents"][3]["report"]
    assert sim_slot["is_simulation"] and sim_slot["headline"].startswith("SIMULAZIONE")
    fr = a["final_report"]
    assert fr["generated_by"] == "ai" and fr["summary"]
    assert fr["disclaimer"].startswith("Report a scopo educativo")
    assert fr["agent_statuses"]["statistics"] in ("completed", "cached")
    assert fr["match"]["id"] == mid

    before = _usage_count(seeded_engine)
    again = await api_client.post("/api/v1/analyses", json={"match_id": mid})
    assert again.status_code == 200 and again.json()["reused"] and again.json()["id"] == run_id
    assert _usage_count(seeded_engine) == before  # no AI call at all

    forced = await api_client.post("/api/v1/analyses", json={"match_id": mid, "force": True})
    assert forced.status_code == 202 and forced.json()["id"] != run_id
    f = (await api_client.get(f"/api/v1/analyses/{forced.json()['id']}")).json()
    assert all(s["status"] == "cached" for s in f["agents"])
    assert _usage_count(seeded_engine) == before  # served from the AI cache

    md = await api_client.get(f"/api/v1/analyses/{run_id}/report.md")
    assert md.status_code == 200 and md.headers["content-type"].startswith("text/markdown")
    assert "# Report di analisi" in md.text and "DATI SINTETICI" in md.text
    assert "## Informazioni mancanti" in md.text and "scommessa" in md.text

    listed = (await api_client.get(f"/api/v1/analyses?match_id={mid}")).json()
    assert {x["id"] for x in listed} >= {run_id, forced.json()["id"]}


async def test_real_league_analysis_skips_unsupported_agents(api_client) -> None:
    mid = await _match(api_client, "SA", "finished")
    run_id = (await api_client.post("/api/v1/analyses", json={"match_id": mid})).json()["id"]
    a = (await api_client.get(f"/api/v1/analyses/{run_id}")).json()
    st = {s["agent"]: s["status"] for s in a["agents"]}
    assert st["statistics"] == "skipped" and st["team_intelligence"] == "skipped"
    assert st["match_analyst"] in ("completed", "cached") and st["simulation"] in (
        "completed",
        "cached",
    )
    assert a["status"] == "completed"
    assert a["final_report"]["confidence"] == "low"  # two agents without data
    assert any("xG" in m for m in a["final_report"]["missing_information"])


async def test_agent_crash_gives_partial_run(api_client, monkeypatch) -> None:
    from football_ai.agents.registry import AGENTS

    def boom(*a, **k):
        raise RuntimeError("guasto simulato")

    monkeypatch.setattr(AGENTS["team_intelligence"], "build_evidence", boom)
    mid = await _match(api_client, "DEMO", "finished")
    run_id = (
        await api_client.post("/api/v1/analyses", json={"match_id": mid, "force": True})
    ).json()["id"]
    a = (await api_client.get(f"/api/v1/analyses/{run_id}")).json()
    assert a["status"] == "partial"
    slot = next(s for s in a["agents"] if s["agent"] == "team_intelligence")
    assert slot["status"] == "failed" and "guasto simulato" in slot["report"]["error"]
    assert a["final_report"] is not None and a["final_report"]["confidence"] != "high"


def test_master_cannot_introduce_new_numbers_or_agents(seeded_engine) -> None:
    from football_ai.ai.schemas import AgentReport, Finding

    with Session(seeded_engine) as s:
        mid = s.scalar(
            select(Match.id)
            .join(Season, Season.id == Match.season_id)
            .join(Competition, Competition.id == Season.competition_id)
            .where(Competition.code == "DEMO", Match.status == MatchStatus.SCHEDULED)
            .limit(1)
        )
        ctx = match_context(s, mid)
    reports = {
        "match_analyst": AgentReport(
            agent="match_analyst",
            status="completed",
            headline="Casa in forma",
            confidence="medium",
            findings=[
                Finding(
                    claim="La squadra di casa ha 18 punti", evidence_keys=["k"], strength="medium"
                )
            ],
            missing_information=[],
            limitations=[],
            sources=[],
            provider="p",
            model="m",
            prompt_version="v1",
        )
    }
    base = {
        "summary": "La squadra di casa ha 18 punti.",
        "agreements": [],
        "contradictions": [],
        "missing_information": [],
        "overall_confidence": "medium",
        "key_findings": [{"agent": "match_analyst", "finding": "18 punti"}],
    }
    validate_master(MasterOutput.model_validate(base), reports, [], ctx)
    with pytest.raises(GuardViolationError, match="numeri"):
        validate_master(
            MasterOutput.model_validate({**base, "summary": "Vincerà con il 73% di sicurezza."}),
            reports,
            [],
            ctx,
        )
    with pytest.raises(GuardViolationError, match="agente"):
        validate_master(
            MasterOutput.model_validate(
                {**base, "key_findings": [{"agent": "statistics", "finding": "x"}]}
            ),
            reports,
            [],
            ctx,
        )
    with pytest.raises(GuardViolationError, match="scommesse"):
        validate_master(
            MasterOutput.model_validate({**base, "summary": "Ottima scommessa."}), reports, [], ctx
        )


async def test_catalogue_usage_and_errors(api_client) -> None:
    cat = (await api_client.get("/api/v1/agents")).json()
    assert [c["name"] for c in cat] == [
        "match_analyst",
        "statistics",
        "team_intelligence",
        "simulation",
        "master",
    ]
    assert next(c for c in cat if c["name"] == "simulation")["is_simulation"]
    u = (await api_client.get("/api/v1/ai/usage")).json()
    assert u["provider"] == "mock" and u["billable"] is False and u["limits"]["daily_calls"] == 100
    assert (
        await api_client.post("/api/v1/analyses", json={"match_id": 99999999})
    ).status_code == 404
    assert (
        await api_client.get("/api/v1/analyses/00000000-0000-0000-0000-000000000000")
    ).status_code == 404
    assert (await api_client.get("/api/v1/analyses/not-a-uuid")).status_code == 422

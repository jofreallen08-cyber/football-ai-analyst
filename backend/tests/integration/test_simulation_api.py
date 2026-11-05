from __future__ import annotations

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from football_ai.agents.registry import AGENTS
from football_ai.ai.llm.mock import MockLLMProvider
from football_ai.core.config import Settings
from football_ai.services.agents import run_agent
from football_ai.services.analytics import match_context

pytestmark = pytest.mark.db


async def _demo(c):
    comps = (await c.get("/api/v1/competitions")).json()
    season = next(x for x in comps if x["code"] == "DEMO")["seasons"][0]["id"]
    up = (await c.get(f"/api/v1/matches?season_id={season}&status=scheduled&limit=1")).json()
    return season, up["items"][0]


async def test_baseline_simulation_is_labelled_and_reproducible(api_client) -> None:
    _, m = await _demo(api_client)
    body = {"match_id": m["id"], "seed": 11, "n_iterations": 5000}
    r1 = await api_client.post("/api/v1/simulations", json=body)
    r2 = await api_client.post("/api/v1/simulations", json=body)
    assert r1.status_code == 201
    a, b = r1.json(), r2.json()
    assert a["is_simulation"] is True and a["label"].startswith("SIMULAZIONE")
    assert a["baseline"] == b["baseline"] and a["id"] != b["id"]
    assert a["scenario"] is None and a["is_synthetic_data"] is True
    assert any("SINTETICI" in x for x in a["limitations"])
    assert a["training_window"]["uses_xg"] is True
    got = (await api_client.get(f"/api/v1/simulations/{a['id']}")).json()
    assert got["baseline"] == a["baseline"]


async def test_scenario_with_absence_and_formation(api_client) -> None:
    _, m = await _demo(api_client)
    opts = (await api_client.get(f"/api/v1/simulations/options?match_id={m['id']}")).json()
    top = max(opts["home_players"], key=lambda p: p["xg_share"] or 0)
    body = {
        "match_id": m["id"],
        "seed": 3,
        "n_iterations": 10000,
        "unavailable_player_ids": [top["player_id"]],
        "away_formation": "5-4-1",
    }
    s = (await api_client.post("/api/v1/simulations", json=body)).json()
    assert s["scenario"] is not None
    assert s["scenario"]["expected_goals_home"] < s["baseline"]["expected_goals_home"]
    assert any(top["name"] in x for x in s["assumptions"])
    hist = (await api_client.get("/api/v1/simulations")).json()
    assert any(h["id"] == s["id"] and h["has_scenario"] for h in hist)


@pytest.mark.parametrize(
    "body,status",
    [
        ({"seed": 1}, 422),
        ({"season_id": 1, "home_team_id": 5, "away_team_id": 5}, 422),
        ({"match_id": 1, "n_iterations": 10}, 422),
        ({"match_id": 1, "home_formation": "9-0-1"}, 422),
        ({"match_id": 99999999}, 404),
        ({"match_id": 1, "unavailable_player_ids": [99999999]}, 422),
    ],
)
async def test_invalid_requests(api_client, body, status) -> None:
    _, m = await _demo(api_client)
    if body.get("match_id") == 1:
        body = {**body, "match_id": m["id"]}
    assert (await api_client.post("/api/v1/simulations", json=body)).status_code == status


async def test_first_matchday_has_no_training_data(api_client) -> None:
    season, _ = await _demo(api_client)
    first = (await api_client.get(f"/api/v1/matches?season_id={season}&limit=1")).json()["items"][0]
    r = await api_client.post("/api/v1/simulations", json={"match_id": first["id"]})
    assert r.status_code == 404 and "insufficienti" in r.json()["detail"]


def test_database_rejects_non_simulation_rows(seeded_engine) -> None:
    with Session(seeded_engine) as s, pytest.raises(IntegrityError):
        s.execute(text("UPDATE simulation_runs SET is_simulation = false"))
        s.execute(
            text(
                "INSERT INTO simulation_runs (id, season_id, home_team_id, away_team_id, scenario, assumptions, "
                "limitations, model_version, seed, n_iterations, training_window, results, is_simulation) "
                "SELECT gen_random_uuid(), 1, 1, 2, '{}', '[]', '[]', 'x', 1, 1000, '{}', '{}', false"
            )
        )


async def test_simulation_agent_report(seeded_engine) -> None:
    from sqlalchemy import select

    from football_ai.models import Match, MatchStatus

    with Session(seeded_engine) as s:
        mid = s.scalar(
            select(Match.id)
            .where(Match.status == MatchStatus.SCHEDULED)
            .order_by(Match.kickoff_at)
            .limit(1)
        )
        ctx = match_context(s, mid)
        rep = await run_agent(
            s, Settings(_env_file=None), MockLLMProvider(), AGENTS["simulation"], ctx
        )  # type: ignore[call-arg]
    assert rep.status in ("completed", "cached") and rep.is_simulation
    assert rep.headline.startswith("SIMULAZIONE")
    assert all(k.startswith(("sim.", "meta.")) for f in rep.findings for k in f.evidence_keys)

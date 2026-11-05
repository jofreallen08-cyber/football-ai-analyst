from __future__ import annotations

import pytest

pytestmark = pytest.mark.db


async def _seasons(c):
    comps = {x["code"]: x for x in (await c.get("/api/v1/competitions")).json()}
    return comps["DEMO"]["seasons"][0]["id"], comps["SA"]["seasons"][0]["id"]


async def test_standings_real_league(api_client) -> None:
    _, sa = await _seasons(api_client)
    d = (await api_client.get(f"/api/v1/seasons/{sa}/standings")).json()
    assert len(d["rows"]) == 20 and d["rows"][0]["position"] == 1
    assert sum(r["played"] for r in d["rows"]) == 2 * 380
    assert "scontri diretti" in d["tie_break_note"]


async def test_context_for_real_league_declares_missing_data(api_client) -> None:
    _, sa = await _seasons(api_client)
    m = (await api_client.get(f"/api/v1/matches?season_id={sa}&order=desc&limit=1")).json()
    ctx = (await api_client.get(f"/api/v1/matches/{m['items'][0]['id']}/context")).json()
    assert ctx["capabilities"] == {
        "xg": False,
        "lineups": False,
        "player_stats": False,
        "availability": False,
    }
    assert any("xG" in x for x in ctx["missing"])
    assert ctx["home"]["availability"] == []


async def test_context_uses_only_data_before_kickoff(api_client) -> None:
    demo, _ = await _seasons(api_client)
    first = (await api_client.get(f"/api/v1/matches?season_id={demo}&limit=1")).json()
    ctx = (await api_client.get(f"/api/v1/matches/{first['items'][0]['id']}/context")).json()
    assert ctx["home"]["form_last5"]["sample_size"] == 0
    assert ctx["home"]["position"] is None
    assert ctx["home"]["last_lineup"] is None


async def test_context_upcoming_demo_match(api_client) -> None:
    demo, _ = await _seasons(api_client)
    up = (await api_client.get(f"/api/v1/matches?season_id={demo}&status=scheduled&limit=1")).json()
    ctx = (await api_client.get(f"/api/v1/matches/{up['items'][0]['id']}/context")).json()
    assert ctx["capabilities"]["xg"] and ctx["capabilities"]["lineups"]
    assert ctx["home"]["form_last5"]["sample_size"] == 5
    assert ctx["home"]["last_lineup"]["formation"]
    assert "Formazioni ufficiali non ancora annunciate" in ctx["missing"]
    assert ctx["sources"][0]["is_synthetic"] is True


async def test_team_and_player_analytics(api_client) -> None:
    demo, sa = await _seasons(api_client)
    team = (await api_client.get("/api/v1/teams?q=Montevento")).json()[0]["id"]
    ta = (await api_client.get(f"/api/v1/teams/{team}/analytics?season_id={demo}")).json()
    assert ta["has_xg"] and len(ta["xg_series"]) == 11
    assert ta["form_last5"]["sample_size"] == 5
    wrong = await api_client.get(f"/api/v1/teams/{team}/analytics?season_id={sa}")
    assert wrong.status_code == 404
    lead = (await api_client.get(f"/api/v1/seasons/{demo}/player-leaders?metric=goals")).json()
    assert len(lead["items"]) == 10
    goals = [i["aggregate"]["totals"]["goals"] for i in lead["items"]]
    assert goals == sorted(goals, reverse=True)
    pid = lead["items"][0]["player_id"]
    pa = (await api_client.get(f"/api/v1/players/{pid}/analytics?season_id={demo}")).json()
    assert pa["aggregate"]["totals"]["goals"] == goals[0]
    bad = await api_client.get(f"/api/v1/seasons/{demo}/player-leaders?metric=rating")
    assert bad.status_code == 422


async def test_overview(api_client) -> None:
    ov = (await api_client.get("/api/v1/overview")).json()
    assert ov["totals"]["competitions"] >= 2
    assert all(m["status"] == "finished" for m in ov["recent"])
    assert all(m["status"] == "scheduled" for m in ov["upcoming"])

"""Read API against the seeded test database."""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.db


async def test_competitions_and_sources(api_client) -> None:
    comps = (await api_client.get("/api/v1/competitions")).json()
    by_code = {c["code"]: c for c in comps}
    assert by_code["DEMO"]["is_synthetic"] is True
    assert by_code["SA"]["is_synthetic"] is False
    assert by_code["SA"]["seasons"][0]["label"] == "2025/26"
    sources = (await api_client.get("/api/v1/sources")).json()
    assert {s["key"] for s in sources} >= {"local_sample", "openfootball"}
    assert all(s["attribution_text"] for s in sources if s["key"] != "fake")


async def test_match_list_filters_and_pagination(api_client) -> None:
    comps = (await api_client.get("/api/v1/competitions")).json()
    sa = next(c for c in comps if c["code"] == "SA")["seasons"][0]["id"]
    page = (await api_client.get(f"/api/v1/matches?season_id={sa}&limit=5&offset=5")).json()
    assert page["total"] == 380 and len(page["items"]) == 5 and page["offset"] == 5
    first = page["items"][0]
    assert first["has_team_stats"] is False and first["source"] == "openfootball"

    team_id = first["home_team"]["id"]
    tp = (
        await api_client.get(f"/api/v1/matches?season_id={sa}&team_id={team_id}&limit=200")
    ).json()
    assert tp["total"] == 38
    assert all(team_id in (m["home_team"]["id"], m["away_team"]["id"]) for m in tp["items"])


async def test_match_detail_with_stats_lineups_and_provenance(api_client) -> None:
    comps = (await api_client.get("/api/v1/competitions")).json()
    demo = next(c for c in comps if c["code"] == "DEMO")["seasons"][0]["id"]
    page = (
        await api_client.get(f"/api/v1/matches?season_id={demo}&status=finished&limit=1")
    ).json()
    detail = (await api_client.get(f"/api/v1/matches/{page['items'][0]['id']}")).json()
    assert len(detail["team_stats"]) == 2
    home = detail["team_stats"][0]
    assert home["is_home"] is True and home["xg"] is not None
    assert home["xga"] == detail["team_stats"][1]["xg"]
    assert home["offsides"] is None  # not provided by the source
    assert len(detail["lineups"]) == 2
    starters = [e for e in detail["lineups"][0]["entries"] if e["role"] == "starter"]
    assert len(starters) == 11 and all(e["grid_x"] is not None for e in starters)
    assert detail["provenance"]["is_synthetic"] is True
    assert "SINTETICI" in detail["attribution"]


async def test_teams_players_and_search(api_client) -> None:
    teams = (await api_client.get("/api/v1/teams?q=internazionale")).json()
    assert teams[0]["name"] == "FC Internazionale Milano"
    team = (await api_client.get(f"/api/v1/teams/{teams[0]['id']}")).json()
    assert team["seasons"][0]["competition_code"] == "SA"
    demo_team = (await api_client.get("/api/v1/teams?q=Montevento")).json()[0]
    players = (await api_client.get(f"/api/v1/players?team_id={demo_team['id']}&limit=50")).json()
    assert players["total"] == 20
    p = (await api_client.get(f"/api/v1/players/{players['items'][0]['id']}")).json()
    assert p["team"]["id"] == demo_team["id"]


async def test_search_wildcards_are_escaped(api_client) -> None:
    assert (await api_client.get("/api/v1/teams?q=%25")).json() == []


@pytest.mark.parametrize(
    "path,status",
    [
        ("/api/v1/matches/999999", 404),
        ("/api/v1/teams/999999", 404),
        ("/api/v1/players/999999", 404),
        ("/api/v1/matches/0", 422),
        ("/api/v1/matches?limit=500", 422),
        ("/api/v1/matches?status=boh", 422),
        ("/api/v1/teams?q=", 422),
    ],
)
async def test_input_validation_and_not_found(api_client, path, status) -> None:
    resp = await api_client.get(path)
    assert resp.status_code == status
    assert resp.headers["content-type"].startswith("application/problem+json")


async def test_ingestion_runs_listed(api_client) -> None:
    runs = (await api_client.get("/api/v1/ingestion-runs")).json()
    assert any(r["source"] == "openfootball" and r["status"] == "success" for r in runs)

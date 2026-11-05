"""Analytics endpoints (deterministic, no AI involved)."""

from __future__ import annotations

from typing import Annotated, Literal

from fastapi import APIRouter, Path, Query

from football_ai.api.deps import SessionDep
from football_ai.schemas.analytics import (
    MatchContext,
    OverviewOut,
    PlayerAnalytics,
    PlayerLeadersOut,
    StandingsOut,
    TeamAnalytics,
)
from football_ai.services import analytics as svc

router = APIRouter(tags=["analisi"])
Id = Annotated[int, Path(ge=1, le=2**62)]
SeasonId = Annotated[int, Query(ge=1, le=2**62)]
Metric = Literal[
    "goals",
    "assists",
    "shots",
    "shots_on_target",
    "xg",
    "xa",
    "key_passes",
    "tackles",
    "interceptions",
    "yellow_cards",
    "red_cards",
]


@router.get("/overview", response_model=OverviewOut, summary="Panoramica")
def overview(session: SessionDep) -> OverviewOut:
    return svc.overview(session)


@router.get("/seasons/{season_id}/standings", response_model=StandingsOut, summary="Classifica")
def standings(session: SessionDep, season_id: Id) -> StandingsOut:
    return svc.standings(session, season_id)


@router.get(
    "/seasons/{season_id}/player-leaders",
    response_model=PlayerLeadersOut,
    summary="Migliori giocatori per metrica",
)
def player_leaders(
    session: SessionDep,
    season_id: Id,
    metric: Metric = "goals",
    per90: bool = False,
    team_id: Annotated[int | None, Query(ge=1, le=2**62)] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 10,
) -> PlayerLeadersOut:
    return svc.player_leaders(session, season_id, metric, per90=per90, team_id=team_id, limit=limit)


@router.get("/teams/{team_id}/analytics", response_model=TeamAnalytics, summary="Analisi squadra")
def team_analytics(session: SessionDep, team_id: Id, season_id: SeasonId) -> TeamAnalytics:
    return svc.team_analytics(session, team_id, season_id)


@router.get(
    "/players/{player_id}/analytics", response_model=PlayerAnalytics, summary="Analisi giocatore"
)
def player_analytics(session: SessionDep, player_id: Id, season_id: SeasonId) -> PlayerAnalytics:
    return svc.player_analytics(session, player_id, season_id)


@router.get(
    "/matches/{match_id}/context",
    response_model=MatchContext,
    summary="Contesto pre-partita verificato (input degli agenti AI)",
)
def match_context(session: SessionDep, match_id: Id) -> MatchContext:
    return svc.match_context(session, match_id)

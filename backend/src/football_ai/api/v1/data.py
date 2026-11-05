"""Read endpoints: sources, competitions, teams, matches, players, ingestion runs."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Literal

from fastapi import APIRouter, Path, Query

from football_ai.api.deps import Limit, Offset, SearchQuery, SessionDep
from football_ai.models import MatchStatus
from football_ai.repositories import football as repo
from football_ai.schemas.common import Page
from football_ai.schemas.football import (
    CompetitionOut,
    IngestionRunOut,
    MatchDetail,
    MatchOut,
    PlayerOut,
    SourceOut,
    TeamDetail,
    TeamOut,
)

router = APIRouter(tags=["dati"])
Id = Annotated[int, Path(ge=1, le=2**62)]
OptId = Annotated[int | None, Query(ge=1, le=2**62)]


@router.get("/sources", response_model=list[SourceOut], summary="Fonti dati e licenze")
def sources(session: SessionDep) -> list[SourceOut]:
    return repo.list_sources(session)


@router.get("/competitions", response_model=list[CompetitionOut], summary="Competizioni e stagioni")
def competitions(session: SessionDep) -> list[CompetitionOut]:
    return repo.list_competitions(session)


@router.get("/teams", response_model=list[TeamOut], summary="Squadre")
def teams(session: SessionDep, season_id: OptId = None, q: SearchQuery = None) -> list[TeamOut]:
    return repo.list_teams(session, season_id=season_id, q=q)


@router.get("/teams/{team_id}", response_model=TeamDetail, summary="Dettaglio squadra")
def team(session: SessionDep, team_id: Id) -> TeamDetail:
    return repo.get_team(session, team_id)


@router.get("/matches", response_model=Page[MatchOut], summary="Partite")
def matches(
    session: SessionDep,
    season_id: OptId = None,
    team_id: OptId = None,
    status: MatchStatus | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    order: Literal["asc", "desc"] = "asc",
    limit: Limit = 50,
    offset: Offset = 0,
) -> Page[MatchOut]:
    return repo.list_matches(
        session,
        season_id=season_id,
        team_id=team_id,
        status=status,
        date_from=date_from,
        date_to=date_to,
        order=order,
        limit=limit,
        offset=offset,
    )


@router.get("/matches/{match_id}", response_model=MatchDetail, summary="Dettaglio partita")
def match(session: SessionDep, match_id: Id) -> MatchDetail:
    return repo.get_match(session, match_id)


@router.get("/players", response_model=Page[PlayerOut], summary="Giocatori")
def players(
    session: SessionDep,
    team_id: OptId = None,
    season_id: OptId = None,
    q: SearchQuery = None,
    limit: Limit = 50,
    offset: Offset = 0,
) -> Page[PlayerOut]:
    return repo.list_players(
        session, team_id=team_id, season_id=season_id, q=q, limit=limit, offset=offset
    )


@router.get("/players/{player_id}", response_model=PlayerOut, summary="Dettaglio giocatore")
def player(session: SessionDep, player_id: Id) -> PlayerOut:
    return repo.get_player(session, player_id)


@router.get("/ingestion-runs", response_model=list[IngestionRunOut], summary="Storico importazioni")
def ingestion_runs(session: SessionDep, limit: Limit = 20) -> list[IngestionRunOut]:
    return repo.list_ingestion_runs(session, limit)

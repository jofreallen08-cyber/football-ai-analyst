"""Read queries for the football domain. Returns API schemas, never ORM objects."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from typing import Any, Literal

from sqlalchemy import Select, and_, func, or_, select, true
from sqlalchemy.orm import Session, aliased

from football_ai.core.errors import NotFoundError
from football_ai.models import (
    Competition,
    DataSource,
    IngestionIssue,
    IngestionRun,
    IssueSeverity,
    Lineup,
    LineupEntry,
    Match,
    MatchStatus,
    MatchTeamStats,
    Player,
    Season,
    SquadMembership,
    Team,
)
from football_ai.schemas.common import Page
from football_ai.schemas.football import (
    CompetitionOut,
    CompetitionSeasonRef,
    IngestionRunOut,
    LineupEntryOut,
    LineupOut,
    MatchDetail,
    MatchOut,
    PlayerOut,
    Provenance,
    SeasonOut,
    SourceOut,
    TeamDetail,
    TeamOut,
    TeamRef,
    TeamStatsOut,
)

Home = aliased(Team, name="home")
Away = aliased(Team, name="away")


def _sources(session: Session) -> dict[int, DataSource]:
    return {s.id: s for s in session.scalars(select(DataSource))}


def list_sources(session: Session) -> list[SourceOut]:
    rows = session.scalars(select(DataSource).order_by(DataSource.key))
    return [SourceOut.model_validate(r) for r in rows]


def list_competitions(session: Session) -> list[CompetitionOut]:
    src = _sources(session)
    comps = session.scalars(select(Competition).order_by(Competition.name)).all()
    seasons = session.scalars(select(Season).order_by(Season.label.desc())).all()
    by_comp: dict[int, list[SeasonOut]] = {}
    for s in seasons:
        by_comp.setdefault(s.competition_id, []).append(SeasonOut.model_validate(s))
    return [
        CompetitionOut(
            id=c.id,
            name=c.name,
            code=c.code,
            country=c.country,
            type=c.type.value,
            source=src[c.source_id].key,
            is_synthetic=src[c.source_id].is_synthetic,
            seasons=by_comp.get(c.id, []),
        )
        for c in comps
    ]


def get_season(session: Session, season_id: int) -> Season:
    season = session.get(Season, season_id)
    if season is None:
        raise NotFoundError("Stagione non trovata")
    return season


def _team_ref(t: Team) -> TeamRef:
    return TeamRef(id=t.id, name=t.name, short_name=t.short_name)


def _team_out(t: Team, src: dict[int, DataSource]) -> TeamOut:
    return TeamOut(
        id=t.id,
        name=t.name,
        short_name=t.short_name,
        country=t.country,
        founded=t.founded,
        source=src[t.source_id].key,
        is_synthetic=src[t.source_id].is_synthetic,
    )


def list_teams(
    session: Session, *, season_id: int | None = None, q: str | None = None
) -> list[TeamOut]:
    stmt = select(Team)
    if season_id is not None:
        in_season = (
            select(Match.home_team_id)
            .where(Match.season_id == season_id)
            .union(select(Match.away_team_id).where(Match.season_id == season_id))
        )
        stmt = stmt.where(Team.id.in_(in_season))
    if q:
        stmt = stmt.where(Team.name.ilike(f"%{_escape_like(q)}%", escape="\\"))
    src = _sources(session)
    return [_team_out(t, src) for t in session.scalars(stmt.order_by(Team.name))]


def team_seasons(session: Session, team_id: int) -> list[CompetitionSeasonRef]:
    stmt = (
        select(Season.id, Season.label, Competition.id, Competition.name, Competition.code)
        .join(Competition, Competition.id == Season.competition_id)
        .where(
            Season.id.in_(
                select(Match.season_id).where(
                    or_(Match.home_team_id == team_id, Match.away_team_id == team_id)
                )
            )
        )
        .order_by(Season.label.desc(), Competition.name)
    )
    return [
        CompetitionSeasonRef(
            season_id=r[0],
            season_label=r[1],
            competition_id=r[2],
            competition_name=r[3],
            competition_code=r[4],
        )
        for r in session.execute(stmt)
    ]


def get_team(session: Session, team_id: int) -> TeamDetail:
    team = session.get(Team, team_id)
    if team is None:
        raise NotFoundError("Squadra non trovata")
    base = _team_out(team, _sources(session))
    return TeamDetail(**base.model_dump(), seasons=team_seasons(session, team_id))


def _match_select() -> Select[Any]:
    has_stats = (
        select(func.count(MatchTeamStats.id))
        .where(MatchTeamStats.match_id == Match.id)
        .correlate(Match)
        .scalar_subquery()
    )
    return (
        select(Match, Home, Away, Season, Competition, DataSource, has_stats)
        .join(Home, Home.id == Match.home_team_id)
        .join(Away, Away.id == Match.away_team_id)
        .join(Season, Season.id == Match.season_id)
        .join(Competition, Competition.id == Season.competition_id)
        .join(DataSource, DataSource.id == Match.source_id)
    )


def _match_out(row: Sequence[Any]) -> MatchOut:
    m, home, away, season, comp, src, n_stats = row
    return MatchOut(
        id=m.id,
        season_id=m.season_id,
        competition_code=comp.code,
        competition_name=comp.name,
        season_label=season.label,
        matchday=m.matchday,
        kickoff_at=m.kickoff_at,
        status=m.status.value,
        home_team=_team_ref(home),
        away_team=_team_ref(away),
        home_score=m.home_score,
        away_score=m.away_score,
        home_score_ht=m.home_score_ht,
        away_score_ht=m.away_score_ht,
        has_team_stats=bool(n_stats),
        source=src.key,
        is_synthetic=src.is_synthetic,
    )


def list_matches(
    session: Session,
    *,
    season_id: int | None = None,
    team_id: int | None = None,
    status: MatchStatus | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    order: Literal["asc", "desc"] = "asc",
    limit: int = 50,
    offset: int = 0,
) -> Page[MatchOut]:
    conds = []
    if season_id is not None:
        conds.append(Match.season_id == season_id)
    if team_id is not None:
        conds.append(or_(Match.home_team_id == team_id, Match.away_team_id == team_id))
    if status is not None:
        conds.append(Match.status == status)
    if date_from is not None:
        conds.append(Match.kickoff_at >= date_from)
    if date_to is not None:
        conds.append(Match.kickoff_at <= date_to)
    where = and_(*conds) if conds else None
    stmt = _match_select()
    count = select(func.count(Match.id))
    if where is not None:
        stmt = stmt.where(where)
        count = count.where(where)
    sort = Match.kickoff_at.asc() if order == "asc" else Match.kickoff_at.desc()
    rows = session.execute(stmt.order_by(sort, Match.id).limit(limit).offset(offset)).all()
    return Page[MatchOut](
        items=[_match_out(r) for r in rows],
        total=session.scalar(count) or 0,
        limit=limit,
        offset=offset,
    )


def get_match(session: Session, match_id: int) -> MatchDetail:
    row = session.execute(_match_select().where(Match.id == match_id)).first()
    if row is None:
        raise NotFoundError("Partita non trovata")
    base = _match_out(row)
    m: Match = row[0]
    src: DataSource = row[5]
    stats = session.scalars(
        select(MatchTeamStats)
        .where(MatchTeamStats.match_id == match_id)
        .order_by(MatchTeamStats.is_home.desc())
    ).all()
    lineups = []
    for lu in session.scalars(select(Lineup).where(Lineup.match_id == match_id)):
        entries = session.execute(
            select(LineupEntry, Player.full_name)
            .join(Player, Player.id == LineupEntry.player_id)
            .where(LineupEntry.lineup_id == lu.id)
            .order_by(LineupEntry.role, LineupEntry.grid_x.nulls_last(), LineupEntry.id)
        ).all()
        lineups.append(
            LineupOut(
                team_id=lu.team_id,
                formation=lu.formation,
                confirmed=lu.confirmed,
                announced_at=lu.announced_at,
                entries=[
                    LineupEntryOut(
                        player_id=e.player_id,
                        player_name=name,
                        role=e.role.value,
                        position=e.position,
                        grid_x=e.grid_x,
                        grid_y=e.grid_y,
                        shirt_number=e.shirt_number,
                    )
                    for e, name in entries
                ],
            )
        )
    return MatchDetail(
        **base.model_dump(),
        attendance=m.attendance,
        referee=m.referee,
        team_stats=[TeamStatsOut.model_validate(s) for s in stats],
        lineups=lineups,
        provenance=Provenance(
            source=src.key,
            is_synthetic=src.is_synthetic,
            fetched_at=m.fetched_at,
            source_updated_at=m.source_updated_at,
        ),
        attribution=src.attribution_text,
    )


def _escape_like(q: str) -> str:
    return q.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def list_players(
    session: Session,
    *,
    team_id: int | None = None,
    season_id: int | None = None,
    q: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> Page[PlayerOut]:
    latest = (
        select(
            SquadMembership.player_id,
            SquadMembership.team_id,
            SquadMembership.shirt_number,
            func.row_number()
            .over(partition_by=SquadMembership.player_id, order_by=SquadMembership.season_id.desc())
            .label("rn"),
        )
        .where(SquadMembership.season_id == season_id if season_id is not None else true())
        .subquery()
    )
    stmt = (
        select(Player, Team, latest.c.shirt_number, DataSource)
        .outerjoin(latest, and_(latest.c.player_id == Player.id, latest.c.rn == 1))
        .outerjoin(Team, Team.id == latest.c.team_id)
        .join(DataSource, DataSource.id == Player.source_id)
    )
    if team_id is not None:
        stmt = stmt.where(latest.c.team_id == team_id)
    if season_id is not None:
        stmt = stmt.where(latest.c.player_id.is_not(None))
    if q:
        stmt = stmt.where(Player.full_name.ilike(f"%{_escape_like(q)}%", escape="\\"))
    total = session.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = session.execute(
        stmt.order_by(Player.full_name, Player.id).limit(limit).offset(offset)
    ).all()
    items = [
        PlayerOut(
            id=p.id,
            full_name=p.full_name,
            known_as=p.known_as,
            birth_date=p.birth_date,
            nationality=p.nationality,
            primary_position=p.primary_position,
            team=_team_ref(t) if t is not None else None,
            shirt_number=shirt,
            source=src.key,
            is_synthetic=src.is_synthetic,
        )
        for p, t, shirt, src in rows
    ]
    return Page[PlayerOut](items=items, total=total, limit=limit, offset=offset)


def get_player(session: Session, player_id: int) -> PlayerOut:
    p = session.get(Player, player_id)
    if p is None:
        raise NotFoundError("Giocatore non trovato")
    sm = session.execute(
        select(SquadMembership, Team)
        .join(Team, Team.id == SquadMembership.team_id)
        .where(SquadMembership.player_id == player_id)
        .order_by(SquadMembership.season_id.desc())
        .limit(1)
    ).first()
    src = session.get_one(DataSource, p.source_id)
    return PlayerOut(
        id=p.id,
        full_name=p.full_name,
        known_as=p.known_as,
        birth_date=p.birth_date,
        nationality=p.nationality,
        primary_position=p.primary_position,
        team=_team_ref(sm[1]) if sm else None,
        shirt_number=sm[0].shirt_number if sm else None,
        source=src.key,
        is_synthetic=src.is_synthetic,
    )


def list_ingestion_runs(session: Session, limit: int = 20) -> list[IngestionRunOut]:
    warnings = (
        select(func.count(IngestionIssue.id))
        .where(
            IngestionIssue.ingestion_run_id == IngestionRun.id,
            IngestionIssue.severity == IssueSeverity.WARNING,
        )
        .correlate(IngestionRun)
        .scalar_subquery()
    )
    rows = session.execute(
        select(IngestionRun, DataSource.key, warnings)
        .join(DataSource, DataSource.id == IngestionRun.source_id)
        .order_by(IngestionRun.id.desc())
        .limit(limit)
    ).all()
    return [
        IngestionRunOut(
            id=r.id,
            source=key,
            scope={k: str(v) for k, v in r.scope.items()},
            status=r.status.value,
            started_at=r.started_at,
            finished_at=r.finished_at,
            records_upserted=r.records_upserted,
            records_rejected=r.records_rejected,
            warnings=w,
            error=r.error,
        )
        for r, key, w in rows
    ]

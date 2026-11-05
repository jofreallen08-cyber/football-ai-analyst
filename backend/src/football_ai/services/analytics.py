"""Analytics use-cases: standings, team/player analytics, match context, overview."""

from __future__ import annotations

from collections import Counter
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from football_ai.core.errors import DataUnavailableError, NotFoundError
from football_ai.features import players as pf
from football_ai.features import team as tf
from football_ai.features.frames import finished
from football_ai.models import (
    AvailabilityStatus,
    Competition,
    DataSource,
    Lineup,
    LineupEntry,
    LineupRole,
    Match,
    MatchStatus,
    Player,
    PlayerAvailability,
    Season,
    Team,
)
from football_ai.repositories import analytics as arepo
from football_ai.repositories import football as frepo
from football_ai.schemas.analytics import (
    AvailabilityItem,
    LastLineup,
    MatchContext,
    OverviewOut,
    PlayerAnalytics,
    PlayerLeader,
    PlayerLeadersOut,
    PlayerMatchLog,
    SeasonRef,
    StandingsOut,
    TeamAnalytics,
    TeamContext,
)
from football_ai.schemas.football import SourceOut, TeamRef

TIE_BREAK_NOTE = (
    "Classifica calcolata dai risultati disponibili: punti, differenza reti, gol fatti. "
    "I criteri ufficiali di parità (es. scontri diretti) possono differire."
)


def season_ref(session: Session, season_id: int) -> SeasonRef:
    row = session.execute(
        select(Season, Competition, DataSource)
        .join(Competition, Competition.id == Season.competition_id)
        .join(DataSource, DataSource.id == Season.source_id)
        .where(Season.id == season_id)
    ).first()
    if row is None:
        raise NotFoundError("Stagione non trovata")
    s, c, src = row
    return SeasonRef(
        id=s.id,
        label=s.label,
        competition_id=c.id,
        competition_name=c.name,
        competition_code=c.code,
        is_synthetic=src.is_synthetic,
    )


def team_refs(session: Session, ids: set[int]) -> dict[int, TeamRef]:
    if not ids:
        return {}
    return {
        t.id: TeamRef(id=t.id, name=t.name, short_name=t.short_name)
        for t in session.scalars(select(Team).where(Team.id.in_(ids)))
    }


def standings(session: Session, season_id: int) -> StandingsOut:
    ref = season_ref(session, season_id)
    df = arepo.season_frame(session, season_id)
    rows = tf.standings(df)
    return StandingsOut(
        season=ref,
        teams=team_refs(session, {r.team_id for r in rows}),
        rows=rows,
        tie_break_note=TIE_BREAK_NOTE,
    )


def team_analytics(session: Session, team_id: int, season_id: int) -> TeamAnalytics:
    team = session.get(Team, team_id)
    if team is None:
        raise NotFoundError("Squadra non trovata")
    ref = season_ref(session, season_id)
    df = arepo.season_frame(session, season_id)
    if team_id not in set(df["team_id"]):
        raise DataUnavailableError("La squadra non ha partite in questa stagione")
    table = tf.standings(df)
    stats = tf.stat_averages(df, team_id)
    series = tf.xg_series(df, team_id)
    has_xg = any(p.xg is not None for p in series)
    missing = list(stats.missing)
    if not has_xg:
        missing.insert(0, "xG non disponibile per questa competizione")
    return TeamAnalytics(
        team=TeamRef(id=team.id, name=team.name, short_name=team.short_name),
        season=ref,
        teams=team_refs(session, set(df["team_id"])),
        position=next((r.position for r in table if r.team_id == team_id), None),
        form_last5=tf.form(df, team_id, 5),
        form_last10=tf.form(df, team_id, 10),
        splits=tf.splits(df, team_id),
        stats=stats,
        xg_series=series,
        has_xg=has_xg,
        missing=missing,
    )


def _player_info(session: Session, ids: set[int]) -> dict[int, Player]:
    if not ids:
        return {}
    return {p.id: p for p in session.scalars(select(Player).where(Player.id.in_(ids)))}


def player_leaders(
    session: Session,
    season_id: int,
    metric: str,
    *,
    per90: bool = False,
    team_id: int | None = None,
    limit: int = 10,
) -> PlayerLeadersOut:
    ref = season_ref(session, season_id)
    df = arepo.season_player_frame(session, season_id, team_id=team_id)
    aggs = pf.aggregate_players(df)
    top = pf.leaders(aggs, metric, n=limit, per90=per90)
    info = _player_info(session, {a.player_id for a in top})
    teams = team_refs(session, {a.team_id for a in top})
    return PlayerLeadersOut(
        season=ref,
        metric=metric,
        per90=per90,
        min_minutes_per90=pf.MIN_MINUTES_PER90,
        items=[
            PlayerLeader(
                player_id=a.player_id,
                player_name=info[a.player_id].full_name,
                position=info[a.player_id].primary_position,
                team=teams[a.team_id],
                aggregate=a,
            )
            for a in top
        ],
    )


def player_analytics(session: Session, player_id: int, season_id: int) -> PlayerAnalytics:
    if session.get(Player, player_id) is None:
        raise NotFoundError("Giocatore non trovato")
    ref = season_ref(session, season_id)
    df = arepo.season_player_frame(session, season_id, player_id=player_id)
    aggs = pf.aggregate_players(df)
    missing = [] if aggs else ["Statistiche individuali non disponibili per questa stagione"]
    log = [
        PlayerMatchLog(
            match_id=int(r.match_id),
            kickoff_at=r.kickoff_at.to_pydatetime(),
            **{
                k: (None if r_val != r_val else float(r_val))
                for k, r_val in (
                    ("minutes", r.minutes),
                    ("goals", r.goals),
                    ("assists", r.assists),
                    ("xg", r.xg),
                    ("xa", r.xa),
                    ("shots", r.shots),
                )
            },
        )
        for r in df.sort_values("kickoff_at").itertuples()
    ]
    return PlayerAnalytics(
        season=ref,
        aggregate=max(aggs, key=lambda a: a.minutes) if aggs else None,
        match_log=log,
        missing=missing,
    )


# ------------------------------------------------------------------ match context


def _availability(
    session: Session,
    team_id: int,
    as_of: datetime,
    aggs: dict[int, pf.PlayerAggregate],
    team_minutes: float,
    team_xg: float | None,
) -> list[AvailabilityItem]:
    rows = session.execute(
        select(PlayerAvailability, Player, DataSource.key)
        .join(Player, Player.id == PlayerAvailability.player_id)
        .join(DataSource, DataSource.id == PlayerAvailability.source_id)
        .where(
            PlayerAvailability.team_id == team_id,
            PlayerAvailability.status == AvailabilityStatus.ACTIVE,
            PlayerAvailability.reported_at <= as_of,
        )
        .order_by(PlayerAvailability.reported_at.desc())
    ).all()
    items = []
    for a, p, src in rows:
        agg = aggs.get(p.id)
        xg = agg.totals.get("xg") if agg else None
        items.append(
            AvailabilityItem(
                player_id=p.id,
                player_name=p.full_name,
                position=p.primary_position,
                team_id=team_id,
                type=a.type.value,
                description=a.description,
                reported_at=a.reported_at,
                expected_return=a.expected_return.isoformat() if a.expected_return else None,
                source=src,
                minutes_share=round(agg.minutes / team_minutes, 3)
                if agg and team_minutes
                else None,
                xg_share=round(xg / team_xg, 3) if xg is not None and team_xg else None,
            )
        )
    return items


def _lineups(
    session: Session, team_id: int, season_id: int, before: datetime
) -> tuple[LastLineup | None, dict[str, int]]:
    rows = session.execute(
        select(Lineup, Match.kickoff_at)
        .join(Match, Match.id == Lineup.match_id)
        .where(Lineup.team_id == team_id, Match.season_id == season_id, Match.kickoff_at < before)
        .order_by(Match.kickoff_at.desc())
    ).all()
    usage = Counter(lu.formation for lu, _ in rows if lu.formation)
    if not rows:
        return None, {}
    last, ko = rows[0]
    starters = session.scalars(
        select(Player.full_name)
        .join(LineupEntry, LineupEntry.player_id == Player.id)
        .where(LineupEntry.lineup_id == last.id, LineupEntry.role == LineupRole.STARTER)
        .order_by(LineupEntry.grid_x, LineupEntry.grid_y)
    ).all()
    return (
        LastLineup(
            match_id=last.match_id,
            kickoff_at=ko,
            formation=last.formation,
            confirmed=last.confirmed,
            starters=list(starters),
        ),
        dict(usage),
    )


def match_context(session: Session, match_id: int) -> MatchContext:
    """Everything known *before kick-off* about a match, with sources and gaps."""
    match = frepo.get_match(session, match_id)
    m = session.get_one(Match, match_id)
    as_of = m.kickoff_at
    df = arepo.season_frame(session, m.season_id)
    table = {r.team_id: r for r in tf.standings(df, before=as_of)}
    pdf = arepo.season_player_frame(session, m.season_id)
    pdf = pdf[pdf["kickoff_at"] < as_of]
    aggs = {(a.player_id): a for a in pf.aggregate_players(pdf)}

    played = finished(df, before=as_of)

    def team_ctx(team_id: int, venue: str) -> TeamContext:
        # minutes available to one player = matches played by the team x 90
        team_minutes = float((played["team_id"] == team_id).sum() * 90)
        team_aggs = {k: v for k, v in aggs.items() if v.team_id == team_id}
        team_xg_vals = [a.totals.get("xg") for a in team_aggs.values()]
        team_xg = sum(x for x in team_xg_vals if x is not None) or None
        last, usage = _lineups(session, team_id, m.season_id, as_of)
        row = table.get(team_id)
        return TeamContext(
            team=match.home_team if team_id == m.home_team_id else match.away_team,
            position=row.position if row and row.played else None,
            points=row.points if row and row.played else None,
            form_last5=tf.form(df, team_id, 5, before=as_of),
            venue_form_last5=tf.form(df, team_id, 5, before=as_of, venue=venue),
            splits=tf.splits(df, team_id, before=as_of),
            stats=tf.stat_averages(df, team_id, before=as_of),
            availability=_availability(session, team_id, as_of, team_aggs, team_minutes, team_xg),
            last_lineup=last,
            formation_usage=usage,
        )

    home = team_ctx(m.home_team_id, "home")
    away = team_ctx(m.away_team_id, "away")
    h2h = tf.head_to_head(
        arepo.pair_frame(session, m.home_team_id, m.away_team_id),
        m.home_team_id,
        m.away_team_id,
        before=as_of,
    )
    src = session.get_one(DataSource, m.source_id)
    has_xg = any(x.per_match is not None for x in home.stats.metrics if x.key == "xg")
    has_lineups = home.last_lineup is not None or away.last_lineup is not None
    has_player_stats = bool(aggs)
    has_availability_source = (
        session.scalar(
            select(func.count(PlayerAvailability.id)).where(
                PlayerAvailability.source_id == m.source_id
            )
        )
        or 0
    ) > 0
    missing: list[str] = []
    if not has_xg:
        missing.append("xG e statistiche di squadra non disponibili dalla fonte")
    if not has_player_stats:
        missing.append("Statistiche individuali dei giocatori non disponibili")
    if not has_lineups:
        missing.append("Formazioni non disponibili dalla fonte")
    if not has_availability_source:
        missing.append("Nessuna fonte verificata su infortuni e squalifiche")
    if match.status == "scheduled":
        missing.append("Formazioni ufficiali non ancora annunciate")
    if h2h.sample_size < 3:
        missing.append(f"Scontri diretti disponibili: solo {h2h.sample_size}")
    if home.form_last5.sample_size < 5 or away.form_last5.sample_size < 5:
        missing.append("Meno di 5 partite precedenti in stagione per almeno una squadra")
    return MatchContext(
        match=match,
        as_of=as_of,
        home=home,
        away=away,
        head_to_head=h2h,
        teams=team_refs(session, set(df["team_id"])),
        sources=[SourceOut.model_validate(src)],
        capabilities={
            "xg": has_xg,
            "lineups": has_lineups,
            "player_stats": has_player_stats,
            "availability": has_availability_source,
        },
        missing=missing,
    )


def overview(session: Session) -> OverviewOut:
    now = datetime.now(UTC)
    totals = {
        "competitions": session.scalar(select(func.count(Competition.id))) or 0,
        "matches": session.scalar(select(func.count(Match.id))) or 0,
        "finished": session.scalar(
            select(func.count(Match.id)).where(Match.status == MatchStatus.FINISHED)
        )
        or 0,
        "teams": session.scalar(select(func.count(Team.id))) or 0,
        "players": session.scalar(select(func.count(Player.id))) or 0,
    }
    recent = frepo.list_matches(
        session, status=MatchStatus.FINISHED, date_to=now, order="desc", limit=6
    ).items
    upcoming = frepo.list_matches(
        session, status=MatchStatus.SCHEDULED, date_from=now, order="asc", limit=6
    ).items
    return OverviewOut(
        totals=totals, recent=recent, upcoming=upcoming, sources=frepo.list_sources(session)
    )

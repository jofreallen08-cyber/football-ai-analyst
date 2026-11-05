"""Database constraint tests against a real PostgreSQL schema (migrated by Alembic)."""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest
from sqlalchemy import inspect
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from football_ai.models import (
    Competition,
    CompetitionType,
    DataSource,
    Match,
    MatchStatus,
    MatchTeamStats,
    Season,
    Team,
    TeamAlias,
)

pytestmark = pytest.mark.db


def _seed(session: Session, now: datetime) -> tuple[DataSource, Season, Team, Team]:
    src = DataSource(key="local_sample", name="Dati di esempio locali")
    session.add(src)
    session.flush()
    prov = {"source_id": src.id, "fetched_at": now}
    comp = Competition(
        name="Serie A", code="SA", country="Italia", type=CompetitionType.LEAGUE, **prov
    )
    session.add(comp)
    session.flush()
    season = Season(competition_id=comp.id, label="2025/26", **prov)
    home = Team(name="Squadra Casa", **prov)
    away = Team(name="Squadra Ospite", **prov)
    session.add_all([season, home, away])
    session.flush()
    return src, season, home, away


def _match(src: DataSource, season: Season, home: Team, away: Team, now: datetime, **kw) -> Match:
    return Match(
        season_id=season.id,
        home_team_id=home.id,
        away_team_id=away.id,
        kickoff_at=now,
        status=MatchStatus.FINISHED,
        source_id=src.id,
        fetched_at=now,
        **kw,
    )


def test_all_tables_created(db_engine) -> None:
    tables = set(inspect(db_engine).get_table_names())
    assert {"matches", "match_team_stats", "player_match_stats", "data_sources"} <= tables


def test_valid_match_with_missing_stats_is_null_not_zero(db_session, now) -> None:
    src, season, home, away = _seed(db_session, now)
    m = _match(src, season, home, away, now, home_score=2, away_score=1)
    db_session.add(m)
    db_session.flush()
    stats = MatchTeamStats(
        match_id=m.id, team_id=home.id, is_home=True, source_id=src.id, fetched_at=now
    )
    db_session.add(stats)
    db_session.flush()
    db_session.refresh(stats)
    assert stats.xg is None and stats.corners is None


def test_negative_score_rejected(db_session, now) -> None:
    src, season, home, away = _seed(db_session, now)
    db_session.add(_match(src, season, home, away, now, home_score=-1, away_score=0))
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_team_cannot_play_itself(db_session, now) -> None:
    src, season, home, _ = _seed(db_session, now)
    db_session.add(_match(src, season, home, home, now))
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_duplicate_match_rejected(db_session, now) -> None:
    src, season, home, away = _seed(db_session, now)
    db_session.add(_match(src, season, home, away, now))
    db_session.flush()
    db_session.add(_match(src, season, home, away, now))
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_rematch_on_other_date_allowed(db_session, now) -> None:
    src, season, home, away = _seed(db_session, now)
    db_session.add(_match(src, season, home, away, now))
    db_session.add(_match(src, season, home, away, now + timedelta(days=90)))
    db_session.flush()


@pytest.mark.parametrize("possession", [-1, 100.5])
def test_possession_out_of_range_rejected(db_session, now, possession) -> None:
    src, season, home, away = _seed(db_session, now)
    m = _match(src, season, home, away, now)
    db_session.add(m)
    db_session.flush()
    db_session.add(
        MatchTeamStats(
            match_id=m.id,
            team_id=home.id,
            is_home=True,
            possession_pct=possession,
            source_id=src.id,
            fetched_at=now,
        )
    )
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_shots_on_target_cannot_exceed_shots(db_session, now) -> None:
    src, season, home, away = _seed(db_session, now)
    m = _match(src, season, home, away, now)
    db_session.add(m)
    db_session.flush()
    db_session.add(
        MatchTeamStats(
            match_id=m.id,
            team_id=home.id,
            is_home=True,
            shots=3,
            shots_on_target=5,
            source_id=src.id,
            fetched_at=now,
        )
    )
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_team_alias_unique_case_insensitive(db_session, now) -> None:
    _, _, home, away = _seed(db_session, now)
    db_session.add(TeamAlias(team_id=home.id, alias="Internazionale"))
    db_session.flush()
    db_session.add(TeamAlias(team_id=away.id, alias="INTERNAZIONALE"))
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_fact_rows_require_source(db_session, now) -> None:
    db_session.add(Team(name="Senza fonte", fetched_at=now))
    with pytest.raises(IntegrityError):
        db_session.flush()

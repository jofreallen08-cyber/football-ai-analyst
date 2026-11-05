"""Core football domain tables: competitions, seasons, teams, players, matches, stats."""

from __future__ import annotations

import enum
from datetime import date, datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    SmallInteger,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from football_ai.models.base import Base, IdMixin, ProvenanceMixin, TimestampMixin


def _enum(cls: type[enum.Enum], name: str) -> Enum:
    return Enum(cls, name=name, values_callable=lambda e: [m.value for m in e])


class CompetitionType(enum.StrEnum):
    LEAGUE = "league"
    CUP = "cup"
    INTERNATIONAL = "international"


class MatchStatus(enum.StrEnum):
    SCHEDULED = "scheduled"
    LIVE = "live"
    FINISHED = "finished"
    POSTPONED = "postponed"
    CANCELLED = "cancelled"


class Competition(IdMixin, TimestampMixin, ProvenanceMixin, Base):
    __tablename__ = "competitions"
    __table_args__ = (UniqueConstraint("code"),)

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    code: Mapped[str] = mapped_column(String(32), nullable=False)
    country: Mapped[str | None] = mapped_column(String(100))
    type: Mapped[CompetitionType] = mapped_column(
        _enum(CompetitionType, "competition_type"), nullable=False
    )
    gender: Mapped[str] = mapped_column(String(16), default="men", nullable=False)
    tier: Mapped[int | None] = mapped_column(SmallInteger)


class Season(IdMixin, TimestampMixin, ProvenanceMixin, Base):
    __tablename__ = "seasons"
    __table_args__ = (
        UniqueConstraint("competition_id", "label"),
        CheckConstraint(
            "end_date IS NULL OR start_date IS NULL OR end_date >= start_date", name="dates"
        ),
    )

    competition_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("competitions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    label: Mapped[str] = mapped_column(String(32), nullable=False)
    start_date: Mapped[date | None] = mapped_column(Date)
    end_date: Mapped[date | None] = mapped_column(Date)
    is_current: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class Team(IdMixin, TimestampMixin, ProvenanceMixin, Base):
    __tablename__ = "teams"

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    short_name: Mapped[str | None] = mapped_column(String(64))
    country: Mapped[str | None] = mapped_column(String(100))
    founded: Mapped[int | None] = mapped_column(SmallInteger)
    crest_url: Mapped[str | None] = mapped_column(String(500))


class TeamAlias(IdMixin, TimestampMixin, Base):
    """Alternative spellings of a team name used for entity resolution."""

    __tablename__ = "team_aliases"

    team_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("teams.id", ondelete="CASCADE"), nullable=False, index=True
    )
    alias: Mapped[str] = mapped_column(String(200), nullable=False)


# Case-insensitive uniqueness of aliases (expression index, defined after the class
# so that it references the real column rather than a string literal).
Index("uq_team_aliases_alias_lower", func.lower(TeamAlias.alias), unique=True)


class Player(IdMixin, TimestampMixin, ProvenanceMixin, Base):
    __tablename__ = "players"

    full_name: Mapped[str] = mapped_column(String(200), nullable=False)
    known_as: Mapped[str | None] = mapped_column(String(200))
    birth_date: Mapped[date | None] = mapped_column(Date)
    nationality: Mapped[str | None] = mapped_column(String(100))
    primary_position: Mapped[str | None] = mapped_column(String(32))


class Match(IdMixin, TimestampMixin, ProvenanceMixin, Base):
    __tablename__ = "matches"
    __table_args__ = (
        UniqueConstraint("season_id", "home_team_id", "away_team_id", "kickoff_at"),
        CheckConstraint("home_team_id <> away_team_id", name="distinct_teams"),
        CheckConstraint(
            "(home_score IS NULL OR home_score >= 0) AND (away_score IS NULL OR away_score >= 0)",
            name="scores_non_negative",
        ),
        CheckConstraint(
            "(home_score_ht IS NULL OR home_score_ht >= 0)"
            " AND (away_score_ht IS NULL OR away_score_ht >= 0)",
            name="ht_scores_non_negative",
        ),
        Index("ix_matches_season_kickoff", "season_id", "kickoff_at"),
        Index("ix_matches_home_kickoff", "home_team_id", "kickoff_at"),
        Index("ix_matches_away_kickoff", "away_team_id", "kickoff_at"),
    )

    season_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("seasons.id", ondelete="CASCADE"), nullable=False
    )
    matchday: Mapped[int | None] = mapped_column(SmallInteger)
    stage: Mapped[str | None] = mapped_column(String(64))
    kickoff_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    home_team_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("teams.id", ondelete="RESTRICT"), nullable=False
    )
    away_team_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("teams.id", ondelete="RESTRICT"), nullable=False
    )
    status: Mapped[MatchStatus] = mapped_column(_enum(MatchStatus, "match_status"), nullable=False)
    home_score: Mapped[int | None] = mapped_column(SmallInteger)
    away_score: Mapped[int | None] = mapped_column(SmallInteger)
    home_score_ht: Mapped[int | None] = mapped_column(SmallInteger)
    away_score_ht: Mapped[int | None] = mapped_column(SmallInteger)
    neutral_venue: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    attendance: Mapped[int | None] = mapped_column(Integer)
    referee: Mapped[str | None] = mapped_column(String(200))


class MatchTeamStats(IdMixin, TimestampMixin, ProvenanceMixin, Base):
    """Per-team statistics for a match. NULL = statistic not available."""

    __tablename__ = "match_team_stats"
    __table_args__ = (
        UniqueConstraint("match_id", "team_id"),
        CheckConstraint(
            "possession_pct IS NULL OR (possession_pct >= 0 AND possession_pct <= 100)",
            name="possession_range",
        ),
        CheckConstraint(
            "pass_accuracy_pct IS NULL OR (pass_accuracy_pct >= 0 AND pass_accuracy_pct <= 100)",
            name="pass_accuracy_range",
        ),
        CheckConstraint("xg IS NULL OR xg >= 0", name="xg_non_negative"),
        CheckConstraint("xga IS NULL OR xga >= 0", name="xga_non_negative"),
        CheckConstraint(
            "shots_on_target IS NULL OR shots IS NULL OR shots_on_target <= shots",
            name="shots_on_target_le_shots",
        ),
    )

    match_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("matches.id", ondelete="CASCADE"), nullable=False, index=True
    )
    team_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("teams.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    is_home: Mapped[bool] = mapped_column(Boolean, nullable=False)
    xg: Mapped[float | None] = mapped_column(Numeric(5, 2, asdecimal=False))
    xga: Mapped[float | None] = mapped_column(Numeric(5, 2, asdecimal=False))
    shots: Mapped[int | None] = mapped_column(SmallInteger)
    shots_on_target: Mapped[int | None] = mapped_column(SmallInteger)
    possession_pct: Mapped[float | None] = mapped_column(Numeric(5, 2, asdecimal=False))
    corners: Mapped[int | None] = mapped_column(SmallInteger)
    fouls: Mapped[int | None] = mapped_column(SmallInteger)
    yellow_cards: Mapped[int | None] = mapped_column(SmallInteger)
    red_cards: Mapped[int | None] = mapped_column(SmallInteger)
    passes: Mapped[int | None] = mapped_column(Integer)
    pass_accuracy_pct: Mapped[float | None] = mapped_column(Numeric(5, 2, asdecimal=False))
    offsides: Mapped[int | None] = mapped_column(SmallInteger)


class PlayerMatchStats(IdMixin, TimestampMixin, ProvenanceMixin, Base):
    """Per-player statistics for a match. NULL = statistic not available."""

    __tablename__ = "player_match_stats"
    __table_args__ = (
        UniqueConstraint("match_id", "player_id"),
        CheckConstraint(
            "minutes IS NULL OR (minutes >= 0 AND minutes <= 130)", name="minutes_range"
        ),
        CheckConstraint("goals IS NULL OR goals >= 0", name="goals_non_negative"),
        CheckConstraint("xg IS NULL OR xg >= 0", name="xg_non_negative"),
        Index("ix_player_match_stats_player_match", "player_id", "match_id"),
    )

    match_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("matches.id", ondelete="CASCADE"), nullable=False, index=True
    )
    player_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("players.id", ondelete="RESTRICT"), nullable=False
    )
    team_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("teams.id", ondelete="RESTRICT"), nullable=False
    )
    minutes: Mapped[int | None] = mapped_column(SmallInteger)
    started: Mapped[bool | None] = mapped_column(Boolean)
    position: Mapped[str | None] = mapped_column(String(32))
    goals: Mapped[int | None] = mapped_column(SmallInteger)
    assists: Mapped[int | None] = mapped_column(SmallInteger)
    shots: Mapped[int | None] = mapped_column(SmallInteger)
    shots_on_target: Mapped[int | None] = mapped_column(SmallInteger)
    xg: Mapped[float | None] = mapped_column(Numeric(5, 2, asdecimal=False))
    xa: Mapped[float | None] = mapped_column(Numeric(5, 2, asdecimal=False))
    key_passes: Mapped[int | None] = mapped_column(SmallInteger)
    passes: Mapped[int | None] = mapped_column(SmallInteger)
    pass_accuracy_pct: Mapped[float | None] = mapped_column(Numeric(5, 2, asdecimal=False))
    tackles: Mapped[int | None] = mapped_column(SmallInteger)
    interceptions: Mapped[int | None] = mapped_column(SmallInteger)
    yellow_cards: Mapped[int | None] = mapped_column(SmallInteger)
    red_cards: Mapped[int | None] = mapped_column(SmallInteger)
    rating: Mapped[float | None] = mapped_column(Numeric(4, 2, asdecimal=False))

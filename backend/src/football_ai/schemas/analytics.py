"""Analytics response schemas (wrap the feature dataclasses)."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from football_ai.features.players import PlayerAggregate
from football_ai.features.team import (
    FormSummary,
    HeadToHead,
    SeriesPoint,
    SplitSummary,
    StandingRow,
    StatsSummary,
)
from football_ai.schemas.football import MatchOut, SourceOut, TeamRef


class SeasonRef(BaseModel):
    id: int
    label: str
    competition_id: int
    competition_name: str
    competition_code: str
    is_synthetic: bool


class StandingsOut(BaseModel):
    season: SeasonRef
    teams: dict[int, TeamRef]
    rows: list[StandingRow]
    tie_break_note: str


class TeamAnalytics(BaseModel):
    team: TeamRef
    season: SeasonRef
    teams: dict[int, TeamRef]
    position: int | None
    form_last5: FormSummary
    form_last10: FormSummary
    splits: dict[str, SplitSummary]
    stats: StatsSummary
    xg_series: list[SeriesPoint]
    has_xg: bool
    missing: list[str]


class PlayerLeader(BaseModel):
    player_id: int
    player_name: str
    position: str | None
    team: TeamRef
    aggregate: PlayerAggregate


class PlayerLeadersOut(BaseModel):
    season: SeasonRef
    metric: str
    per90: bool
    min_minutes_per90: int
    items: list[PlayerLeader]


class PlayerMatchLog(BaseModel):
    match_id: int
    kickoff_at: datetime
    minutes: float | None
    goals: float | None
    assists: float | None
    xg: float | None
    xa: float | None
    shots: float | None


class PlayerAnalytics(BaseModel):
    season: SeasonRef
    aggregate: PlayerAggregate | None
    match_log: list[PlayerMatchLog]
    missing: list[str]


class AvailabilityItem(BaseModel):
    player_id: int
    player_name: str
    position: str | None
    team_id: int
    type: str
    description: str | None
    reported_at: datetime
    expected_return: str | None
    source: str
    minutes_share: float | None
    xg_share: float | None


class LastLineup(BaseModel):
    match_id: int
    kickoff_at: datetime
    formation: str | None
    confirmed: bool
    starters: list[str]


class TeamContext(BaseModel):
    team: TeamRef
    position: int | None
    points: int | None
    form_last5: FormSummary
    venue_form_last5: FormSummary
    splits: dict[str, SplitSummary]
    stats: StatsSummary
    availability: list[AvailabilityItem]
    last_lineup: LastLineup | None
    formation_usage: dict[str, int]


class MatchContext(BaseModel):
    """Verified, deterministic data bundle for one match — the only input of the agents."""

    match: MatchOut
    as_of: datetime
    home: TeamContext
    away: TeamContext
    head_to_head: HeadToHead
    teams: dict[int, TeamRef]
    sources: list[SourceOut]
    capabilities: dict[str, bool]
    missing: list[str]


class OverviewOut(BaseModel):
    totals: dict[str, int]
    recent: list[MatchOut]
    upcoming: list[MatchOut]
    sources: list[SourceOut]

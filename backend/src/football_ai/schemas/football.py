"""Read schemas for the football domain. ``None`` always means *not available*."""

from __future__ import annotations

from datetime import date, datetime

from football_ai.schemas.common import ORMModel


class SourceOut(ORMModel):
    key: str
    name: str
    license_name: str | None
    license_url: str | None
    attribution_text: str | None
    commercial_use_allowed: bool
    is_synthetic: bool


class Provenance(ORMModel):
    source: str
    is_synthetic: bool
    fetched_at: datetime
    source_updated_at: datetime | None


class SeasonOut(ORMModel):
    id: int
    label: str
    start_date: date | None
    end_date: date | None
    is_current: bool


class CompetitionOut(ORMModel):
    id: int
    name: str
    code: str
    country: str | None
    type: str
    source: str
    is_synthetic: bool
    seasons: list[SeasonOut]


class TeamRef(ORMModel):
    id: int
    name: str
    short_name: str | None


class TeamOut(TeamRef):
    country: str | None
    founded: int | None
    source: str
    is_synthetic: bool


class TeamDetail(TeamOut):
    seasons: list[CompetitionSeasonRef]


class CompetitionSeasonRef(ORMModel):
    season_id: int
    season_label: str
    competition_id: int
    competition_name: str
    competition_code: str


class MatchOut(ORMModel):
    id: int
    season_id: int
    competition_code: str
    competition_name: str
    season_label: str
    matchday: int | None
    kickoff_at: datetime
    status: str
    home_team: TeamRef
    away_team: TeamRef
    home_score: int | None
    away_score: int | None
    home_score_ht: int | None
    away_score_ht: int | None
    has_team_stats: bool
    source: str
    is_synthetic: bool


class TeamStatsOut(ORMModel):
    team_id: int
    is_home: bool
    xg: float | None
    xga: float | None
    shots: int | None
    shots_on_target: int | None
    possession_pct: float | None
    corners: int | None
    fouls: int | None
    yellow_cards: int | None
    red_cards: int | None
    passes: int | None
    pass_accuracy_pct: float | None
    offsides: int | None


class LineupEntryOut(ORMModel):
    player_id: int
    player_name: str
    role: str
    position: str | None
    grid_x: float | None
    grid_y: float | None
    shirt_number: int | None


class LineupOut(ORMModel):
    team_id: int
    formation: str | None
    confirmed: bool
    announced_at: datetime | None
    entries: list[LineupEntryOut]


class MatchDetail(MatchOut):
    attendance: int | None
    referee: str | None
    team_stats: list[TeamStatsOut]
    lineups: list[LineupOut]
    provenance: Provenance
    attribution: str | None


class PlayerOut(ORMModel):
    id: int
    full_name: str
    known_as: str | None
    birth_date: date | None
    nationality: str | None
    primary_position: str | None
    team: TeamRef | None
    shirt_number: int | None
    source: str
    is_synthetic: bool


class IngestionRunOut(ORMModel):
    id: int
    source: str
    scope: dict[str, str]
    status: str
    started_at: datetime
    finished_at: datetime | None
    records_upserted: int
    records_rejected: int
    warnings: int
    error: str | None


TeamDetail.model_rebuild()

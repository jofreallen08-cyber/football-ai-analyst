"""Provider contract and the validated records exchanged with the ingestion service."""

from __future__ import annotations

import enum
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Literal, Protocol, Self, runtime_checkable

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class Capability(enum.StrEnum):
    COMPETITIONS = "competitions"
    FIXTURES = "fixtures"
    RESULTS = "results"
    TEAM_STATS = "team_stats"
    PLAYER_STATS = "player_stats"
    XG = "xg"
    LINEUPS = "lineups"
    AVAILABILITY = "availability"


@dataclass(frozen=True)
class ProviderLicense:
    name: str
    url: str | None
    attribution: str
    commercial_use_allowed: bool


@dataclass(frozen=True)
class RateLimitPolicy:
    """At most ``requests`` calls every ``per_seconds`` seconds."""

    requests: int
    per_seconds: float


class CapabilityNotSupportedError(Exception):
    """Raised when a provider is asked for data it cannot supply."""


class ProviderError(Exception):
    """Raised when a provider cannot fetch or parse its source."""


# --------------------------------------------------------------------------- records


class _Record(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, str_strip_whitespace=True)


def _aware(value: datetime | None) -> datetime | None:
    if value is not None and value.tzinfo is None:
        raise ValueError("il timestamp deve includere il fuso orario")
    return value


class PCompetition(_Record):
    external_id: str
    name: str = Field(min_length=1, max_length=200)
    code: str = Field(min_length=1, max_length=32)
    country: str | None = None
    type: Literal["league", "cup", "international"] = "league"
    tier: int | None = Field(default=None, ge=1, le=20)


class PSeason(_Record):
    external_id: str
    label: str = Field(min_length=1, max_length=32)
    start_date: date | None = None
    end_date: date | None = None
    is_current: bool = False

    @model_validator(mode="after")
    def _dates(self) -> Self:
        if self.start_date and self.end_date and self.end_date < self.start_date:
            raise ValueError("end_date precede start_date")
        return self


class PTeam(_Record):
    external_id: str
    name: str = Field(min_length=1, max_length=200)
    short_name: str | None = Field(default=None, max_length=64)
    country: str | None = None
    founded: int | None = Field(default=None, ge=1850, le=2100)


class PPlayer(_Record):
    external_id: str
    full_name: str = Field(min_length=1, max_length=200)
    known_as: str | None = None
    birth_date: date | None = None
    nationality: str | None = None
    primary_position: Literal["GK", "DEF", "MID", "FWD"] | None = None


class PSquadMember(_Record):
    player_external_id: str
    team_external_id: str
    shirt_number: int | None = Field(default=None, ge=1, le=99)


class PTeamStats(_Record):
    """Team statistics for one match. ``None`` means *not provided by the source*."""

    xg: float | None = Field(default=None, ge=0, le=15)
    shots: int | None = Field(default=None, ge=0, le=80)
    shots_on_target: int | None = Field(default=None, ge=0, le=80)
    possession_pct: float | None = Field(default=None, ge=0, le=100)
    corners: int | None = Field(default=None, ge=0, le=40)
    fouls: int | None = Field(default=None, ge=0, le=60)
    yellow_cards: int | None = Field(default=None, ge=0, le=15)
    red_cards: int | None = Field(default=None, ge=0, le=5)
    passes: int | None = Field(default=None, ge=0, le=1500)
    pass_accuracy_pct: float | None = Field(default=None, ge=0, le=100)
    offsides: int | None = Field(default=None, ge=0, le=30)

    @model_validator(mode="after")
    def _shots(self) -> Self:
        if (
            self.shots is not None
            and self.shots_on_target is not None
            and self.shots_on_target > self.shots
        ):
            raise ValueError("tiri in porta superiori ai tiri totali")
        return self


class PPlayerStats(_Record):
    player_external_id: str
    team_external_id: str
    minutes: int | None = Field(default=None, ge=0, le=130)
    started: bool | None = None
    position: str | None = None
    goals: int | None = Field(default=None, ge=0, le=10)
    assists: int | None = Field(default=None, ge=0, le=10)
    shots: int | None = Field(default=None, ge=0, le=20)
    shots_on_target: int | None = Field(default=None, ge=0, le=20)
    xg: float | None = Field(default=None, ge=0, le=10)
    xa: float | None = Field(default=None, ge=0, le=10)
    key_passes: int | None = Field(default=None, ge=0, le=30)
    passes: int | None = Field(default=None, ge=0, le=250)
    pass_accuracy_pct: float | None = Field(default=None, ge=0, le=100)
    tackles: int | None = Field(default=None, ge=0, le=30)
    interceptions: int | None = Field(default=None, ge=0, le=30)
    yellow_cards: int | None = Field(default=None, ge=0, le=2)
    red_cards: int | None = Field(default=None, ge=0, le=1)


class PLineupEntry(_Record):
    player_external_id: str
    role: Literal["starter", "substitute"]
    position: str | None = None
    grid_x: float | None = Field(default=None, ge=0, le=100)
    grid_y: float | None = Field(default=None, ge=0, le=100)
    shirt_number: int | None = Field(default=None, ge=1, le=99)


class PLineup(_Record):
    team_external_id: str
    formation: str | None = Field(default=None, pattern=r"^\d(-\d){2,4}$")
    confirmed: bool
    announced_at: datetime | None = None
    entries: list[PLineupEntry] = Field(default_factory=list)

    _tz = field_validator("announced_at")(_aware)


class PMatch(_Record):
    external_id: str
    kickoff_at: datetime
    matchday: int | None = Field(default=None, ge=1, le=60)
    stage: str | None = None
    home_team_external_id: str
    away_team_external_id: str
    status: Literal["scheduled", "live", "finished", "postponed", "cancelled"]
    home_score: int | None = Field(default=None, ge=0, le=30)
    away_score: int | None = Field(default=None, ge=0, le=30)
    home_score_ht: int | None = Field(default=None, ge=0, le=30)
    away_score_ht: int | None = Field(default=None, ge=0, le=30)
    neutral_venue: bool = False
    attendance: int | None = Field(default=None, ge=0)
    referee: str | None = None
    home_stats: PTeamStats | None = None
    away_stats: PTeamStats | None = None
    player_stats: list[PPlayerStats] = Field(default_factory=list)
    lineups: list[PLineup] = Field(default_factory=list)

    _tz = field_validator("kickoff_at")(_aware)

    @model_validator(mode="after")
    def _consistency(self) -> Self:
        if self.home_team_external_id == self.away_team_external_id:
            raise ValueError("una squadra non può affrontare se stessa")
        if self.status == "finished" and (self.home_score is None or self.away_score is None):
            raise ValueError("partita terminata senza punteggio")
        if self.status == "scheduled" and (
            self.home_score is not None or self.away_score is not None
        ):
            raise ValueError("partita in programma con punteggio")
        for ht, ft in (
            (self.home_score_ht, self.home_score),
            (self.away_score_ht, self.away_score),
        ):
            if ht is not None and ft is not None and ht > ft:
                raise ValueError("gol del primo tempo superiori al finale")
        return self


class PAvailability(_Record):
    external_id: str
    player_external_id: str
    team_external_id: str
    type: Literal["injury", "suspension", "international_duty", "doubtful", "other"]
    description: str | None = Field(default=None, max_length=500)
    reported_at: datetime
    expected_return: date | None = None
    source_url: str | None = None
    status: Literal["active", "resolved"]

    _tz = field_validator("reported_at")(_aware)


@dataclass
class RecordIssue:
    """A raw record that failed validation. Never dropped silently."""

    entity_type: str
    external_id: str | None
    message: str
    payload: dict[str, object] | None = None
    severity: Literal["warning", "error"] = "error"


@dataclass
class SeasonBundle:
    """Everything a provider returns for one competition season."""

    competition: PCompetition
    season: PSeason
    teams: list[PTeam] = field(default_factory=list)
    players: list[PPlayer] = field(default_factory=list)
    squads: list[PSquadMember] = field(default_factory=list)
    matches: list[PMatch] = field(default_factory=list)
    availability: list[PAvailability] = field(default_factory=list)
    source_updated_at: datetime | None = None
    issues: list[RecordIssue] = field(default_factory=list)


@dataclass(frozen=True)
class AvailableSeason:
    competition_code: str
    competition_name: str
    season_label: str


# --------------------------------------------------------------------------- protocol


@runtime_checkable
class DataProvider(Protocol):
    """Interface implemented by every data source."""

    key: str
    name: str
    license: ProviderLicense
    capabilities: frozenset[Capability]
    is_synthetic: bool

    async def list_available(self) -> list[AvailableSeason]:
        """Competition seasons this provider can supply."""
        ...

    async def fetch_season(self, competition_code: str, season_label: str) -> SeasonBundle:
        """Fetch, validate and return one competition season."""
        ...

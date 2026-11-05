"""Simulation lab request/response schemas."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, model_validator

from football_ai.schemas.football import TeamRef

FORMATIONS = ["4-3-3", "3-4-3", "4-2-3-1", "4-4-2", "3-5-2", "4-1-4-1", "5-3-2", "5-4-1"]


class SimulationRequest(BaseModel):
    season_id: int | None = Field(default=None, ge=1)
    home_team_id: int | None = Field(default=None, ge=1)
    away_team_id: int | None = Field(default=None, ge=1)
    match_id: int | None = Field(default=None, ge=1)
    venue: Literal["home", "neutral", "swapped"] = "home"
    unavailable_player_ids: list[int] = Field(default_factory=list, max_length=30)
    home_formation: str | None = None
    away_formation: str | None = None
    seed: int = Field(default=2026, ge=0, le=2**31 - 1)
    n_iterations: int = Field(default=20_000, ge=1_000, le=200_000)

    @model_validator(mode="after")
    def _check(self) -> SimulationRequest:
        if self.match_id is None and None in (self.season_id, self.home_team_id, self.away_team_id):
            raise ValueError("indicare match_id oppure season_id, home_team_id e away_team_id")
        if self.home_team_id is not None and self.home_team_id == self.away_team_id:
            raise ValueError("le due squadre devono essere diverse")
        for f in (self.home_formation, self.away_formation):
            if f is not None and f not in FORMATIONS:
                raise ValueError(f"modulo non supportato: {f}")
        return self


class Outcome(BaseModel):
    expected_goals_home: float
    expected_goals_away: float
    home_win_share: float
    draw_share: float
    away_win_share: float
    mean_goals_home: float
    mean_goals_away: float
    home_clean_sheet_share: float
    away_clean_sheet_share: float
    both_score_share: float
    top_scorelines: list[tuple[str, float]]
    goals_distribution_home: list[float]
    goals_distribution_away: list[float]


class TrainingWindow(BaseModel):
    matches_used: int
    start: datetime | None
    end: datetime | None
    as_of: datetime
    uses_xg: bool
    home_matches: int
    away_matches: int


class SimulationOut(BaseModel):
    id: uuid.UUID
    is_simulation: Literal[True] = True
    label: str = "SIMULAZIONE — scenario ipotetico, non un risultato reale né garantito"
    created_at: datetime
    match_id: int | None
    season_id: int
    home_team: TeamRef
    away_team: TeamRef
    venue: str
    model_version: str
    seed: int
    n_iterations: int
    training_window: TrainingWindow
    strengths: dict[str, dict[str, float]]
    baseline: Outcome
    scenario: Outcome | None
    scenario_description: dict[str, object]
    assumptions: list[str]
    limitations: list[str]
    is_synthetic_data: bool


class SimulationSummary(BaseModel):
    id: uuid.UUID
    created_at: datetime
    home_team: TeamRef
    away_team: TeamRef
    venue: str
    seed: int
    n_iterations: int
    has_scenario: bool
    home_win_share: float
    draw_share: float
    away_win_share: float


class PlayerOption(BaseModel):
    player_id: int
    name: str
    position: str | None
    minutes: int
    minutes_share: float | None
    xg_share: float | None
    reported_unavailable: bool


class SimulationOptions(BaseModel):
    season_id: int
    home_team: TeamRef
    away_team: TeamRef
    home_usual_formation: str | None
    away_usual_formation: str | None
    formations: list[str]
    home_players: list[PlayerOption]
    away_players: list[PlayerOption]
    as_of: datetime

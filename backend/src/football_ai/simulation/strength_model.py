"""Team attack/defence strengths from historical matches (Poisson-style ratings).

Method (model ``poisson-v1``):
* "goal production" per match = goals, blended with xG when the source provides it
  (60% xG, 40% goals) because xG is a less noisy measure of chance quality;
* matches are weighted by exponential time decay (half-life 120 days);
* team attack = weighted goal production per match / league average,
  team defence = weighted goals conceded per match / league average,
  each shrunk towards 1.0 with a prior worth 5 matches (small samples stay cautious);
* expected goals: home = league home average × attack(home) × defence(away),
  away = league away average × attack(away) × defence(home).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

import numpy as np
import pandas as pd

from football_ai.features.frames import finished

MODEL_VERSION = "poisson-v1"
HALF_LIFE_DAYS = 120.0
PRIOR_MATCHES = 5.0
XG_WEIGHT = 0.6


@dataclass(frozen=True)
class TeamStrength:
    team_id: int
    attack: float
    defence: float
    matches: int


@dataclass(frozen=True)
class StrengthModel:
    league_home_goals: float
    league_away_goals: float
    teams: dict[int, TeamStrength]
    matches_used: int
    window_start: datetime | None
    window_end: datetime | None
    uses_xg: bool

    def team(self, team_id: int) -> TeamStrength:
        return self.teams.get(team_id, TeamStrength(team_id, 1.0, 1.0, 0))

    def expected_goals(
        self, home_id: int, away_id: int, neutral: bool = False
    ) -> tuple[float, float]:
        h, a = self.team(home_id), self.team(away_id)
        if neutral:
            base = (self.league_home_goals + self.league_away_goals) / 2
            return base * h.attack * a.defence, base * a.attack * h.defence
        return (
            self.league_home_goals * h.attack * a.defence,
            self.league_away_goals * a.attack * h.defence,
        )


def fit(df: pd.DataFrame, as_of: datetime) -> StrengthModel:
    """Fit strengths on finished matches strictly before ``as_of``."""
    f = finished(df, before=as_of).copy()
    if f.empty:
        return StrengthModel(1.4, 1.1, {}, 0, None, None, False)
    has_xg = f["xg"].notna() & f["xga"].notna()
    f["prod"] = np.where(has_xg, XG_WEIGHT * f["xg"] + (1 - XG_WEIGHT) * f["gf"], f["gf"])
    f["conc"] = np.where(has_xg, XG_WEIGHT * f["xga"] + (1 - XG_WEIGHT) * f["ga"], f["ga"])
    age_days = (pd.Timestamp(as_of) - f["kickoff_at"]).dt.total_seconds() / 86400
    f["w"] = np.power(0.5, age_days / HALF_LIFE_DAYS)

    home = f[f["is_home"]]
    away = f[~f["is_home"]]
    league_home = float(np.average(home["prod"], weights=home["w"])) if len(home) else 1.4
    league_away = float(np.average(away["prod"], weights=away["w"])) if len(away) else 1.1
    league_avg = (league_home + league_away) / 2

    teams: dict[int, TeamStrength] = {}
    for tid, g in f.groupby("team_id"):
        w = g["w"].to_numpy()
        att_raw = float(np.average(g["prod"], weights=w)) / league_avg
        def_raw = float(np.average(g["conc"], weights=w)) / league_avg
        eff_n = float(w.sum())
        shrink = eff_n / (eff_n + PRIOR_MATCHES)
        teams[int(tid)] = TeamStrength(
            team_id=int(tid),
            attack=round(1 + shrink * (att_raw - 1), 4),
            defence=round(1 + shrink * (def_raw - 1), 4),
            matches=len(g),
        )
    return StrengthModel(
        league_home_goals=round(league_home, 4),
        league_away_goals=round(league_away, 4),
        teams=teams,
        matches_used=int(f["match_id"].nunique()),
        window_start=f["kickoff_at"].min().to_pydatetime(),
        window_end=f["kickoff_at"].max().to_pydatetime(),
        uses_xg=bool(has_xg.any()),
    )

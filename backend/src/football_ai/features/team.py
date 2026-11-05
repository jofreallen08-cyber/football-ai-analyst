"""Team-level features: form, home/away splits, statistic averages, xG series."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

import pandas as pd

from football_ai.features.frames import finished, none_if_nan

METRIC_LABELS = {
    "xg": "xG",
    "xga": "xG concessi",
    "shots": "tiri",
    "shots_on_target": "tiri in porta",
    "possession_pct": "possesso palla",
    "corners": "calci d'angolo",
    "fouls": "falli",
    "yellow_cards": "ammonizioni",
    "red_cards": "espulsioni",
    "pass_accuracy_pct": "precisione passaggi",
    "opp_shots": "tiri concessi",
}
# metrics where a lower value is better (used for percentile direction)
LOWER_IS_BETTER = {"xga", "fouls", "yellow_cards", "red_cards", "opp_shots"}


@dataclass
class FormMatch:
    match_id: int
    kickoff_at: datetime
    opponent_id: int
    is_home: bool
    gf: int
    ga: int
    result: str
    xg: float | None
    xga: float | None


@dataclass
class FormSummary:
    sample_size: int
    wins: int
    draws: int
    losses: int
    points: int
    ppg: float | None
    goals_for: int
    goals_against: int
    xg_for: float | None
    xg_against: float | None
    matches: list[FormMatch]


def form(
    df: pd.DataFrame,
    team_id: int,
    n: int = 5,
    before: datetime | None = None,
    venue: str | None = None,
) -> FormSummary:
    """Last ``n`` finished matches of ``team_id`` (most recent first)."""
    t = finished(df, before)
    t = t[t["team_id"] == team_id]
    if venue == "home":
        t = t[t["is_home"]]
    elif venue == "away":
        t = t[~t["is_home"]]
    last = t.sort_values("kickoff_at").tail(n).iloc[::-1]
    xg_ok = last["xg"].notna()
    return FormSummary(
        sample_size=len(last),
        wins=int((last["result"] == "W").sum()),
        draws=int((last["result"] == "D").sum()),
        losses=int((last["result"] == "L").sum()),
        points=int(last["points"].sum()),
        ppg=none_if_nan(last["points"].mean()) if len(last) else None,
        goals_for=int(last["gf"].sum()),
        goals_against=int(last["ga"].sum()),
        xg_for=none_if_nan(last.loc[xg_ok, "xg"].sum()) if xg_ok.any() else None,
        xg_against=none_if_nan(last.loc[xg_ok, "xga"].sum()) if xg_ok.any() else None,
        matches=[
            FormMatch(
                match_id=int(r.match_id),
                kickoff_at=r.kickoff_at.to_pydatetime(),
                opponent_id=int(r.opponent_id),
                is_home=bool(r.is_home),
                gf=int(r.gf),
                ga=int(r.ga),
                result=str(r.result),
                xg=none_if_nan(r.xg),
                xga=none_if_nan(r.xga),
            )
            for r in last.itertuples()
        ],
    )


@dataclass
class SplitSummary:
    played: int
    wins: int
    draws: int
    losses: int
    ppg: float | None
    goals_for_pg: float | None
    goals_against_pg: float | None
    xg_pg: float | None
    xga_pg: float | None
    xg_coverage: int


def _split(t: pd.DataFrame) -> SplitSummary:
    has_xg = t["xg"].notna()
    return SplitSummary(
        played=len(t),
        wins=int((t["result"] == "W").sum()),
        draws=int((t["result"] == "D").sum()),
        losses=int((t["result"] == "L").sum()),
        ppg=none_if_nan(t["points"].mean()) if len(t) else None,
        goals_for_pg=none_if_nan(t["gf"].mean()) if len(t) else None,
        goals_against_pg=none_if_nan(t["ga"].mean()) if len(t) else None,
        xg_pg=none_if_nan(t.loc[has_xg, "xg"].mean()) if has_xg.any() else None,
        xga_pg=none_if_nan(t.loc[has_xg, "xga"].mean()) if has_xg.any() else None,
        xg_coverage=int(has_xg.sum()),
    )


def splits(
    df: pd.DataFrame, team_id: int, before: datetime | None = None
) -> dict[str, SplitSummary]:
    t = finished(df, before)
    t = t[t["team_id"] == team_id]
    return {"home": _split(t[t["is_home"]]), "away": _split(t[~t["is_home"]]), "all": _split(t)}


@dataclass
class MetricSummary:
    key: str
    label: str
    per_match: float | None
    league_avg: float | None
    percentile: float | None
    matches_with_data: int
    lower_is_better: bool


@dataclass
class StatsSummary:
    matches: int
    metrics: list[MetricSummary]
    missing: list[str] = field(default_factory=list)


def stat_averages(df: pd.DataFrame, team_id: int, before: datetime | None = None) -> StatsSummary:
    """Per-match averages vs league, computed only where data exists."""
    f = finished(df, before)
    t = f[f["team_id"] == team_id]
    team_means = f.groupby("team_id")[list(METRIC_LABELS)].mean()
    metrics: list[MetricSummary] = []
    missing: list[str] = []
    for key, label in METRIC_LABELS.items():
        k = int(t[key].notna().sum())
        if k == 0:
            missing.append(f"{label}: non disponibile dalla fonte")
            metrics.append(MetricSummary(key, label, None, None, None, 0, key in LOWER_IS_BETTER))
            continue
        value = float(t[key].mean())
        col = team_means[key].dropna()
        pct = None
        if len(col) > 1:
            if key in LOWER_IS_BETTER:
                pct = float((col > value).sum() + 0.5 * ((col == value).sum() - 1)) / (len(col) - 1)
            else:
                pct = float((col < value).sum() + 0.5 * ((col == value).sum() - 1)) / (len(col) - 1)
        metrics.append(
            MetricSummary(
                key=key,
                label=label,
                per_match=none_if_nan(value),
                league_avg=none_if_nan(col.mean()),
                percentile=none_if_nan(pct * 100 if pct is not None else None, 0),
                matches_with_data=k,
                lower_is_better=key in LOWER_IS_BETTER,
            )
        )
    return StatsSummary(matches=len(t), metrics=metrics, missing=missing)


@dataclass
class SeriesPoint:
    match_id: int
    kickoff_at: datetime
    matchday: int | None
    opponent_id: int
    is_home: bool
    gf: int
    ga: int
    xg: float | None
    xga: float | None
    xg_rolling: float | None
    xga_rolling: float | None


def xg_series(df: pd.DataFrame, team_id: int, window: int = 3) -> list[SeriesPoint]:
    t = finished(df)
    t = t[t["team_id"] == team_id].sort_values("kickoff_at")
    roll_xg = t["xg"].rolling(window, min_periods=window).mean()
    roll_xga = t["xga"].rolling(window, min_periods=window).mean()
    return [
        SeriesPoint(
            match_id=int(r.match_id),
            kickoff_at=r.kickoff_at.to_pydatetime(),
            matchday=int(r.matchday) if pd.notna(r.matchday) else None,
            opponent_id=int(r.opponent_id),
            is_home=bool(r.is_home),
            gf=int(r.gf),
            ga=int(r.ga),
            xg=none_if_nan(r.xg),
            xga=none_if_nan(r.xga),
            xg_rolling=none_if_nan(roll_xg.loc[i]),
            xga_rolling=none_if_nan(roll_xga.loc[i]),
        )
        for i, r in zip(t.index, t.itertuples(), strict=True)
    ]


@dataclass
class StandingRow:
    position: int
    team_id: int
    played: int
    wins: int
    draws: int
    losses: int
    goals_for: int
    goals_against: int
    goal_difference: int
    points: int
    form: list[str]


def standings(df: pd.DataFrame, before: datetime | None = None) -> list[StandingRow]:
    """League table from finished matches (sorted by points, goal difference, goals for).

    Official tie-breakers differ by league (e.g. head-to-head in Serie A / La Liga);
    this table uses the simple criteria and is labelled accordingly in the UI.
    """
    f = finished(df, before)
    teams = sorted(set(df["team_id"]))
    rows = []
    for tid in teams:
        t = f[f["team_id"] == tid].sort_values("kickoff_at")
        gf, ga = int(t["gf"].sum()), int(t["ga"].sum())
        rows.append(
            StandingRow(
                position=0,
                team_id=int(tid),
                played=len(t),
                wins=int((t["result"] == "W").sum()),
                draws=int((t["result"] == "D").sum()),
                losses=int((t["result"] == "L").sum()),
                goals_for=gf,
                goals_against=ga,
                goal_difference=gf - ga,
                points=int(t["points"].sum()),
                form=[str(x) for x in t["result"].tail(5)],
            )
        )
    rows.sort(key=lambda r: (-r.points, -r.goal_difference, -r.goals_for, r.team_id))
    for i, r in enumerate(rows, start=1):
        r.position = i
    return rows


@dataclass
class HeadToHead:
    sample_size: int
    team_a_wins: int
    draws: int
    team_b_wins: int
    team_a_goals: int
    team_b_goals: int
    matches: list[FormMatch]


def head_to_head(
    df: pd.DataFrame, team_a: int, team_b: int, before: datetime | None = None, n: int = 10
) -> HeadToHead:
    """Meetings between two teams from team A's perspective (most recent first)."""
    f = finished(df, before)
    t = f[(f["team_id"] == team_a) & (f["opponent_id"] == team_b)]
    t = t.sort_values("kickoff_at").tail(n).iloc[::-1]
    return HeadToHead(
        sample_size=len(t),
        team_a_wins=int((t["result"] == "W").sum()),
        draws=int((t["result"] == "D").sum()),
        team_b_wins=int((t["result"] == "L").sum()),
        team_a_goals=int(t["gf"].sum()),
        team_b_goals=int(t["ga"].sum()),
        matches=form(t.assign(status="finished"), team_a, n=n).matches,
    )

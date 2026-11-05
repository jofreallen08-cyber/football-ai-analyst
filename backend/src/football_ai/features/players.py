"""Player aggregates and per-90 metrics."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pandas as pd

from football_ai.features.frames import none_if_nan

MIN_MINUTES_PER90 = 270
COUNT_METRICS = [
    "goals",
    "assists",
    "shots",
    "shots_on_target",
    "xg",
    "xa",
    "key_passes",
    "tackles",
    "interceptions",
    "yellow_cards",
    "red_cards",
]
PLAYER_COLUMNS = [
    "match_id",
    "kickoff_at",
    "player_id",
    "team_id",
    "minutes",
    "started",
    *COUNT_METRICS,
    "passes",
    "pass_accuracy_pct",
]


def player_frame(rows: list[dict[str, Any]]) -> pd.DataFrame:
    df = pd.DataFrame(rows, columns=PLAYER_COLUMNS)
    for c in ["minutes", *COUNT_METRICS, "passes", "pass_accuracy_pct"]:
        df[c] = pd.to_numeric(df[c], errors="coerce").astype(float)
    df["kickoff_at"] = pd.to_datetime(df["kickoff_at"], utc=True)
    return df


@dataclass
class PlayerAggregate:
    player_id: int
    team_id: int
    appearances: int
    starts: int
    minutes: int
    totals: dict[str, float | None]
    per90: dict[str, float | None]
    per90_reliable: bool
    missing: list[str] = field(default_factory=list)


def aggregate_players(df: pd.DataFrame) -> list[PlayerAggregate]:
    out = []
    for (pid, tid), g in df.groupby(["player_id", "team_id"]):
        minutes = int(g["minutes"].sum()) if g["minutes"].notna().any() else 0
        totals: dict[str, float | None] = {}
        per90: dict[str, float | None] = {}
        missing = []
        reliable = minutes >= MIN_MINUTES_PER90
        for m in COUNT_METRICS:
            if g[m].notna().any():
                total = float(g[m].sum())
                totals[m] = none_if_nan(total)
                per90[m] = none_if_nan(total / minutes * 90) if reliable else None
            else:
                totals[m] = None
                per90[m] = None
                missing.append(m)
        out.append(
            PlayerAggregate(
                player_id=int(pid),
                team_id=int(tid),
                appearances=int((g["minutes"].fillna(0) > 0).sum()),
                starts=int(g["started"].fillna(False).astype(bool).sum()),
                minutes=minutes,
                totals=totals,
                per90=per90,
                per90_reliable=reliable,
                missing=missing,
            )
        )
    return out


def leaders(
    aggs: list[PlayerAggregate], metric: str, n: int = 10, per90: bool = False
) -> list[PlayerAggregate]:
    if metric not in COUNT_METRICS:
        raise ValueError(f"metrica non supportata: {metric}")

    def source(a: PlayerAggregate) -> float | None:
        return (a.per90 if per90 else a.totals).get(metric)

    ranked = [a for a in aggs if source(a) is not None]
    ranked.sort(key=lambda a: (-(source(a) or 0.0), -a.minutes, a.player_id))
    return ranked[:n]

"""Builds the team-centric match frame used by every feature."""

from __future__ import annotations

from datetime import datetime
from typing import Any

import numpy as np
import pandas as pd

STAT_COLUMNS = [
    "xg",
    "shots",
    "shots_on_target",
    "possession_pct",
    "corners",
    "fouls",
    "yellow_cards",
    "red_cards",
    "passes",
    "pass_accuracy_pct",
]
FRAME_COLUMNS = [
    "match_id",
    "season_id",
    "kickoff_at",
    "matchday",
    "status",
    "team_id",
    "opponent_id",
    "is_home",
    "gf",
    "ga",
    *STAT_COLUMNS,
    "xga",
    "opp_shots",
    "opp_shots_on_target",
]


def team_match_frame(rows: list[dict[str, Any]]) -> pd.DataFrame:
    """Convert one-row-per-match dicts into two rows per match (one per team).

    Each input row needs: match_id, season_id, kickoff_at, matchday, status,
    home_team_id, away_team_id, home_score, away_score and optional
    ``home_<stat>`` / ``away_<stat>`` keys (``None`` = not available).
    """
    out: list[dict[str, Any]] = []
    for r in rows:
        for side, other in (("home", "away"), ("away", "home")):
            rec: dict[str, Any] = {
                "match_id": r["match_id"],
                "season_id": r["season_id"],
                "kickoff_at": r["kickoff_at"],
                "matchday": r.get("matchday"),
                "status": r["status"],
                "team_id": r[f"{side}_team_id"],
                "opponent_id": r[f"{other}_team_id"],
                "is_home": side == "home",
                "gf": r.get(f"{side}_score"),
                "ga": r.get(f"{other}_score"),
            }
            for c in STAT_COLUMNS:
                rec[c] = r.get(f"{side}_{c}")
            rec["xga"] = r.get(f"{other}_xg")
            rec["opp_shots"] = r.get(f"{other}_shots")
            rec["opp_shots_on_target"] = r.get(f"{other}_shots_on_target")
            out.append(rec)
    df = pd.DataFrame(out, columns=FRAME_COLUMNS)
    for c in ["gf", "ga", *STAT_COLUMNS, "xga", "opp_shots", "opp_shots_on_target"]:
        df[c] = pd.to_numeric(df[c], errors="coerce").astype(float)
    df["kickoff_at"] = pd.to_datetime(df["kickoff_at"], utc=True)
    df["result"] = None
    df.loc[df["gf"] > df["ga"], "result"] = "W"
    df.loc[df["gf"] == df["ga"], "result"] = "D"
    df.loc[df["gf"] < df["ga"], "result"] = "L"
    df["points"] = df["result"].map({"W": 3, "D": 1, "L": 0})
    return df.sort_values(["kickoff_at", "match_id", "is_home"]).reset_index(drop=True)


def finished(df: pd.DataFrame, before: datetime | None = None) -> pd.DataFrame:
    """Finished matches (with a known score), optionally strictly before ``before``."""
    mask = (df["status"] == "finished") & df["gf"].notna() & df["ga"].notna()
    if before is not None:
        mask &= df["kickoff_at"] < pd.Timestamp(before)
    return df[mask]


def none_if_nan(x: Any, digits: int = 2) -> float | None:
    if x is None:
        return None
    try:
        f = float(x)
    except (TypeError, ValueError):
        return None
    return None if np.isnan(f) else round(f, digits)

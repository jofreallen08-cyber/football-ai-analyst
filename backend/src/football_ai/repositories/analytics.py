"""Loads database rows into the DataFrames consumed by :mod:`football_ai.features`."""

from __future__ import annotations

from typing import Any

import pandas as pd
from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session, aliased

from football_ai.features.frames import STAT_COLUMNS, team_match_frame
from football_ai.features.players import player_frame
from football_ai.models import Match, MatchTeamStats, PlayerMatchStats

HS = aliased(MatchTeamStats, name="hs")
AS = aliased(MatchTeamStats, name="as_")


def _rows(session: Session, where: Any) -> list[dict[str, Any]]:
    stmt = (
        select(Match, HS, AS)
        .outerjoin(HS, and_(HS.match_id == Match.id, HS.team_id == Match.home_team_id))
        .outerjoin(AS, and_(AS.match_id == Match.id, AS.team_id == Match.away_team_id))
        .where(where)
    )
    out = []
    for m, hs, as_ in session.execute(stmt):
        row: dict[str, Any] = {
            "match_id": m.id,
            "season_id": m.season_id,
            "kickoff_at": m.kickoff_at,
            "matchday": m.matchday,
            "status": m.status.value,
            "home_team_id": m.home_team_id,
            "away_team_id": m.away_team_id,
            "home_score": m.home_score,
            "away_score": m.away_score,
        }
        for prefix, stats in (("home", hs), ("away", as_)):
            for c in STAT_COLUMNS:
                row[f"{prefix}_{c}"] = getattr(stats, c) if stats is not None else None
        out.append(row)
    return out


def season_frame(session: Session, season_id: int) -> pd.DataFrame:
    return team_match_frame(_rows(session, Match.season_id == season_id))


def pair_frame(session: Session, team_a: int, team_b: int) -> pd.DataFrame:
    """All matches between two teams, any season."""
    cond = or_(
        and_(Match.home_team_id == team_a, Match.away_team_id == team_b),
        and_(Match.home_team_id == team_b, Match.away_team_id == team_a),
    )
    return team_match_frame(_rows(session, cond))


def season_player_frame(
    session: Session, season_id: int, team_id: int | None = None, player_id: int | None = None
) -> pd.DataFrame:
    stmt = (
        select(PlayerMatchStats, Match.kickoff_at)
        .join(Match, Match.id == PlayerMatchStats.match_id)
        .where(Match.season_id == season_id)
    )
    if team_id is not None:
        stmt = stmt.where(PlayerMatchStats.team_id == team_id)
    if player_id is not None:
        stmt = stmt.where(PlayerMatchStats.player_id == player_id)
    rows = []
    for ps, ko in session.execute(stmt):
        rows.append(
            {
                "match_id": ps.match_id,
                "kickoff_at": ko,
                "player_id": ps.player_id,
                "team_id": ps.team_id,
                "minutes": ps.minutes,
                "started": ps.started,
                **{
                    c: getattr(ps, c)
                    for c in (
                        "goals assists shots shots_on_target xg xa key_passes tackles "
                        "interceptions yellow_cards red_cards passes pass_accuracy_pct"
                    ).split()
                },
            }
        )
    return player_frame(rows)

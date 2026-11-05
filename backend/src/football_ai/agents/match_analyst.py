"""Agent 1 — Match Analyst: form, home/away, standings, head-to-head, rest days."""

from __future__ import annotations

from typing import Any

from football_ai.agents.base import BaseAgent, results_string
from football_ai.schemas.analytics import MatchContext, TeamContext


def _team(prefix: str, t: TeamContext, venue: str, ctx: MatchContext) -> dict[str, Any]:
    f5, vf5 = t.form_last5, t.venue_form_last5
    split = t.splits.get(venue)
    last = f5.matches[0].kickoff_at if f5.matches else None
    return {
        f"{prefix}.position": t.position,
        f"{prefix}.points": t.points,
        f"{prefix}.form5.results": results_string(t),
        f"{prefix}.form5.points": f5.points if f5.sample_size else None,
        f"{prefix}.form5.goals_for": f5.goals_for if f5.sample_size else None,
        f"{prefix}.form5.goals_against": f5.goals_against if f5.sample_size else None,
        f"{prefix}.form5.sample_size": f5.sample_size,
        f"{prefix}.{venue}_form5.results": results_string(t, venue=True),
        f"{prefix}.{venue}_form5.points": vf5.points if vf5.sample_size else None,
        f"{prefix}.{venue}.played": split.played if split else None,
        f"{prefix}.{venue}.points_per_game": split.ppg if split else None,
        f"{prefix}.{venue}.goals_for_per_game": split.goals_for_pg if split else None,
        f"{prefix}.{venue}.goals_against_per_game": split.goals_against_pg if split else None,
        f"{prefix}.rest_days": (ctx.as_of - last).days if last else None,
    }


class MatchAnalystAgent(BaseAgent):
    name = "match_analyst"
    title = "Match Analyst"

    def build_evidence(self, ctx: MatchContext) -> dict[str, Any]:
        h2h = ctx.head_to_head
        return {
            **self.meta(ctx),
            **_team("home", ctx.home, "home", ctx),
            **_team("away", ctx.away, "away", ctx),
            "h2h.sample_size": h2h.sample_size,
            "h2h.home_team_wins": h2h.team_a_wins if h2h.sample_size else None,
            "h2h.draws": h2h.draws if h2h.sample_size else None,
            "h2h.away_team_wins": h2h.team_b_wins if h2h.sample_size else None,
            "h2h.home_team_goals": h2h.team_a_goals if h2h.sample_size else None,
            "h2h.away_team_goals": h2h.team_b_goals if h2h.sample_size else None,
        }

    def skip_reason(self, ctx: MatchContext, evidence: dict[str, Any]) -> str | None:
        if (
            ctx.home.form_last5.sample_size == 0
            and ctx.away.form_last5.sample_size == 0
            and (ctx.head_to_head.sample_size == 0)
        ):
            return "Nessuna partita precedente disponibile per le due squadre."
        return None

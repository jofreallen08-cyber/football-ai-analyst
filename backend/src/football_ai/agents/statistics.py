"""Agent 2 — Statistics AI: xG/xGA, shots, possession, corners, discipline, key players."""

from __future__ import annotations

from typing import Any

from football_ai.agents.base import BaseAgent
from football_ai.schemas.analytics import MatchContext, TeamContext


def _team(prefix: str, t: TeamContext) -> dict[str, Any]:
    ev: dict[str, Any] = {f"{prefix}.matches": t.stats.matches}
    for m in t.stats.metrics:
        if m.per_match is None:
            continue
        ev[f"{prefix}.{m.key}.per_match"] = m.per_match
        ev[f"{prefix}.{m.key}.league_avg"] = m.league_avg
        ev[f"{prefix}.{m.key}.percentile"] = m.percentile
        ev[f"{prefix}.{m.key}.matches_with_data"] = m.matches_with_data
    allsplit = t.splits.get("all")
    if allsplit and allsplit.xg_pg is not None and allsplit.goals_for_pg is not None:
        ev[f"{prefix}.goals_minus_xg_per_match"] = round(allsplit.goals_for_pg - allsplit.xg_pg, 2)
    if allsplit and allsplit.xga_pg is not None and allsplit.goals_against_pg is not None:
        ev[f"{prefix}.conceded_minus_xga_per_match"] = round(
            allsplit.goals_against_pg - allsplit.xga_pg, 2
        )
    f5 = t.form_last5
    if f5.xg_for is not None:
        ev[f"{prefix}.last5.xg_for"] = f5.xg_for
        ev[f"{prefix}.last5.xg_against"] = f5.xg_against
    for i, p in enumerate(t.key_players, start=1):
        base = f"{prefix}.key_player{i}"
        ev.update(
            {
                f"{base}.name": p.name,
                f"{base}.position": p.position,
                f"{base}.minutes": p.minutes,
                f"{base}.goals": p.goals,
                f"{base}.assists": p.assists,
                f"{base}.xg": p.xg,
                f"{base}.xa": p.xa,
            }
        )
    return ev


class StatisticsAgent(BaseAgent):
    name = "statistics"
    title = "Statistics AI"

    def build_evidence(
        self, ctx: MatchContext, extra: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        return {**self.meta(ctx), **_team("home", ctx.home), **_team("away", ctx.away)}

    def skip_reason(
        self, ctx: MatchContext, evidence: dict[str, Any], extra: dict[str, Any] | None = None
    ) -> str | None:
        has_metrics = any(k.endswith(".per_match") for k in evidence)
        if not has_metrics:
            return (
                "La fonte non fornisce statistiche di prestazione (xG, tiri, possesso) "
                "per questa competizione."
            )
        return None

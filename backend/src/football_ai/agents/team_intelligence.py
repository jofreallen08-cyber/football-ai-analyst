"""Agent 3 — Team Intelligence: verified availability, lineups and formations."""

from __future__ import annotations

from typing import Any

from football_ai.agents.base import BaseAgent
from football_ai.schemas.analytics import MatchContext, TeamContext


def _team(prefix: str, t: TeamContext) -> dict[str, Any]:
    ev: dict[str, Any] = {f"{prefix}.unavailable_count": len(t.availability)}
    for i, a in enumerate(t.availability, start=1):
        base = f"{prefix}.absence{i}"
        ev.update(
            {
                f"{base}.player": a.player_name,
                f"{base}.position": a.position,
                f"{base}.type": a.type,
                f"{base}.description": a.description,
                f"{base}.reported_at": a.reported_at.date().isoformat(),
                f"{base}.expected_return": a.expected_return,
                f"{base}.minutes_share": a.minutes_share,
                f"{base}.xg_share": a.xg_share,
                f"{base}.source": a.source,
            }
        )
    if t.confirmed_lineup:
        ev[f"{prefix}.confirmed_lineup.formation"] = t.confirmed_lineup.formation
        ev[f"{prefix}.confirmed_lineup.starters"] = ", ".join(t.confirmed_lineup.starters)
    if t.last_lineup:
        ev[f"{prefix}.last_lineup.date"] = t.last_lineup.kickoff_at.date().isoformat()
        ev[f"{prefix}.last_lineup.formation"] = t.last_lineup.formation
        ev[f"{prefix}.last_lineup.starters"] = ", ".join(t.last_lineup.starters)
    for formation, n in sorted(t.formation_usage.items(), key=lambda x: -x[1]):
        ev[f"{prefix}.formation_usage.{formation}"] = n
    return ev


class TeamIntelligenceAgent(BaseAgent):
    name = "team_intelligence"
    title = "Team Intelligence"

    def build_evidence(self, ctx: MatchContext) -> dict[str, Any]:
        return {
            **self.meta(ctx),
            "meta.availability_source": ctx.capabilities.get("availability", False),
            "meta.lineup_source": ctx.capabilities.get("lineups", False),
            **_team("home", ctx.home),
            **_team("away", ctx.away),
        }

    def skip_reason(self, ctx: MatchContext, evidence: dict[str, Any]) -> str | None:
        if not ctx.capabilities.get("availability") and not ctx.capabilities.get("lineups"):
            return (
                "Nessuna fonte verificata su indisponibilità e formazioni per questa competizione."
            )
        return None

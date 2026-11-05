"""Agent 4 — Simulation AI: explains deterministic simulations (never generates numbers)."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from football_ai.agents.base import BaseAgent
from football_ai.core.errors import DataUnavailableError
from football_ai.schemas.analytics import MatchContext
from football_ai.schemas.simulation import Outcome, SimulationRequest
from football_ai.services import simulation as sim

SEED = 2026
ITERATIONS = 20_000


def _outcome(prefix: str, o: Outcome) -> dict[str, Any]:
    top = o.top_scorelines[0] if o.top_scorelines else None
    return {
        f"{prefix}.expected_goals_home": o.expected_goals_home,
        f"{prefix}.expected_goals_away": o.expected_goals_away,
        f"{prefix}.home_win_share": o.home_win_share,
        f"{prefix}.draw_share": o.draw_share,
        f"{prefix}.away_win_share": o.away_win_share,
        f"{prefix}.both_score_share": o.both_score_share,
        f"{prefix}.most_frequent_scoreline": top[0] if top else None,
        f"{prefix}.most_frequent_scoreline_share": top[1] if top else None,
    }


class SimulationAgent(BaseAgent):
    name = "simulation"
    title = "Simulation AI"
    is_simulation = True

    def prepare(self, session: Session, ctx: MatchContext) -> dict[str, Any] | None:
        absent = [a.player_id for a in ctx.home.availability + ctx.away.availability]
        req = SimulationRequest(
            match_id=ctx.match.id, unavailable_player_ids=[], seed=SEED, n_iterations=ITERATIONS
        )
        try:
            opts = sim.options(session, req)
            known = {p.player_id for p in opts.home_players + opts.away_players}
            req = req.model_copy(
                update={"unavailable_player_ids": [p for p in absent if p in known]}
            )
            result = sim.run(session, req, persist=False)
        except DataUnavailableError as exc:
            return {"error": str(exc)}
        return {"simulation": result}

    def build_evidence(
        self, ctx: MatchContext, extra: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        ev: dict[str, Any] = {**self.meta(ctx), "meta.is_simulation": True}
        result = (extra or {}).get("simulation")
        if result is None:
            return ev
        w = result.training_window
        ev.update(
            {
                "sim.model_version": result.model_version,
                "sim.seed": result.seed,
                "sim.iterations": result.n_iterations,
                "sim.training_matches": w.matches_used,
                "sim.home_team_matches": w.home_matches,
                "sim.away_team_matches": w.away_matches,
                "sim.uses_xg": w.uses_xg,
                "sim.home_attack": result.strengths["home"]["attack"],
                "sim.home_defence": result.strengths["home"]["defence"],
                "sim.away_attack": result.strengths["away"]["attack"],
                "sim.away_defence": result.strengths["away"]["defence"],
                **_outcome("sim.baseline", result.baseline),
            }
        )
        if result.scenario is not None:
            ev["sim.scenario.absences"] = ", ".join(
                str(a["name"]) for a in result.scenario_description.get("absences", [])
            )
            ev.update(_outcome("sim.scenario", result.scenario))
        for i, a in enumerate(result.assumptions, start=1):
            ev[f"sim.assumption{i}"] = a
        for i, lim in enumerate(result.limitations, start=1):
            ev[f"sim.limitation{i}"] = lim
        return ev

    def skip_reason(
        self, ctx: MatchContext, evidence: dict[str, Any], extra: dict[str, Any] | None = None
    ) -> str | None:
        if extra and "error" in extra:
            return str(extra["error"])
        return None

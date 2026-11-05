"""Agent base class."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from sqlalchemy.orm import Session

from football_ai.schemas.analytics import MatchContext, TeamContext
from football_ai.schemas.football import TeamRef


def team_name(t: TeamRef) -> str:
    return t.name


def results_string(ctx_team: TeamContext, venue: bool = False) -> str | None:
    form = ctx_team.venue_form_last5 if venue else ctx_team.form_last5
    if not form.sample_size:
        return None
    letters = {"W": "V", "D": "N", "L": "P"}
    # oldest → most recent, Italian letters
    return "".join(letters[m.result] for m in reversed(form.matches))


class BaseAgent(ABC):
    name: str
    title: str
    prompt_version: str = "v1"
    #: outputs of this agent are hypothetical simulations
    is_simulation: bool = False

    def prepare(self, session: Session, ctx: MatchContext) -> dict[str, Any] | None:
        """Optional deterministic pre-computation (e.g. running a simulation)."""
        return None

    def meta(self, ctx: MatchContext) -> dict[str, Any]:
        m = ctx.match
        return {
            "meta.competition": f"{m.competition_name} {m.season_label}",
            "meta.matchday": m.matchday,
            "meta.kickoff_at": m.kickoff_at.isoformat(),
            "meta.status": m.status,
            "meta.home_team": m.home_team.name,
            "meta.away_team": m.away_team.name,
            "meta.is_synthetic": m.is_synthetic,
            "meta.data_as_of": ctx.as_of.isoformat(),
        }

    @abstractmethod
    def build_evidence(
        self, ctx: MatchContext, extra: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Flat ``key -> value`` facts the model may cite (``None`` = not available)."""

    def known_missing(self, ctx: MatchContext) -> list[str]:
        return list(ctx.missing)

    def skip_reason(
        self, ctx: MatchContext, evidence: dict[str, Any], extra: dict[str, Any] | None = None
    ) -> str | None:
        """Return a reason to skip the LLM call (insufficient data), or ``None``."""
        return None

    def sources(self, ctx: MatchContext) -> list[str]:
        return [s.key for s in ctx.sources]

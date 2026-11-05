"""Deterministic cross-checks between agents' inputs and outputs.

These run without any AI: they compare verified numbers so the Master Analyst (and the
user) see disagreements even if the language model misses them.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from football_ai.ai.schemas import AgentReport
from football_ai.schemas.analytics import MatchContext


@dataclass
class Contradiction:
    code: str
    description: str
    agents: list[str]
    severity: str  # "info" | "warning"

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def _form_vs_underlying(ctx: MatchContext) -> list[Contradiction]:
    out = []
    for side, t in (("casa", ctx.home), ("trasferta", ctx.away)):
        f = t.form_last5
        if f.sample_size < 4 or f.xg_for is None or f.xg_against is None:
            continue
        xg_diff = f.xg_for - f.xg_against
        if f.points >= 10 and xg_diff < -0.5:
            out.append(
                Contradiction(
                    "form_better_than_xg",
                    f"{t.team.name} ({side}): {f.points} punti nelle ultime {f.sample_size} partite, "
                    f"ma differenza xG negativa ({xg_diff:+.2f}). I risultati superano il rendimento sottostante.",
                    ["match_analyst", "statistics"],
                    "warning",
                )
            )
        if f.points <= 4 and xg_diff > 0.5:
            out.append(
                Contradiction(
                    "form_worse_than_xg",
                    f"{t.team.name} ({side}): solo {f.points} punti nelle ultime {f.sample_size} partite, "
                    f"ma differenza xG positiva ({xg_diff:+.2f}). "
                    "I risultati sono inferiori al rendimento sottostante.",
                    ["match_analyst", "statistics"],
                    "warning",
                )
            )
    return out


def _table_vs_simulation(ctx: MatchContext, sim: dict[str, Any] | None) -> list[Contradiction]:
    if not sim or ctx.home.position is None or ctx.away.position is None:
        return []
    base = sim.get("baseline", {})
    hw, aw = base.get("home_win_share"), base.get("away_win_share")
    if hw is None or aw is None:
        return []
    gap = ctx.away.position - ctx.home.position  # >0: home team higher in the table
    if gap >= 5 and aw > hw:
        return [
            Contradiction(
                "table_vs_simulation",
                f"{ctx.home.team.name} è {gap} posizioni sopra in classifica, ma nelle simulazioni "
                f"prevale più spesso {ctx.away.team.name} ({aw:.0%} contro {hw:.0%}).",
                ["match_analyst", "simulation"],
                "warning",
            )
        ]
    if gap <= -5 and hw > aw:
        return [
            Contradiction(
                "table_vs_simulation",
                f"{ctx.away.team.name} è {-gap} posizioni sopra in classifica, ma nelle simulazioni "
                f"prevale più spesso {ctx.home.team.name} ({hw:.0%} contro {aw:.0%}).",
                ["match_analyst", "simulation"],
                "warning",
            )
        ]
    return []


def _absence_impact(ctx: MatchContext, sim: dict[str, Any] | None) -> list[Contradiction]:
    out = []
    for t in (ctx.home, ctx.away):
        for a in t.availability:
            if a.xg_share is not None and a.xg_share >= 0.2:
                note = ""
                if sim and sim.get("scenario"):
                    d = sim["scenario"]["home_win_share"] - sim["baseline"]["home_win_share"]
                    note = (
                        " Lo scenario simulato con le assenze sposta le vittorie della squadra "
                        f"di casa di {d * 100:+.1f} punti."
                    )
                out.append(
                    Contradiction(
                        "key_absence",
                        f"{a.player_name} ({t.team.name}) è segnalato indisponibile e vale il "
                        f"{a.xg_share:.0%} degli xG della squadra: i dati di forma e statistiche "
                        f"includono il suo contributo.{note}",
                        ["team_intelligence", "statistics", "simulation"],
                        "info",
                    )
                )
    return out


def _confidence_vs_sample(
    ctx: MatchContext, reports: dict[str, AgentReport]
) -> list[Contradiction]:
    small = ctx.home.form_last5.sample_size < 5 or ctx.away.form_last5.sample_size < 5
    high = [n for n, r in reports.items() if r.confidence == "high"]
    if small and high:
        return [
            Contradiction(
                "confidence_vs_sample",
                "Alcuni agenti dichiarano confidenza alta, ma per almeno una squadra "
                "ci sono meno di 5 partite precedenti.",
                high,
                "warning",
            )
        ]
    return []


def detect(
    ctx: MatchContext, reports: dict[str, AgentReport], simulation: dict[str, Any] | None
) -> list[Contradiction]:
    return [
        *_form_vs_underlying(ctx),
        *_table_vs_simulation(ctx, simulation),
        *_absence_impact(ctx, simulation),
        *_confidence_vs_sample(ctx, reports),
    ]

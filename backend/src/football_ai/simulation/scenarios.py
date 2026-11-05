"""Scenario modifiers. Every modifier is an explicit, user-visible assumption."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

# Illustrative tactical multipliers — NOT estimated from data. Shown to the user verbatim.
FORMATION_PROFILE: dict[str, tuple[str, float, float]] = {
    # formation: (style, attack multiplier, goals-conceded multiplier)
    "4-3-3": ("offensivo", 1.04, 1.03),
    "3-4-3": ("offensivo", 1.05, 1.04),
    "4-2-3-1": ("equilibrato", 1.00, 1.00),
    "4-4-2": ("equilibrato", 1.00, 1.00),
    "3-5-2": ("equilibrato", 0.99, 0.98),
    "4-1-4-1": ("prudente", 0.97, 0.97),
    "5-3-2": ("difensivo", 0.94, 0.94),
    "5-4-1": ("difensivo", 0.91, 0.92),
}
REPLACEMENT_SHARE = 0.5  # a substitute is assumed to recover 50% of the absent player's output
DEFENSIVE_IMPACT = {"GK": 0.15, "DEF": 0.10, "MID": 0.05, "FWD": 0.0}


@dataclass(frozen=True)
class Absence:
    player_id: int
    team: Literal["home", "away"]
    name: str
    position: str | None
    xg_share: float | None
    minutes_share: float | None


@dataclass
class Scenario:
    venue: Literal["home", "neutral", "swapped"] = "home"
    absences: list[Absence] = field(default_factory=list)
    home_formation: str | None = None
    away_formation: str | None = None
    home_usual_formation: str | None = None
    away_usual_formation: str | None = None

    def is_baseline(self) -> bool:
        return (
            self.venue == "home"
            and not self.absences
            and self.home_formation in (None, self.home_usual_formation)
            and self.away_formation in (None, self.away_usual_formation)
        )


@dataclass
class Adjustment:
    attack: dict[str, float]
    concede: dict[str, float]
    assumptions: list[str]


def _formation_delta(chosen: str | None, usual: str | None) -> tuple[float, float, str | None]:
    if not chosen or chosen == usual:
        return 1.0, 1.0, None
    if chosen not in FORMATION_PROFILE:
        raise ValueError(f"modulo non supportato: {chosen}")
    c_style, c_att, c_conc = FORMATION_PROFILE[chosen]
    u_att, u_conc = FORMATION_PROFILE[usual][1:] if usual in FORMATION_PROFILE else (1.0, 1.0)
    return c_att / u_att, c_conc / u_conc, c_style


def adjustments(s: Scenario) -> Adjustment:
    attack = {"home": 1.0, "away": 1.0}
    concede = {"home": 1.0, "away": 1.0}
    notes: list[str] = []
    for a in s.absences:
        if a.xg_share:
            factor = 1 - REPLACEMENT_SHARE * min(a.xg_share, 0.6)
            attack[a.team] *= factor
            notes.append(
                f"Assenza di {a.name}: produzione offensiva ridotta del "
                f"{(1 - factor) * 100:.1f}% (quota xG {a.xg_share * 100:.0f}%, sostituto al "
                f"{REPLACEMENT_SHARE * 100:.0f}%)."
            )
        impact = DEFENSIVE_IMPACT.get(a.position or "", 0.0) * (a.minutes_share or 0.0)
        if impact:
            concede[a.team] *= 1 + impact
            notes.append(
                f"Assenza di {a.name} ({a.position}): gol concessi +{impact * 100:.1f}% "
                "(ipotesi sull'impatto difensivo, non stimata dai dati)."
            )
        if not a.xg_share and not impact:
            notes.append(
                f"Assenza di {a.name}: nessun effetto quantificabile dai dati disponibili."
            )
    for side, chosen, usual in (
        ("home", s.home_formation, s.home_usual_formation),
        ("away", s.away_formation, s.away_usual_formation),
    ):
        att, conc, style = _formation_delta(chosen, usual)
        if style:
            attack[side] *= att
            concede[side] *= conc
            notes.append(
                f"Modulo {chosen} ({style}) per la squadra di "
                f"{'casa' if side == 'home' else 'trasferta'} invece di {usual or 'non noto'}: "
                f"attacco ×{att:.2f}, gol concessi ×{conc:.2f} (moltiplicatori illustrativi)."
            )
    if s.venue == "neutral":
        notes.append("Campo neutro: nessun vantaggio casalingo.")
    elif s.venue == "swapped":
        notes.append("Campi invertiti: la squadra ospite gioca in casa.")
    return Adjustment(attack, concede, notes)

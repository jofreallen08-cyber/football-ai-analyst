"""Output guards: grounding (evidence keys must exist) and no-betting language."""

from __future__ import annotations

import re
from collections.abc import Iterable

from football_ai.ai.schemas import AgentOutput, Finding

# Wagering vocabulary (Italian + English). Matched as word prefixes, case-insensitive.
BETTING_PATTERNS = [
    r"scommess",
    r"scommett",
    r"bookmaker",
    r"allibrator",
    r"puntat[ae]",
    r"puntare",
    r"giocat[ae] sicur",
    r"pronostic[oi] sicur",
    r"quote? (?:di|delle|dei) (?:scommess|bookmaker)",
    r"value bet",
    r"betting",
    r"\bbets?\b",
    r"\bodds\b",
    r"\bstake\b",
    r"wager",
    r"tipster",
    r"\bschedin",
    r"\bmultipl[ae] vincent",
]
_BETTING_RE = re.compile("|".join(BETTING_PATTERNS), re.IGNORECASE)


class GuardViolationError(ValueError):
    pass


def betting_terms(texts: Iterable[str]) -> list[str]:
    hits: list[str] = []
    for t in texts:
        hits.extend(m.group(0) for m in _BETTING_RE.finditer(t))
    return hits


def check_no_betting(texts: Iterable[str]) -> None:
    hits = betting_terms(texts)
    if hits:
        raise GuardViolationError(
            f"linguaggio legato alle scommesse non consentito: {sorted(set(hits))}"
        )


def ground_findings(output: AgentOutput, evidence_keys: set[str]) -> tuple[list[Finding], int]:
    """Keep only findings whose every evidence key exists in the supplied evidence."""
    kept = [f for f in output.findings if f.evidence_keys and set(f.evidence_keys) <= evidence_keys]
    return kept, len(output.findings) - len(kept)


def agent_texts(output: AgentOutput) -> list[str]:
    return [
        output.headline,
        *(f.claim for f in output.findings),
        *output.missing_information,
        *output.limitations,
    ]

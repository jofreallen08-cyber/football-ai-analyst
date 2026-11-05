"""Deterministic offline provider: no network, no cost.

It produces schema-valid reports built only from the evidence it receives, so the
whole pipeline (validation, cache, orchestration, UI) can run and be tested without
an API key. Output is clearly marked as generated offline.
"""

from __future__ import annotations

import json
from typing import Any

from football_ai.ai.llm.base import LLMResult

MOCK_NOTE = (
    "Report generato in modalità offline (fornitore AI simulato) a partire dai dati verificati."
)


def _fmt(v: Any) -> str:
    if isinstance(v, float):
        return f"{v:.2f}".rstrip("0").rstrip(".").replace(".", ",")
    return str(v)


def _agent_report(evidence: dict[str, Any], missing: list[str]) -> dict[str, Any]:
    facts = [(k, v) for k, v in evidence.items() if v is not None and not k.startswith("meta.")]
    findings = [
        {"claim": f"Dato verificato — {k}: {_fmt(v)}.", "evidence_keys": [k], "strength": "medium"}
        for k, v in facts[:4]
    ]
    return {
        "headline": f"Sintesi offline basata su {len(facts)} dati verificati.",
        "findings": findings,
        "missing_information": missing,
        "confidence": "low",
        "limitations": [MOCK_NOTE],
    }


def _master_report(payload: dict[str, Any]) -> dict[str, Any]:
    reports: dict[str, Any] = payload.get("reports", {})
    contradictions = payload.get("detected_contradictions", [])
    key_findings = []
    for agent, rep in reports.items():
        if rep and rep.get("findings"):
            first = rep["findings"][0]
            claim = first["claim"] if isinstance(first, dict) else str(first)
            key_findings.append({"agent": agent, "finding": claim})
    missing = sorted(
        {m for rep in reports.values() if rep for m in rep.get("missing_information", [])}
    )
    available = sum(1 for r in reports.values() if r and r.get("findings"))
    return {
        "summary": f"Sintesi offline di {available} report disponibili.",
        "key_findings": key_findings,
        "agreements": [],
        "contradictions": [
            {
                "description": c["description"],
                "agents": c["agents"],
                "assessment": "Non risolta (modalità offline).",
            }
            for c in contradictions
        ],
        "missing_information": missing,
        "overall_confidence": "low",
    }


class MockLLMProvider:
    name = "mock"
    model = "mock-offline-v1"
    billable = False

    def __init__(self) -> None:
        self.calls: list[str] = []

    async def complete(
        self,
        *,
        agent: str,
        system: str,
        user: str,
        schema: dict[str, Any],
        max_tokens: int,
    ) -> LLMResult:
        self.calls.append(agent)
        payload = json.loads(user.split("\n", 1)[1]) if "\n" in user else {}
        if agent == "master":
            data = _master_report(payload)
        else:
            data = _agent_report(payload.get("evidence", {}), payload.get("known_missing", []))
        return LLMResult(data=data, input_tokens=0, output_tokens=0, model=self.model)

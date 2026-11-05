"""Report schemas shared by all agents (Pydantic models + strict JSON schemas)."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

Confidence = Literal["low", "medium", "high"]


class Finding(BaseModel):
    claim: str = Field(min_length=1, max_length=600)
    evidence_keys: list[str] = Field(min_length=1)
    strength: Confidence


class AgentOutput(BaseModel):
    """What the model must return for agents 1-4."""

    headline: str = Field(min_length=1, max_length=300)
    findings: list[Finding]
    missing_information: list[str]
    confidence: Confidence
    limitations: list[str]


class AgentReport(AgentOutput):
    """Validated, stored report (model output + metadata added by the application)."""

    agent: str
    status: Literal["completed", "cached", "skipped", "failed"]
    sources: list[str]
    provider: str
    model: str
    prompt_version: str
    rejected_findings: int = 0
    is_simulation: bool = False
    error: str | None = None


def _strict_object(properties: dict[str, Any]) -> dict[str, Any]:
    return {
        "type": "object",
        "properties": properties,
        "required": list(properties),
        "additionalProperties": False,
    }


_STR_LIST = {"type": "array", "items": {"type": "string"}}
_CONF = {"type": "string", "enum": ["low", "medium", "high"]}

AGENT_OUTPUT_SCHEMA: dict[str, Any] = _strict_object(
    {
        "headline": {"type": "string"},
        "findings": {
            "type": "array",
            "items": _strict_object(
                {"claim": {"type": "string"}, "evidence_keys": _STR_LIST, "strength": _CONF}
            ),
        },
        "missing_information": _STR_LIST,
        "confidence": _CONF,
        "limitations": _STR_LIST,
    }
)


class KeyFinding(BaseModel):
    agent: str
    finding: str = Field(min_length=1, max_length=600)


class ContradictionAssessment(BaseModel):
    description: str
    agents: list[str]
    assessment: str


class MasterOutput(BaseModel):
    summary: str = Field(min_length=1, max_length=1500)
    key_findings: list[KeyFinding]
    agreements: list[str]
    contradictions: list[ContradictionAssessment]
    missing_information: list[str]
    overall_confidence: Confidence


MASTER_OUTPUT_SCHEMA: dict[str, Any] = _strict_object(
    {
        "summary": {"type": "string"},
        "key_findings": {
            "type": "array",
            "items": _strict_object({"agent": {"type": "string"}, "finding": {"type": "string"}}),
        },
        "agreements": _STR_LIST,
        "contradictions": {
            "type": "array",
            "items": _strict_object(
                {
                    "description": {"type": "string"},
                    "agents": _STR_LIST,
                    "assessment": {"type": "string"},
                }
            ),
        },
        "missing_information": _STR_LIST,
        "overall_confidence": _CONF,
    }
)

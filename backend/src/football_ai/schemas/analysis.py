"""Analysis (orchestration) API schemas."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel

from football_ai.ai.schemas import AgentReport
from football_ai.schemas.football import MatchOut

AgentRunStatus = Literal["pending", "running", "completed", "cached", "skipped", "failed"]


class AgentInfo(BaseModel):
    name: str
    title: str
    description: str
    data_needs: list[str]
    is_simulation: bool


class AgentSlot(BaseModel):
    agent: str
    title: str
    status: AgentRunStatus
    report: AgentReport | None


class DetectedContradiction(BaseModel):
    code: str
    description: str
    agents: list[str]
    severity: str


class FinalReportOut(BaseModel):
    id: int
    analysis_run_id: uuid.UUID
    match: MatchOut
    created_at: datetime
    generated_by: Literal["ai", "automatic"]
    provider: str
    model: str
    summary: str
    key_findings: list[dict[str, str]]
    agreements: list[str]
    contradictions: list[dict[str, Any]]
    detected_contradictions: list[DetectedContradiction]
    missing_information: list[str]
    confidence: str
    agent_statuses: dict[str, str]
    sources: list[dict[str, Any]]
    data_as_of: datetime
    disclaimer: str


class AnalysisOut(BaseModel):
    id: uuid.UUID
    match: MatchOut
    status: str
    reused: bool = False
    provider: str
    model: str
    requested_at: datetime
    started_at: datetime | None
    finished_at: datetime | None
    error: str | None
    agents: list[AgentSlot]
    final_report: FinalReportOut | None


class AnalysisSummary(BaseModel):
    id: uuid.UUID
    match: MatchOut
    status: str
    requested_at: datetime
    finished_at: datetime | None
    confidence: str | None
    summary: str | None
    generated_by: str | None


class AnalysisRequest(BaseModel):
    match_id: int
    force: bool = False


class AIUsageOut(BaseModel):
    provider: str
    model: str
    effort: str
    billable: bool
    today_calls: int
    today_tokens: int
    by_agent: dict[str, int]
    limits: dict[str, int]
    cache_entries: int
    cache_hits: int

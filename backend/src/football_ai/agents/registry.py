"""Registry of available agents."""

from __future__ import annotations

from football_ai.agents.base import BaseAgent
from football_ai.agents.match_analyst import MatchAnalystAgent
from football_ai.agents.statistics import StatisticsAgent
from football_ai.agents.team_intelligence import TeamIntelligenceAgent

AGENTS: dict[str, BaseAgent] = {
    a.name: a for a in (MatchAnalystAgent(), StatisticsAgent(), TeamIntelligenceAgent())
}

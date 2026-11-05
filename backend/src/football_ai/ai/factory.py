"""Builds the configured LLM provider."""

from __future__ import annotations

from football_ai.ai.llm.anthropic import AnthropicProvider
from football_ai.ai.llm.base import LLMProvider
from football_ai.ai.llm.mock import MockLLMProvider
from football_ai.core.config import Settings


def build_llm(settings: Settings) -> LLMProvider:
    if settings.ai_provider == "anthropic":
        key = settings.anthropic_api_key.get_secret_value() if settings.anthropic_api_key else None
        return AnthropicProvider(
            model=settings.ai_model,
            effort=settings.ai_effort,
            api_key=key,
            timeout=settings.ai_timeout_seconds,
        )
    return MockLLMProvider()

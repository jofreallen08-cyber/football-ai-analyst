"""LLM provider interface."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol


@dataclass
class LLMResult:
    data: dict[str, Any]
    input_tokens: int
    output_tokens: int
    model: str
    request_id: str | None = None


class LLMError(Exception):
    """Provider call failed (network, API error, invalid output)."""


class LLMRefusalError(LLMError):
    """The model declined the request (``stop_reason == "refusal"``)."""


class LLMProvider(Protocol):
    name: str
    model: str
    #: whether calls cost money / count against the budget
    billable: bool

    async def complete(
        self,
        *,
        agent: str,
        system: str,
        user: str,
        schema: dict[str, Any],
        max_tokens: int,
    ) -> LLMResult:
        """Return JSON output that conforms to ``schema``."""
        ...

"""Anthropic Claude provider (official SDK, structured JSON outputs)."""

from __future__ import annotations

import json
from typing import Any, cast

import anthropic
from anthropic.types.beta import BetaOutputConfigParam

from football_ai.ai.llm.base import LLMError, LLMRefusalError, LLMResult
from football_ai.core.logging import get_logger

log = get_logger(__name__)
FALLBACK_BETA = "server-side-fallback-2026-07-01"


class AnthropicProvider:
    """Calls the Messages API with ``output_config.format`` (JSON schema).

    * The API key is read by the SDK from ``ANTHROPIC_API_KEY`` (never logged).
    * Server-side refusal fallback (``fallbacks: "default"``) is enabled so a safety
      decline is retried on Anthropic's recommended fallback model; a final refusal
      is surfaced as :class:`LLMRefusalError`, never as fabricated content.
    """

    name = "anthropic"
    billable = True

    def __init__(
        self,
        *,
        model: str,
        effort: str = "medium",
        api_key: str | None = None,
        timeout: float = 120.0,
        client: anthropic.AsyncAnthropic | None = None,
    ) -> None:
        self.model = model
        self.effort = effort
        self._client = client or anthropic.AsyncAnthropic(
            api_key=api_key, timeout=timeout, max_retries=2
        )

    async def complete(
        self,
        *,
        agent: str,
        system: str,
        user: str,
        schema: dict[str, Any],
        max_tokens: int,
    ) -> LLMResult:
        try:
            response = await self._client.beta.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                system=system,
                messages=[{"role": "user", "content": user}],
                output_config=cast(
                    BetaOutputConfigParam,
                    {"effort": self.effort, "format": {"type": "json_schema", "schema": schema}},
                ),
                betas=[FALLBACK_BETA],
                fallbacks="default",
            )
        except anthropic.RateLimitError as exc:
            raise LLMError("limite di richieste del fornitore AI raggiunto") from exc
        except anthropic.AuthenticationError as exc:
            raise LLMError("chiave API del fornitore AI non valida o mancante") from exc
        except anthropic.APIStatusError as exc:
            raise LLMError(f"errore del fornitore AI (HTTP {exc.status_code})") from exc
        except anthropic.APIConnectionError as exc:
            raise LLMError("fornitore AI non raggiungibile") from exc

        request_id = getattr(response, "_request_id", None)
        if response.stop_reason == "refusal":
            category = getattr(response.stop_details, "category", None)
            raise LLMRefusalError(f"richiesta rifiutata dal modello (categoria: {category})")
        if response.stop_reason == "max_tokens":
            raise LLMError("risposta troncata: limite di token raggiunto")
        text = next((b.text for b in response.content if b.type == "text"), None)
        if text is None:
            raise LLMError("risposta senza contenuto testuale")
        try:
            data = json.loads(text)
        except ValueError as exc:
            raise LLMError("risposta non in formato JSON") from exc
        log.info(
            "llm_call",
            agent=agent,
            model=response.model,
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
            request_id=request_id,
        )
        return LLMResult(
            data=data,
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
            model=response.model,
            request_id=request_id,
        )

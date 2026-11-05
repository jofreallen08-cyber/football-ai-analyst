import json
from types import SimpleNamespace

import pytest

from football_ai.ai.cache import make_cache_key
from football_ai.ai.guard import (
    GuardViolationError,
    betting_terms,
    check_no_betting,
    ground_findings,
)
from football_ai.ai.llm.anthropic import FALLBACK_BETA, AnthropicProvider
from football_ai.ai.llm.base import LLMError, LLMRefusalError
from football_ai.ai.llm.mock import MockLLMProvider
from football_ai.ai.prompts import load_prompt
from football_ai.ai.schemas import AGENT_OUTPUT_SCHEMA, MASTER_OUTPUT_SCHEMA, AgentOutput


@pytest.mark.parametrize(
    "text",
    [
        "Consigliamo di puntare sulla vittoria",
        "Ottima value bet",
        "Le quote dei bookmaker sono basse",
        "Una scommessa sicura",
        "the odds favour the home side",
        "pronostico sicuro",
    ],
)
def test_betting_language_detected(text) -> None:
    assert betting_terms([text])
    with pytest.raises(GuardViolationError):
        check_no_betting([text])


@pytest.mark.parametrize(
    "text",
    [
        "Il giocatore assente rappresenta una quota del 40% dei minuti",
        "La squadra ha giocato bene in trasferta",
        "Punti a partita: 2,1",
    ],
)
def test_neutral_language_allowed(text) -> None:
    check_no_betting([text])


def test_findings_without_valid_evidence_are_dropped() -> None:
    out = AgentOutput.model_validate(
        {
            "headline": "h",
            "confidence": "low",
            "limitations": [],
            "missing_information": [],
            "findings": [
                {"claim": "ok", "evidence_keys": ["a"], "strength": "low"},
                {"claim": "inventato", "evidence_keys": ["a", "zzz"], "strength": "high"},
                {"claim": "vuoto", "evidence_keys": ["b"], "strength": "low"},
            ],
        }
    )
    kept, rejected = ground_findings(out, {"a", "b"})
    assert [f.claim for f in kept] == ["ok", "vuoto"] and rejected == 1


def test_cache_key_is_order_independent_and_input_sensitive() -> None:
    base = dict(agent="a", prompt_version="v1", provider="p", model="m", effort="medium")
    k1 = make_cache_key(**base, payload={"x": 1, "y": 2})
    k2 = make_cache_key(**base, payload={"y": 2, "x": 1})
    k3 = make_cache_key(**base, payload={"x": 1, "y": 3})
    k4 = make_cache_key(**{**base, "prompt_version": "v2"}, payload={"x": 1, "y": 2})
    assert k1 == k2 and len({k1, k3, k4}) == 3


def _assert_strict(schema) -> None:
    if schema.get("type") == "object":
        assert schema["additionalProperties"] is False
        assert set(schema["required"]) == set(schema["properties"])
        for p in schema["properties"].values():
            _assert_strict(p)
    if schema.get("type") == "array":
        _assert_strict(schema["items"])


def test_output_schemas_are_strict() -> None:
    _assert_strict(AGENT_OUTPUT_SCHEMA)
    _assert_strict(MASTER_OUTPUT_SCHEMA)


@pytest.mark.parametrize("agent", ["match_analyst", "statistics", "team_intelligence"])
def test_prompts_load_with_common_rules(agent) -> None:
    p = load_prompt(agent, "v1")
    assert "evidence_keys" in p and "scommessa" in p


async def test_mock_output_is_valid_and_grounded() -> None:
    llm = MockLLMProvider()
    user = "istruzioni\n" + json.dumps(
        {"evidence": {"meta.x": 1, "home.points": 10}, "known_missing": ["m"]}
    )
    res = await llm.complete(agent="match_analyst", system="", user=user, schema={}, max_tokens=10)
    out = AgentOutput.model_validate(res.data)
    assert out.findings[0].evidence_keys == ["home.points"]
    assert out.missing_information == ["m"]


class FakeMessages:
    def __init__(self, response):
        self.response = response
        self.kwargs = None

    async def create(self, **kwargs):
        self.kwargs = kwargs
        return self.response


def _client(response):
    msgs = FakeMessages(response)
    return SimpleNamespace(beta=SimpleNamespace(messages=msgs)), msgs


def _resp(stop="end_turn", text='{"a": 1}', details=None):
    return SimpleNamespace(
        stop_reason=stop,
        stop_details=details,
        content=[SimpleNamespace(type="thinking"), SimpleNamespace(type="text", text=text)],
        usage=SimpleNamespace(input_tokens=11, output_tokens=7),
        model="claude-opus-5-5",
        _request_id="req_1",
    )


async def test_anthropic_provider_request_shape_and_parsing() -> None:
    client, msgs = _client(_resp())
    p = AnthropicProvider(model="claude-opus-5-5", effort="medium", client=client)
    res = await p.complete(
        agent="x", system="sys", user="u", schema={"type": "object"}, max_tokens=100
    )
    assert res.data == {"a": 1} and res.input_tokens == 11 and res.request_id == "req_1"
    kw = msgs.kwargs
    assert kw["model"] == "claude-opus-5-5"
    assert kw["fallbacks"] == "default" and kw["betas"] == [FALLBACK_BETA]
    assert kw["output_config"] == {
        "effort": "medium",
        "format": {"type": "json_schema", "schema": {"type": "object"}},
    }
    assert "thinking" not in kw and "temperature" not in kw


async def test_anthropic_refusal_and_truncation_raise() -> None:
    client, _ = _client(_resp(stop="refusal", details=SimpleNamespace(category="cyber")))
    with pytest.raises(LLMRefusalError, match="cyber"):
        await AnthropicProvider(model="m", client=client).complete(
            agent="x", system="", user="", schema={}, max_tokens=1
        )
    client, _ = _client(_resp(stop="max_tokens"))
    with pytest.raises(LLMError, match="troncata"):
        await AnthropicProvider(model="m", client=client).complete(
            agent="x", system="", user="", schema={}, max_tokens=1
        )
    client, _ = _client(_resp(text="non json"))
    with pytest.raises(LLMError, match="JSON"):
        await AnthropicProvider(model="m", client=client).complete(
            agent="x", system="", user="", schema={}, max_tokens=1
        )

import json

from football_ai.core.logging import REDACTED, configure_logging, get_logger, redact_secrets


def test_redact_processor_masks_credentials() -> None:
    event = {"event": "x", "api_key": "abc", "Authorization": "Bearer t", "team": "Inter"}
    out = redact_secrets(None, "info", event)
    assert out["api_key"] == REDACTED
    assert out["Authorization"] == REDACTED
    assert out["team"] == "Inter"


def test_logs_are_json_and_redacted(capsys) -> None:
    configure_logging("INFO", json=True)
    get_logger("t").info("provider_call", anthropic_api_key="sk-secret", provider="local")
    line = capsys.readouterr().out.strip().splitlines()[-1]
    record = json.loads(line)
    assert record["anthropic_api_key"] == REDACTED
    assert record["provider"] == "local"
    assert "sk-secret" not in line

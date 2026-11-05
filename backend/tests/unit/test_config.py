from pydantic import SecretStr

from football_ai.core.config import Settings


def test_defaults_are_safe() -> None:
    s = Settings(_env_file=None)  # type: ignore[call-arg]
    assert s.api_host == "127.0.0.1"
    assert s.ai_provider == "mock"
    assert s.anthropic_api_key is None


def test_cors_origins_from_comma_separated_env(monkeypatch) -> None:
    monkeypatch.setenv("CORS_ORIGINS", "http://a.local, http://b.local")
    s = Settings(_env_file=None)  # type: ignore[call-arg]
    assert s.cors_origins == ["http://a.local", "http://b.local"]


def test_secret_never_rendered() -> None:
    s = Settings(anthropic_api_key=SecretStr("sk-very-secret"), _env_file=None)  # type: ignore[call-arg]
    assert "sk-very-secret" not in repr(s)
    assert "sk-very-secret" not in s.model_dump_json()

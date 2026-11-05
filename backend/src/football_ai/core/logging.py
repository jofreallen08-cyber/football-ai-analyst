"""Structured logging setup (structlog) with automatic secret redaction."""

from __future__ import annotations

import logging
import sys
from collections.abc import MutableMapping
from typing import Any

import structlog

_SENSITIVE_MARKERS = ("key", "secret", "token", "password", "authorization", "cookie")
REDACTED = "***"


def _is_sensitive(name: str) -> bool:
    lowered = name.lower()
    return any(marker in lowered for marker in _SENSITIVE_MARKERS)


def redact_secrets(
    _logger: Any, _method: str, event_dict: MutableMapping[str, Any]
) -> MutableMapping[str, Any]:
    """structlog processor: mask values whose key looks like a credential."""
    for name in list(event_dict):
        if name != "event" and _is_sensitive(name):
            event_dict[name] = REDACTED
    return event_dict


def configure_logging(level: str = "INFO", json: bool = True) -> None:
    """Configure stdlib logging and structlog. Safe to call more than once."""
    logging.basicConfig(format="%(message)s", stream=sys.stdout, level=level, force=True)
    renderer: Any = structlog.processors.JSONRenderer() if json else structlog.dev.ConsoleRenderer()
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            redact_secrets,
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            renderer,
        ],
        wrapper_class=structlog.make_filtering_bound_logger(logging.getLevelName(level)),
        cache_logger_on_first_use=False,
    )


def get_logger(name: str | None = None) -> Any:
    """Return a structlog logger."""
    return structlog.get_logger(name)

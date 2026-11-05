"""Versioned prompt files: ``ai/prompts/<agent>/<version>.md``."""

from __future__ import annotations

from functools import cache
from pathlib import Path

PROMPT_DIR = Path(__file__).resolve().parent / "prompts"
COMMON = "common"


@cache
def load_prompt(agent: str, version: str) -> str:
    """Common rules + agent-specific instructions (the master prompt is self-contained)."""
    specific = (PROMPT_DIR / agent / f"{version}.md").read_text(encoding="utf-8")
    if agent == "master":
        return specific.strip() + "\n"
    common = (PROMPT_DIR / COMMON / f"{version}.md").read_text(encoding="utf-8")
    return f"{common.strip()}\n\n{specific.strip()}\n"

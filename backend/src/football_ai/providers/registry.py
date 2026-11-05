"""Builds the configured providers."""

from __future__ import annotations

from football_ai.core.config import Settings
from football_ai.providers.base import DataProvider
from football_ai.providers.local_sample import LocalSampleProvider
from football_ai.providers.openfootball import OpenFootballProvider


def build_providers(settings: Settings) -> dict[str, DataProvider]:
    """Return the available providers keyed by ``provider.key``.

    Remote openfootball mode is wired in the CLI, where a database session for the
    HTTP cache is available.
    """
    samples = settings.data_dir / "samples"
    providers: list[DataProvider] = [
        LocalSampleProvider(samples / "demo"),
        OpenFootballProvider(bundled_dir=samples / "openfootball", mode="bundled"),
    ]
    return {p.key: p for p in providers}

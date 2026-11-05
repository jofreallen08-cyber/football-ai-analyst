"""Bundled local datasets in the project's own JSON format (see ``data/samples/demo``).

The shipped dataset is SYNTHETIC (fictional clubs/players) and flagged as such.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from football_ai.providers.base import (
    AvailableSeason,
    Capability,
    PAvailability,
    PCompetition,
    PMatch,
    PPlayer,
    ProviderError,
    ProviderLicense,
    PSeason,
    PSquadMember,
    PTeam,
    RecordIssue,
    SeasonBundle,
)
from football_ai.providers.validation import format_validation_error, validate_records


class LocalSampleProvider:
    key = "local_sample"
    name = "Lega Dimostrativa (dati sintetici)"
    license = ProviderLicense(
        name="Dati sintetici generati dal progetto",
        url=None,
        attribution=(
            "Dati SINTETICI: squadre, giocatori e statistiche sono inventati a scopo dimostrativo."
        ),
        commercial_use_allowed=True,
    )
    capabilities = frozenset(
        {
            Capability.COMPETITIONS,
            Capability.FIXTURES,
            Capability.RESULTS,
            Capability.TEAM_STATS,
            Capability.PLAYER_STATS,
            Capability.XG,
            Capability.LINEUPS,
            Capability.AVAILABILITY,
        }
    )
    is_synthetic = True

    def __init__(self, directory: Path) -> None:
        self.directory = directory

    def _files(self) -> list[Path]:
        return sorted(self.directory.glob("*.json"))

    def _load(self, path: Path) -> dict[str, Any]:
        try:
            data: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            raise ProviderError(f"file di esempio illeggibile: {path.name}") from exc
        return data

    async def list_available(self) -> list[AvailableSeason]:
        out = []
        for path in self._files():
            data = self._load(path)
            out.append(
                AvailableSeason(
                    data["competition"]["code"],
                    data["competition"]["name"],
                    data["season"]["label"],
                )
            )
        return out

    async def fetch_season(self, competition_code: str, season_label: str) -> SeasonBundle:
        for path in self._files():
            data = self._load(path)
            if (
                data["competition"]["code"] == competition_code
                and data["season"]["label"] == season_label
            ):
                return self._parse(data)
        raise ProviderError(f"stagione {competition_code} {season_label} non presente")

    def _parse(self, data: dict[str, Any]) -> SeasonBundle:
        if not data.get("synthetic", False):
            raise ProviderError("il dataset locale deve dichiarare 'synthetic'")
        try:
            competition = PCompetition.model_validate(data["competition"])
            season = PSeason.model_validate(data["season"])
        except ValidationError as exc:
            raise ProviderError(format_validation_error(exc)) from exc
        issues: list[RecordIssue] = []
        updated = data.get("source_updated_at")
        return SeasonBundle(
            competition=competition,
            season=season,
            teams=validate_records(PTeam, data.get("teams", []), "team", issues),
            players=validate_records(PPlayer, data.get("players", []), "player", issues),
            squads=validate_records(PSquadMember, data.get("squads", []), "squad", issues),
            matches=validate_records(PMatch, data.get("matches", []), "match", issues),
            availability=validate_records(
                PAvailability, data.get("availability", []), "availability", issues
            ),
            source_updated_at=datetime.fromisoformat(updated) if updated else None,
            issues=issues,
        )

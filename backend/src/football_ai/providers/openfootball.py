"""openfootball/football.json — public-domain fixtures and results (no advanced stats).

Modes:
* ``bundled`` (default): snapshot shipped in ``data/samples/openfootball`` — offline.
* ``remote``: fetched from GitHub through :class:`CachedHttpClient` (cache + rate limit).

Statistics such as xG, shots or possession are *not* provided by this source and are
therefore left empty — never estimated.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import UTC, datetime, time, timedelta
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from pydantic import ValidationError

from football_ai.providers.base import (
    AvailableSeason,
    Capability,
    PCompetition,
    PMatch,
    ProviderError,
    ProviderLicense,
    PSeason,
    PTeam,
    RecordIssue,
    SeasonBundle,
)
from football_ai.providers.http import CachedHttpClient
from football_ai.providers.validation import format_validation_error


@dataclass(frozen=True)
class _League:
    code: str
    file: str
    name: str
    country: str
    tz: str


LEAGUES = {
    "SA": _League("SA", "it.1", "Serie A", "Italia", "Europe/Rome"),
    "PL": _League("PL", "en.1", "Premier League", "Inghilterra", "Europe/London"),
    "PD": _League("PD", "es.1", "La Liga", "Spagna", "Europe/Madrid"),
}
SEASONS = ["2024/25", "2025/26"]
_ROUND_RE = re.compile(r"(\d+)")


def season_dir(label: str) -> str:
    """'2024/25' -> '2024-25' (openfootball folder naming)."""
    return label.replace("/", "-")


class OpenFootballProvider:
    key = "openfootball"
    name = "openfootball (football.json)"
    license = ProviderLicense(
        name="Public Domain (CC0)",
        url="https://github.com/openfootball/football.json",
        attribution="Risultati e calendari: openfootball/football.json (pubblico dominio).",
        commercial_use_allowed=True,
    )
    capabilities = frozenset({Capability.COMPETITIONS, Capability.FIXTURES, Capability.RESULTS})
    is_synthetic = False

    def __init__(
        self,
        *,
        bundled_dir: Path,
        mode: str = "bundled",
        base_url: str = "",
        http: CachedHttpClient | None = None,
        now: datetime | None = None,
    ) -> None:
        if mode == "remote" and http is None:
            raise ValueError("la modalità remote richiede un client HTTP")
        self.bundled_dir = bundled_dir
        self.mode = mode
        self.base_url = base_url.rstrip("/")
        self.http = http
        self._now = now

    async def list_available(self) -> list[AvailableSeason]:
        return [
            AvailableSeason(code, league.name, label)
            for code, league in LEAGUES.items()
            for label in SEASONS
        ]

    async def _raw(self, league: _League, label: str) -> dict[str, Any]:
        rel = f"{season_dir(label)}/{league.file}.json"
        if self.mode == "remote":
            assert self.http is not None
            data = await self.http.get_json(f"{self.base_url}/{rel}", ttl=timedelta(hours=6))
        else:
            path = self.bundled_dir / rel
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, ValueError) as exc:
                raise ProviderError(f"snapshot openfootball mancante: {rel}") from exc
        if not isinstance(data, dict) or not isinstance(data.get("matches"), list):
            raise ProviderError("formato openfootball inatteso")
        return data

    async def fetch_season(self, competition_code: str, season_label: str) -> SeasonBundle:
        league = LEAGUES.get(competition_code)
        if league is None or season_label not in SEASONS:
            raise ProviderError(f"stagione {competition_code} {season_label} non supportata")
        raw = await self._raw(league, season_label)
        return self.parse(raw, league, season_label)

    def parse(self, raw: dict[str, Any], league: _League, label: str) -> SeasonBundle:
        tz = ZoneInfo(league.tz)
        now = self._now or datetime.now(UTC)
        issues: list[RecordIssue] = []
        teams: dict[str, PTeam] = {}
        matches: list[PMatch] = []
        seen: set[str] = set()
        dates: list[str] = []

        for idx, m in enumerate(raw["matches"]):
            ext = ":".join(
                [
                    league.file,
                    season_dir(label),
                    str(m.get("date")),
                    str(m.get("team1")),
                    str(m.get("team2")),
                ]
            )
            try:
                record = self._match(m, ext, tz)
            except (ValidationError, ValueError, KeyError, TypeError) as exc:
                msg = format_validation_error(exc) if isinstance(exc, ValidationError) else str(exc)
                issues.append(
                    RecordIssue("match", ext, msg or "record non valido", {"index": idx, **m})
                )
                continue
            if ext in seen:
                issues.append(RecordIssue("match", ext, "partita duplicata nella fonte", dict(m)))
                continue
            seen.add(ext)
            if record.status == "scheduled" and record.kickoff_at < now - timedelta(hours=3):
                issues.append(
                    RecordIssue(
                        "match",
                        ext,
                        "partita passata senza risultato nella fonte: punteggio non disponibile",
                        dict(m),
                        severity="warning",
                    )
                )
            for name in (record.home_team_external_id, record.away_team_external_id):
                teams.setdefault(name, PTeam(external_id=name, name=name, country=league.country))
            dates.append(m["date"])
            matches.append(record)

        season_start = datetime.fromisoformat(min(dates)).date() if dates else None
        season_end = datetime.fromisoformat(max(dates)).date() if dates else None
        return SeasonBundle(
            competition=PCompetition(
                external_id=league.file, name=league.name, code=league.code, country=league.country
            ),
            season=PSeason(
                external_id=f"{league.file}:{season_dir(label)}",
                label=label,
                start_date=season_start,
                end_date=season_end,
                is_current=bool(
                    season_start and season_end and season_start <= now.date() <= season_end
                ),
            ),
            teams=sorted(teams.values(), key=lambda t: t.name),
            matches=matches,
            issues=issues,
        )

    @staticmethod
    def _match(m: dict[str, Any], ext: str, tz: ZoneInfo) -> PMatch:
        day = datetime.fromisoformat(m["date"]).date()
        hhmm = m.get("time")
        kick_local = time.fromisoformat(hhmm) if hhmm else time(15, 0)
        kickoff = datetime.combine(day, kick_local, tz).astimezone(UTC)
        score = m.get("score")
        ft: Any = None
        ht: Any = None
        if isinstance(score, list):
            ft = score
        elif isinstance(score, dict):
            ft, ht = score.get("ft"), score.get("ht")
        round_match = _ROUND_RE.search(str(m.get("round", "")))
        payload: dict[str, Any] = {
            "external_id": ext,
            "kickoff_at": kickoff,
            "matchday": int(round_match.group(1)) if round_match else None,
            "home_team_external_id": m["team1"],
            "away_team_external_id": m["team2"],
            "status": "finished" if ft else "scheduled",
        }
        if ft:
            payload.update(home_score=ft[0], away_score=ft[1])
        if ht:
            payload.update(home_score_ht=ht[0], away_score_ht=ht[1])
        return PMatch.model_validate(payload)

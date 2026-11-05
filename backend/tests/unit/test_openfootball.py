from datetime import UTC, datetime
from pathlib import Path

import pytest

from football_ai.providers.base import ProviderError
from football_ai.providers.openfootball import LEAGUES, OpenFootballProvider

NOW = datetime(2026, 11, 5, tzinfo=UTC)
DATA = Path(__file__).resolve().parents[2] / "data" / "samples" / "openfootball"


def _provider() -> OpenFootballProvider:
    return OpenFootballProvider(bundled_dir=DATA, now=NOW)


def test_parses_all_score_formats_and_timezones() -> None:
    raw = {
        "name": "Test",
        "matches": [
            {
                "round": "Matchday 1",
                "date": "2025-08-23",
                "time": "18:30",
                "team1": "A",
                "team2": "B",
                "score": {"ht": [1, 0], "ft": [2, 1]},
            },
            {
                "round": "Matchday 1",
                "date": "2025-08-23",
                "time": "20:45",
                "team1": "C",
                "team2": "D",
                "score": [0, 0],
            },
            {
                "round": "Matchday 2",
                "date": "2026-12-01",
                "time": "20:45",
                "team1": "A",
                "team2": "C",
                "score": {},
            },
        ],
    }
    b = _provider().parse(raw, LEAGUES["SA"], "2025/26")
    m1, m2, m3 = b.matches
    assert (m1.home_score, m1.away_score, m1.home_score_ht) == (2, 1, 1)
    assert m1.kickoff_at == datetime(2025, 8, 23, 16, 30, tzinfo=UTC)  # CEST → UTC
    assert (m2.status, m2.home_score, m2.home_score_ht) == ("finished", 0, None)
    assert m3.status == "scheduled" and m3.home_score is None
    assert m1.home_stats is None  # source has no statistics: never invented
    assert {t.name for t in b.teams} == {"A", "B", "C", "D"}
    assert b.issues == []


def test_past_match_without_score_is_flagged_not_invented() -> None:
    raw = {
        "matches": [
            {
                "round": "Matchday 38",
                "date": "2025-05-23",
                "time": "20:45",
                "team1": "A",
                "team2": "B",
                "score": {},
            }
        ]
    }
    b = _provider().parse(raw, LEAGUES["SA"], "2024/25")
    assert b.matches[0].home_score is None
    assert b.issues[0].severity == "warning"
    assert "non disponibile" in b.issues[0].message


def test_invalid_and_duplicate_records_become_issues() -> None:
    row = {
        "round": "Matchday 1",
        "date": "2025-08-23",
        "time": "18:30",
        "team1": "A",
        "team2": "B",
        "score": [1, 1],
    }
    raw = {
        "matches": [
            row,
            dict(row),
            {**row, "team2": "A", "date": "2025-08-24"},
            {**row, "date": "not-a-date"},
        ]
    }
    b = _provider().parse(raw, LEAGUES["SA"], "2025/26")
    assert len(b.matches) == 1
    msgs = " | ".join(i.message for i in b.issues)
    assert "duplicata" in msgs and "se stessa" in msgs
    assert all(i.severity == "error" for i in b.issues)


async def test_bundled_snapshot_loads_real_season() -> None:
    b = await _provider().fetch_season("SA", "2025/26")
    assert b.competition.name == "Serie A"
    assert len(b.matches) == 380
    assert len(b.teams) == 20
    assert all(m.home_stats is None for m in b.matches)


async def test_unknown_season_rejected() -> None:
    with pytest.raises(ProviderError):
        await _provider().fetch_season("SA", "1999/00")


def test_remote_mode_requires_http_client() -> None:
    with pytest.raises(ValueError):
        OpenFootballProvider(bundled_dir=DATA, mode="remote")

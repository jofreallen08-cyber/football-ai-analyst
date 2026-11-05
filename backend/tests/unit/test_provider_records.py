from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from football_ai.providers.base import PMatch, PTeamStats
from football_ai.providers.validation import validate_records

KO = datetime(2026, 1, 1, 15, tzinfo=UTC)


def _match(**kw):
    base = {
        "external_id": "m1",
        "kickoff_at": KO,
        "home_team_external_id": "a",
        "away_team_external_id": "b",
        "status": "finished",
        "home_score": 1,
        "away_score": 0,
    }
    return PMatch.model_validate({**base, **kw})


def test_valid_match() -> None:
    assert _match().home_score == 1


@pytest.mark.parametrize(
    "kw,msg",
    [
        ({"away_team_external_id": "a"}, "se stessa"),
        ({"home_score": None}, "senza punteggio"),
        ({"status": "scheduled"}, "in programma con punteggio"),
        ({"home_score": -1}, "greater than or equal"),
        ({"kickoff_at": datetime(2026, 1, 1, 15)}, "fuso orario"),
        ({"home_score_ht": 2}, "primo tempo"),
    ],
)
def test_invalid_match(kw, msg) -> None:
    with pytest.raises(ValidationError, match=msg):
        _match(**kw)


def test_team_stats_missing_values_stay_none() -> None:
    s = PTeamStats(shots=10)
    assert s.xg is None and s.possession_pct is None


def test_team_stats_shots_on_target_le_shots() -> None:
    with pytest.raises(ValidationError, match="tiri in porta"):
        PTeamStats(shots=3, shots_on_target=4)


def test_possession_range() -> None:
    with pytest.raises(ValidationError):
        PTeamStats(possession_pct=101)


def test_validate_records_collects_issues_without_failing() -> None:
    issues: list = []
    good = {"external_id": "t1", "name": "Squadra"}
    bad = {"external_id": "t2", "name": ""}
    from football_ai.providers.base import PTeam

    out = validate_records(PTeam, [good, bad], "team", issues)
    assert [t.external_id for t in out] == ["t1"]
    assert issues[0].external_id == "t2" and issues[0].entity_type == "team"

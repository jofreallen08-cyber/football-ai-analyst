from datetime import UTC, datetime, timedelta

import pytest

from football_ai.features.frames import team_match_frame
from football_ai.simulation import strength_model
from football_ai.simulation.engine import simulate
from football_ai.simulation.scenarios import Absence, Scenario, adjustments

T0 = datetime(2026, 1, 1, tzinfo=UTC)


def _df(with_xg: bool):
    rows = []
    i = 0
    # team 1 strong at home and away, team 2 weak, team 3 average
    for rnd in range(6):
        for h, a, hs, as_ in ((1, 2, 3, 0), (3, 1, 1, 2), (2, 3, 0, 1)):
            i += 1
            r = {
                "match_id": i,
                "season_id": 1,
                "kickoff_at": T0 + timedelta(days=7 * rnd),
                "matchday": rnd + 1,
                "status": "finished",
                "home_team_id": h,
                "away_team_id": a,
                "home_score": hs,
                "away_score": as_,
            }
            if with_xg:
                r["home_xg"], r["away_xg"] = hs + 0.2, as_ + 0.1
            rows.append(r)
    return team_match_frame(rows)


def test_strengths_order_and_shrinkage() -> None:
    m = strength_model.fit(_df(False), T0 + timedelta(days=60))
    assert m.team(1).attack > m.team(3).attack > m.team(2).attack
    assert m.team(1).defence < m.team(2).defence  # concedes less
    assert not m.uses_xg and m.matches_used == 18
    assert 0.5 < m.team(1).attack < 3  # shrunk, not extreme
    unknown = m.team(99)
    assert (unknown.attack, unknown.defence, unknown.matches) == (1.0, 1.0, 0)


def test_strengths_use_only_matches_before_as_of_and_xg_when_present() -> None:
    m = strength_model.fit(_df(True), T0 + timedelta(days=8))
    assert m.matches_used == 6 and m.uses_xg
    empty = strength_model.fit(_df(True), T0)
    assert empty.matches_used == 0 and empty.teams == {}


def test_simulation_is_reproducible_and_seed_sensitive() -> None:
    adj = adjustments(Scenario())
    a = simulate(1.6, 1.1, adj, seed=7, n=5000)
    b = simulate(1.6, 1.1, adj, seed=7, n=5000)
    c = simulate(1.6, 1.1, adj, seed=8, n=5000)
    assert a == b and a != c
    assert a.home_win_share + a.draw_share + a.away_win_share == pytest.approx(1, abs=1e-3)
    assert sum(a.goals_distribution_home) == pytest.approx(1, abs=1e-3)
    assert a.home_win_share > a.away_win_share


def test_absence_of_key_scorer_reduces_attack() -> None:
    s = Scenario(absences=[Absence(1, "home", "Bomber", "FWD", xg_share=0.4, minutes_share=0.9)])
    adj = adjustments(s)
    assert adj.attack["home"] == pytest.approx(0.8)
    base = simulate(1.6, 1.1, adjustments(Scenario()), seed=1, n=20000)
    sc = simulate(1.6, 1.1, adj, seed=1, n=20000)
    assert sc.expected_goals_home < base.expected_goals_home
    assert sc.home_win_share < base.home_win_share
    assert any("Bomber" in n for n in adj.assumptions)


def test_defender_absence_increases_goals_conceded_with_stated_assumption() -> None:
    adj = adjustments(Scenario(absences=[Absence(2, "away", "Muro", "DEF", 0.0, 1.0)]))
    assert adj.concede["away"] == pytest.approx(1.10)
    assert any("non stimata dai dati" in n for n in adj.assumptions)


def test_formation_change_is_relative_to_usual_and_validated() -> None:
    adj = adjustments(Scenario(home_formation="5-4-1", home_usual_formation="4-3-3"))
    assert adj.attack["home"] < 1 and adj.concede["home"] < 1
    assert any("illustrativi" in n for n in adj.assumptions)
    same = adjustments(Scenario(home_formation="4-3-3", home_usual_formation="4-3-3"))
    assert same.attack["home"] == 1.0 and not same.assumptions
    with pytest.raises(ValueError):
        adjustments(Scenario(home_formation="9-0-1"))


def test_baseline_detection() -> None:
    assert Scenario(home_formation="4-3-3", home_usual_formation="4-3-3").is_baseline()
    assert not Scenario(venue="neutral").is_baseline()

"""Pure feature tests on hand-built frames (no database)."""

from datetime import UTC, datetime, timedelta

import pytest

from football_ai.features import players as pf
from football_ai.features import team as tf
from football_ai.features.frames import team_match_frame

T0 = datetime(2026, 1, 1, 15, tzinfo=UTC)


def m(i, home, away, hs, as_, *, xg=None, status="finished", shots=None):
    row = {
        "match_id": i,
        "season_id": 1,
        "kickoff_at": T0 + timedelta(days=7 * i),
        "matchday": i,
        "status": status,
        "home_team_id": home,
        "away_team_id": away,
        "home_score": hs,
        "away_score": as_,
    }
    if xg:
        row["home_xg"], row["away_xg"] = xg
    if shots:
        row["home_shots"], row["away_shots"] = shots
    return row


@pytest.fixture
def df():
    return team_match_frame(
        [
            m(1, 1, 2, 2, 0, xg=(1.8, 0.4), shots=(12, 5)),
            m(2, 3, 1, 1, 1, xg=(1.0, 1.1)),
            m(3, 1, 3, 0, 1, xg=(0.9, 1.5)),
            m(4, 2, 1, 1, 3),  # no stats for this match
            m(5, 1, 2, None, None, status="scheduled"),
        ]
    )


def test_frame_has_two_rows_per_match_with_results(df) -> None:
    assert len(df) == 10
    r = df[(df.match_id == 1) & (df.team_id == 1)].iloc[0]
    assert (r.result, r.points, r.xg, r.xga) == ("W", 3, 1.8, 0.4)


def test_form_most_recent_first_and_excludes_unplayed(df) -> None:
    f = tf.form(df, 1, n=3)
    assert [x.result for x in f.matches] == ["W", "L", "D"]
    assert (f.points, f.wins, f.draws, f.losses, f.sample_size) == (4, 1, 1, 1, 3)


def test_form_xg_only_over_matches_with_data(df) -> None:
    f = tf.form(df, 1, n=5)
    assert f.xg_for == pytest.approx(3.8) and f.xg_against == pytest.approx(2.9)


def test_form_before_date_and_venue(df) -> None:
    f = tf.form(df, 1, before=T0 + timedelta(days=15))
    assert f.sample_size == 2
    assert tf.form(df, 1, venue="away").sample_size == 2


def test_splits_report_xg_coverage(df) -> None:
    s = tf.splits(df, 1)
    assert s["home"].played == 2 and s["away"].played == 2
    assert s["away"].xg_coverage == 1  # match 4 has no xG
    assert s["away"].xg_pg == pytest.approx(1.1)


def test_stat_averages_never_impute_missing(df) -> None:
    s = tf.stat_averages(df, 1)
    by = {x.key: x for x in s.metrics}
    assert by["shots"].per_match == 12 and by["shots"].matches_with_data == 1
    assert by["corners"].per_match is None
    assert any("calci d'angolo" in x for x in s.missing)


def test_percentile_respects_direction(df) -> None:
    by = {x.key: x for x in tf.stat_averages(df, 1).metrics}
    assert by["xg"].percentile == 100  # best xG of the three teams
    assert by["xga"].lower_is_better


def test_standings_order_and_points(df) -> None:
    table = tf.standings(df)
    assert [(r.team_id, r.points) for r in table] == [(1, 7), (3, 4), (2, 0)]
    assert table[0].form == ["W", "D", "L", "W"]


def test_head_to_head_from_team_a_perspective(df) -> None:
    h = tf.head_to_head(df, 1, 2)
    assert (h.sample_size, h.team_a_wins, h.team_b_wins, h.team_a_goals) == (2, 2, 0, 5)


def test_xg_series_rolling_needs_full_window(df) -> None:
    s = tf.xg_series(df, 1, window=2)
    assert s[0].xg_rolling is None and s[1].xg_rolling == pytest.approx(1.45)
    assert s[3].xg is None


def test_player_per90_threshold_and_leaders() -> None:
    rows = []
    for i in range(4):
        rows.append(
            {
                "match_id": i,
                "kickoff_at": T0,
                "player_id": 1,
                "team_id": 1,
                "minutes": 90,
                "started": True,
                "goals": 1,
                "xg": 0.5,
            }
        )
        rows.append(
            {
                "match_id": i,
                "kickoff_at": T0,
                "player_id": 2,
                "team_id": 1,
                "minutes": 20,
                "started": False,
                "goals": 1,
                "xg": 0.6,
            }
        )
    aggs = {a.player_id: a for a in pf.aggregate_players(pf.player_frame(rows))}
    assert aggs[1].per90["goals"] == 1.0 and aggs[1].per90_reliable
    assert aggs[2].per90["goals"] is None and not aggs[2].per90_reliable
    assert aggs[1].totals["tackles"] is None and "tackles" in aggs[1].missing
    top = pf.leaders(list(aggs.values()), "xg", n=1)
    assert top[0].player_id == 2
    assert [a.player_id for a in pf.leaders(list(aggs.values()), "xg", per90=True)] == [1]
    with pytest.raises(ValueError):
        pf.leaders([], "rating")

"""Seeded Monte Carlo engine. Same inputs + same seed → identical outputs."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from football_ai.simulation.scenarios import Adjustment

MAX_GOALS_BUCKET = 6


@dataclass
class SimulationResult:
    expected_goals_home: float
    expected_goals_away: float
    home_win_share: float
    draw_share: float
    away_win_share: float
    mean_goals_home: float
    mean_goals_away: float
    home_clean_sheet_share: float
    away_clean_sheet_share: float
    both_score_share: float
    top_scorelines: list[tuple[str, float]]
    goals_distribution_home: list[float]
    goals_distribution_away: list[float]


def simulate(
    lam_home: float, lam_away: float, adj: Adjustment, *, seed: int, n: int
) -> SimulationResult:
    lh = max(0.05, lam_home * adj.attack["home"] * adj.concede["away"])
    la = max(0.05, lam_away * adj.attack["away"] * adj.concede["home"])
    rng = np.random.default_rng(seed)
    gh = rng.poisson(lh, n)
    ga = rng.poisson(la, n)
    pairs, counts = np.unique(np.stack([gh, ga], axis=1), axis=0, return_counts=True)
    order = np.argsort(-counts, kind="stable")[:8]

    def dist(g: np.ndarray) -> list[float]:
        clipped = np.minimum(g, MAX_GOALS_BUCKET)
        return [round(float((clipped == k).mean()), 4) for k in range(MAX_GOALS_BUCKET + 1)]

    return SimulationResult(
        expected_goals_home=round(lh, 3),
        expected_goals_away=round(la, 3),
        home_win_share=round(float((gh > ga).mean()), 4),
        draw_share=round(float((gh == ga).mean()), 4),
        away_win_share=round(float((gh < ga).mean()), 4),
        mean_goals_home=round(float(gh.mean()), 3),
        mean_goals_away=round(float(ga.mean()), 3),
        home_clean_sheet_share=round(float((ga == 0).mean()), 4),
        away_clean_sheet_share=round(float((gh == 0).mean()), 4),
        both_score_share=round(float(((gh > 0) & (ga > 0)).mean()), 4),
        top_scorelines=[
            (f"{int(pairs[i][0])}-{int(pairs[i][1])}", round(float(counts[i] / n), 4))
            for i in order
        ],
        goals_distribution_home=dist(gh),
        goals_distribution_away=dist(ga),
    )

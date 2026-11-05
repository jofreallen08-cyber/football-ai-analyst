"""Generate the SYNTHETIC "Lega Dimostrativa" dataset (fictional clubs and players).

Purpose: demonstrate features that free real-data sources do not provide (xG, lineups,
player stats, availability). Every team, player and number here is invented and the
dataset is flagged ``synthetic: true``; the UI labels it as such everywhere.

Deterministic: the same seed always produces byte-identical output.

Usage: uv run python scripts/generate_demo_dataset.py
"""

from __future__ import annotations

import json
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any

import numpy as np

SEED = 20260822
OUT = Path(__file__).resolve().parents[1] / "data" / "samples" / "demo" / "DEMO_2026-27.json"
SEASON_START = date(2026, 8, 22)
FINISHED_ROUNDS = 11  # rounds 12-18 are scheduled (upcoming fixtures)
SOURCE_UPDATED_AT = datetime(2026, 11, 2, 9, 0, tzinfo=UTC)

# name, short, attack, defence (lower = better), possession style, formation
TEAMS = [
    ("Aquile di Montevento", "Montevento", 1.30, 0.80, 0.9, "4-3-3"),
    ("Atletico Valdoro", "Valdoro", 1.15, 0.90, 0.4, "4-2-3-1"),
    ("Borgo Azzurro", "Borgo", 0.85, 1.05, -0.3, "4-4-2"),
    ("Calcio Riviera Blu", "Riviera", 1.05, 1.00, 0.2, "4-3-3"),
    ("Dinamo Pietralunga", "Pietralunga", 0.95, 0.95, -0.5, "3-5-2"),
    ("Fortitudo Lago Scuro", "Lago Scuro", 0.80, 1.20, -0.6, "4-4-2"),
    ("Olimpia Sette Colli", "Sette Colli", 1.20, 0.85, 0.7, "4-2-3-1"),
    ("Real Castelmare", "Castelmare", 1.00, 1.10, 0.1, "3-4-3"),
    ("Sporting Valfiorita", "Valfiorita", 0.90, 1.00, 0.0, "4-3-3"),
    ("Unione Torre Alta", "Torre Alta", 0.75, 1.15, -0.4, "5-3-2"),
]

FIRST = [
    "Luca",
    "Marco",
    "Davide",
    "Matteo",
    "Andrea",
    "Pablo",
    "Diego",
    "Javier",
    "Tom",
    "Jack",
    "Samuel",
    "Nicolò",
    "Federico",
    "Alessio",
    "Iker",
    "Hugo",
    "Leo",
    "Elia",
    "Tommaso",
    "Gabriel",
    "Mattia",
    "Oscar",
    "Ruben",
    "Emil",
    "Noah",
    "Kofi",
    "Yuto",
    "Adrian",
    "Bruno",
    "Simone",
]
LAST = [
    "Bellandi",
    "Corvino",
    "Ferrandi",
    "Galvani",
    "Lombrisi",
    "Marchetto",
    "Novelli",
    "Orsatti",
    "Pellegri",
    "Rinaldo",
    "Santangeli",
    "Tornaghi",
    "Valtorta",
    "Zanardo",
    "Abadía",
    "Calvero",
    "Doranza",
    "Escudil",
    "Fontanar",
    "Arkwell",
    "Brindley",
    "Colquist",
    "Denholm",
    "Fairwater",
    "Halbrook",
    "Mensaro",
    "Okonde",
    "Takeyuki",
    "Varga-Lind",
    "Quirelli",
    "Sabatelli",
    "Treviso-Moll",
    "Uccellini",
    "Vettori",
]

# position label, x (0 own goal → 100 opponent goal), y (0 → 100 width), role group
FORMATIONS: dict[str, list[tuple[str, float, float, str]]] = {
    "4-3-3": [
        ("GK", 5, 50, "GK"),
        ("RB", 25, 85, "DEF"),
        ("CB", 22, 62, "DEF"),
        ("CB", 22, 38, "DEF"),
        ("LB", 25, 15, "DEF"),
        ("CM", 48, 70, "MID"),
        ("DM", 42, 50, "MID"),
        ("CM", 48, 30, "MID"),
        ("RW", 75, 82, "FWD"),
        ("ST", 80, 50, "FWD"),
        ("LW", 75, 18, "FWD"),
    ],
    "4-2-3-1": [
        ("GK", 5, 50, "GK"),
        ("RB", 25, 85, "DEF"),
        ("CB", 22, 62, "DEF"),
        ("CB", 22, 38, "DEF"),
        ("LB", 25, 15, "DEF"),
        ("DM", 42, 62, "MID"),
        ("DM", 42, 38, "MID"),
        ("RAM", 62, 80, "MID"),
        ("CAM", 63, 50, "MID"),
        ("LAM", 62, 20, "FWD"),
        ("ST", 82, 50, "FWD"),
    ],
    "4-4-2": [
        ("GK", 5, 50, "GK"),
        ("RB", 25, 85, "DEF"),
        ("CB", 22, 62, "DEF"),
        ("CB", 22, 38, "DEF"),
        ("LB", 25, 15, "DEF"),
        ("RM", 52, 85, "MID"),
        ("CM", 47, 60, "MID"),
        ("CM", 47, 40, "MID"),
        ("LM", 52, 15, "MID"),
        ("ST", 78, 60, "FWD"),
        ("ST", 78, 40, "FWD"),
    ],
    "3-5-2": [
        ("GK", 5, 50, "GK"),
        ("CB", 22, 72, "DEF"),
        ("CB", 20, 50, "DEF"),
        ("CB", 22, 28, "DEF"),
        ("RWB", 50, 90, "DEF"),
        ("CM", 46, 66, "MID"),
        ("DM", 40, 50, "MID"),
        ("CM", 46, 34, "MID"),
        ("LWB", 50, 10, "MID"),
        ("ST", 78, 60, "FWD"),
        ("ST", 78, 40, "FWD"),
    ],
    "3-4-3": [
        ("GK", 5, 50, "GK"),
        ("CB", 22, 72, "DEF"),
        ("CB", 20, 50, "DEF"),
        ("CB", 22, 28, "DEF"),
        ("RM", 50, 88, "DEF"),
        ("CM", 45, 60, "MID"),
        ("CM", 45, 40, "MID"),
        ("LM", 50, 12, "MID"),
        ("RW", 75, 78, "FWD"),
        ("ST", 82, 50, "FWD"),
        ("LW", 75, 22, "FWD"),
    ],
    "5-3-2": [
        ("GK", 5, 50, "GK"),
        ("RWB", 30, 90, "DEF"),
        ("CB", 20, 70, "DEF"),
        ("CB", 18, 50, "DEF"),
        ("CB", 20, 30, "DEF"),
        ("LWB", 30, 10, "DEF"),
        ("CM", 46, 68, "MID"),
        ("CM", 44, 50, "MID"),
        ("CM", 46, 32, "MID"),
        ("ST", 76, 60, "FWD"),
        ("ST", 76, 40, "FWD"),
    ],
}
SQUAD_SHAPE = {"GK": 2, "DEF": 7, "MID": 6, "FWD": 5}
XG_WEIGHT = {"GK": 0.0, "DEF": 0.06, "MID": 0.22, "FWD": 0.55}


def r2(x: float) -> float:
    return float(round(x, 2))


def round_robin(n: int) -> list[list[tuple[int, int]]]:
    teams = list(range(n))
    rounds = []
    for r in range(n - 1):
        pairs = []
        for i in range(n // 2):
            a, b = teams[i], teams[n - 1 - i]
            pairs.append((a, b) if (r + i) % 2 == 0 else (b, a))
        rounds.append(pairs)
        teams = [teams[0], teams[-1], *teams[1:-1]]
    return rounds + [[(b, a) for a, b in rnd] for rnd in rounds]


def main() -> None:
    rng = np.random.default_rng(SEED)
    used_names: set[str] = set()
    teams, players, squads = [], [], []
    roster: dict[int, list[dict[str, Any]]] = {}

    for t_idx, (name, short, *_rest) in enumerate(TEAMS):
        tid = f"demo-team-{t_idx + 1}"
        teams.append({"external_id": tid, "name": name, "short_name": short, "country": "Demo"})
        roster[t_idx] = []
        shirt = 1
        for pos, count in SQUAD_SHAPE.items():
            for k in range(count):
                while True:
                    full = f"{rng.choice(FIRST)} {rng.choice(LAST)}"
                    if full not in used_names:
                        used_names.add(full)
                        break
                pid = f"demo-player-{t_idx + 1}-{pos.lower()}{k + 1}"
                quality = float(rng.uniform(0.7, 1.3))
                birth = date(1993, 1, 1) + timedelta(days=int(rng.integers(0, 4000)))
                players.append(
                    {
                        "external_id": pid,
                        "full_name": full,
                        "primary_position": pos,
                        "birth_date": birth.isoformat(),
                        "nationality": "Demo",
                    }
                )
                squads.append(
                    {"player_external_id": pid, "team_external_id": tid, "shirt_number": shirt}
                )
                roster[t_idx].append({"id": pid, "pos": pos, "q": quality, "shirt": shirt})
                shirt += 1

    # Availability: (team, position group, index, type, from_round, to_round or None=active)
    absences = [
        (0, "FWD", 0, "injury", 9, None, "Lesione muscolare alla coscia"),
        (1, "MID", 1, "injury", 4, 7, "Distorsione alla caviglia"),
        (2, "DEF", 0, "suspension", 11, 12, "Squalifica per somma di ammonizioni"),
        (3, "FWD", 1, "injury", 10, None, "Infortunio al ginocchio"),
        (6, "MID", 0, "doubtful", 11, None, "Affaticamento, in dubbio"),
        (7, "GK", 0, "injury", 2, 5, "Frattura al dito"),
        (9, "FWD", 0, "injury", 6, None, "Lesione al polpaccio"),
    ]
    round_dates = [SEASON_START + timedelta(weeks=r) for r in range(18)]
    availability = []
    unavailable: dict[int, set[str]] = {r: set() for r in range(1, 19)}
    for i, (t, grp, k, typ, frm, to, desc) in enumerate(absences):
        pid = [p for p in roster[t] if p["pos"] == grp][k]["id"]
        end = to if to is not None else 18
        for r in range(frm, end + 1):
            if typ != "doubtful":
                unavailable[r].add(pid)
        reported = datetime.combine(round_dates[frm - 1], datetime.min.time(), UTC) - timedelta(
            days=2
        )
        availability.append(
            {
                "external_id": f"demo-absence-{i + 1}",
                "player_external_id": pid,
                "team_external_id": f"demo-team-{t + 1}",
                "type": typ,
                "description": desc,
                "reported_at": reported.isoformat(),
                "expected_return": round_dates[end - 1].isoformat() if to is None else None,
                "status": "active" if to is None or to > FINISHED_ROUNDS else "resolved",
            }
        )

    def pick_lineup(t_idx: int, rnd: int) -> tuple[str, list[dict[str, Any]]]:
        formation = TEAMS[t_idx][5]
        avail = [p for p in roster[t_idx] if p["id"] not in unavailable[rnd]]
        by_pos = {
            g: sorted((p for p in avail if p["pos"] == g), key=lambda p: -p["q"])
            for g in SQUAD_SHAPE
        }
        entries, taken = [], set()
        for label, x, y, grp in FORMATIONS[formation]:
            pool = [p for p in by_pos[grp] if p["id"] not in taken] or [
                p for g in ("MID", "DEF", "FWD") for p in by_pos[g] if p["id"] not in taken
            ]
            choice = pool[0] if rng.random() > 0.15 or len(pool) == 1 else pool[1]
            taken.add(choice["id"])
            entries.append(
                {"player": choice, "role": "starter", "position": label, "grid_x": x, "grid_y": y}
            )
        bench = [p for p in avail if p["id"] not in taken]
        for p in bench[:9]:
            entries.append(
                {
                    "player": p,
                    "role": "substitute",
                    "position": p["pos"],
                    "grid_x": None,
                    "grid_y": None,
                }
            )
        return formation, entries

    matches = []
    for rnd_idx, pairs in enumerate(round_robin(len(TEAMS))):
        rnd = rnd_idx + 1
        day = round_dates[rnd_idx]
        for m_idx, (h, a) in enumerate(pairs):
            hour = [15, 18, 20, 12, 15][m_idx % 5]
            kickoff = datetime(day.year, day.month, day.day, hour - 2, 0, tzinfo=UTC)
            match: dict[str, Any] = {
                "external_id": f"demo-match-{rnd}-{m_idx + 1}",
                "kickoff_at": kickoff.isoformat(),
                "matchday": rnd,
                "home_team_external_id": f"demo-team-{h + 1}",
                "away_team_external_id": f"demo-team-{a + 1}",
            }
            if rnd > FINISHED_ROUNDS:
                match["status"] = "scheduled"
                matches.append(match)
                continue
            th, ta = TEAMS[h], TEAMS[a]
            xg_h = 1.35 * th[2] * ta[3] * 1.10 * float(rng.gamma(9, 1 / 9))
            xg_a = 1.35 * ta[2] * th[3] * 0.92 * float(rng.gamma(9, 1 / 9))
            g_h, g_a = int(rng.poisson(xg_h)), int(rng.poisson(xg_a))
            ht_h, ht_a = int(rng.binomial(g_h, 0.45)), int(rng.binomial(g_a, 0.45))
            poss_h = float(np.clip(50 + 7 * (th[4] - ta[4]) + 3 + rng.normal(0, 4), 28, 72))

            def team_stats(xg: float, goals: int, poss: float) -> dict[str, Any]:
                shots = max(goals, int(round(xg / 0.105 + rng.normal(0, 2))), 1)  # noqa: RUF046
                sot = int(min(shots, max(goals, rng.binomial(shots, 0.36))))
                passes = int(poss * 9.4 + rng.normal(0, 25))
                return {
                    "xg": r2(xg),
                    "shots": shots,
                    "shots_on_target": sot,
                    "possession_pct": r2(poss),
                    "corners": int(rng.poisson(shots * 0.33)),
                    "fouls": int(rng.poisson(12)),
                    "yellow_cards": int(rng.poisson(1.9)),
                    "red_cards": int(rng.binomial(1, 0.04)),
                    "passes": passes,
                    "pass_accuracy_pct": r2(
                        float(np.clip(72 + (poss - 50) * 0.35 + rng.normal(0, 2.5), 60, 93))
                    ),
                    "offsides": None,
                }  # not provided by this (demo) source

            hs, as_ = team_stats(xg_h, g_h, poss_h), team_stats(xg_a, g_a, 100 - poss_h)
            match.update(
                {
                    "status": "finished",
                    "home_score": g_h,
                    "away_score": g_a,
                    "home_score_ht": ht_h,
                    "away_score_ht": ht_a,
                    "attendance": int(rng.integers(8000, 42000)),
                    "home_stats": hs,
                    "away_stats": as_,
                }
            )

            lineups, pstats = [], []
            for t_idx, stats, goals in ((h, hs, g_h), (a, as_, g_a)):
                formation, entries = pick_lineup(t_idx, rnd)
                tid = f"demo-team-{t_idx + 1}"
                announced = kickoff - timedelta(minutes=60)
                lineups.append(
                    {
                        "team_external_id": tid,
                        "formation": formation,
                        "confirmed": True,
                        "announced_at": announced.isoformat(),
                        "entries": [
                            {
                                "player_external_id": e["player"]["id"],
                                "role": e["role"],
                                "position": e["position"],
                                "grid_x": e["grid_x"],
                                "grid_y": e["grid_y"],
                                "shirt_number": e["player"]["shirt"],
                            }
                            for e in entries
                        ],
                    }
                )
                starters = [e for e in entries if e["role"] == "starter"]
                subs_used = [
                    e for e in entries if e["role"] == "substitute" and e["player"]["pos"] != "GK"
                ][: int(rng.integers(3, 6))]
                minutes: dict[str, int] = {}
                outfield = [e for e in starters if e["player"]["pos"] != "GK"]
                off_idx = rng.choice(len(outfield), size=len(subs_used), replace=False)
                for e in starters:
                    minutes[e["player"]["id"]] = 90
                for s_i, o_i in zip(subs_used, off_idx, strict=True):
                    out_min = int(rng.integers(55, 86))
                    minutes[outfield[o_i]["player"]["id"]] = out_min
                    minutes[s_i["player"]["id"]] = 90 - out_min
                played = [e for e in starters + subs_used]
                w = np.array(
                    [
                        XG_WEIGHT[e["player"]["pos"]]
                        * e["player"]["q"]
                        * minutes[e["player"]["id"]]
                        / 90
                        for e in played
                    ]
                )
                w = w / w.sum()
                xg_split = w * stats["xg"]
                shots_split = rng.multinomial(stats["shots"], w)
                goal_split = rng.multinomial(goals, w)
                assist_w = np.array(
                    [
                        (0.05 if e["player"]["pos"] == "GK" else 1.0)
                        * minutes[e["player"]["id"]]
                        / 90
                        for e in played
                    ]
                )
                assists = np.zeros(len(played), dtype=int)
                for g_i in range(len(played)):
                    for _ in range(goal_split[g_i]):
                        if rng.random() < 0.72:
                            aw = assist_w.copy()
                            aw[g_i] = 0
                            assists[rng.choice(len(played), p=aw / aw.sum())] += 1
                yc = rng.multinomial(stats["yellow_cards"], np.full(len(played), 1 / len(played)))
                for i, e in enumerate(played):
                    p = e["player"]
                    mins = minutes[p["id"]]
                    on_t = int(
                        min(shots_split[i], max(goal_split[i], rng.binomial(shots_split[i], 0.37)))
                    )
                    pstats.append(
                        {
                            "player_external_id": p["id"],
                            "team_external_id": tid,
                            "minutes": mins,
                            "started": e["role"] == "starter",
                            "position": e["position"],
                            "goals": int(goal_split[i]),
                            "assists": int(assists[i]),
                            "shots": int(shots_split[i]),
                            "shots_on_target": on_t,
                            "xg": r2(float(xg_split[i])),
                            "xa": r2(float(xg_split.sum() * assist_w[i] / assist_w.sum() * 0.7)),
                            "key_passes": int(rng.poisson(1.2 * mins / 90 * (p["pos"] != "GK"))),
                            "passes": int(rng.poisson(38 * mins / 90)),
                            "pass_accuracy_pct": r2(float(np.clip(rng.normal(81, 6), 50, 98))),
                            "tackles": int(
                                rng.poisson(
                                    (2.2 if p["pos"] in ("DEF", "MID") else 0.6) * mins / 90
                                )
                            ),
                            "interceptions": int(
                                rng.poisson((1.4 if p["pos"] == "DEF" else 0.5) * mins / 90)
                            ),
                            "yellow_cards": int(min(yc[i], 1)),
                            "red_cards": 0,
                        }
                    )
            match["lineups"] = lineups
            match["player_stats"] = pstats
            matches.append(match)

    dataset = {
        "synthetic": True,
        "notice": "Dati SINTETICI generati dal progetto: squadre, giocatori e statistiche "
        "sono inventati e servono solo a dimostrare le funzionalità.",
        "generator": {"script": "scripts/generate_demo_dataset.py", "seed": SEED},
        "source_updated_at": SOURCE_UPDATED_AT.isoformat(),
        "competition": {
            "external_id": "demo-league",
            "name": "Lega Dimostrativa",
            "code": "DEMO",
            "country": "Demo",
            "type": "league",
            "tier": 1,
        },
        "season": {
            "external_id": "demo-2026-27",
            "label": "2026/27",
            "start_date": round_dates[0].isoformat(),
            "end_date": round_dates[-1].isoformat(),
            "is_current": True,
        },
        "teams": teams,
        "players": players,
        "squads": squads,
        "matches": matches,
        "availability": availability,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(dataset, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"scritto {OUT} ({len(matches)} partite, {len(players)} giocatori)")


if __name__ == "__main__":
    main()

"""Simulation lab use-cases. All outputs are labelled SIMULATION and stored reproducibly."""

from __future__ import annotations

import uuid
from collections import Counter
from dataclasses import asdict
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from football_ai.core.errors import AppError, DataUnavailableError, NotFoundError
from football_ai.features import players as pf
from football_ai.features.frames import finished
from football_ai.models import (
    AvailabilityStatus,
    DataSource,
    Lineup,
    Match,
    Player,
    PlayerAvailability,
    Season,
    SimulationRun,
    Team,
)
from football_ai.repositories import analytics as arepo
from football_ai.schemas.football import TeamRef
from football_ai.schemas.simulation import (
    FORMATIONS,
    Outcome,
    PlayerOption,
    SimulationOptions,
    SimulationOut,
    SimulationRequest,
    SimulationSummary,
    TrainingWindow,
)
from football_ai.simulation import strength_model
from football_ai.simulation.engine import simulate
from football_ai.simulation.scenarios import Absence, Scenario, adjustments

BASE_LIMITATIONS = [
    "Modello semplificato: gol di ciascuna squadra come processi di Poisson indipendenti.",
    "Non considera dinamiche di gara (espulsioni, cambi, risultato parziale), meteo, motivazioni o calendario.",
    "Le forze delle squadre derivano solo dalle partite precedenti della stagione selezionata.",
    "Le percentuali sono frequenze sulle simulazioni eseguite, non probabilità garantite né previsioni.",
]


class InvalidScenarioError(AppError):
    status_code = 422
    code = "scenario_non_valido"
    title = "Scenario non valido"


def _ref(t: Team) -> TeamRef:
    return TeamRef(id=t.id, name=t.name, short_name=t.short_name)


def _resolve(
    session: Session, req: SimulationRequest
) -> tuple[int, Team, Team, datetime, int | None]:
    if req.match_id is not None:
        m = session.get(Match, req.match_id)
        if m is None:
            raise NotFoundError("Partita non trovata")
        return (
            m.season_id,
            session.get_one(Team, m.home_team_id),
            session.get_one(Team, m.away_team_id),
            m.kickoff_at,
            m.id,
        )
    assert req.season_id and req.home_team_id and req.away_team_id
    if session.get(Season, req.season_id) is None:
        raise NotFoundError("Stagione non trovata")
    home, away = session.get(Team, req.home_team_id), session.get(Team, req.away_team_id)
    if home is None or away is None:
        raise NotFoundError("Squadra non trovata")
    return req.season_id, home, away, datetime.now(UTC), None


def _player_options(
    session: Session, season_id: int, team_id: int, as_of: datetime, matches_played: int
) -> list[PlayerOption]:
    pdf = arepo.season_player_frame(session, season_id, team_id=team_id)
    pdf = pdf[pdf["kickoff_at"] < as_of]
    aggs = pf.aggregate_players(pdf)
    team_xg = sum((a.totals.get("xg") or 0.0) for a in aggs) or None
    team_minutes = matches_played * 90 or None
    reported = set(
        session.scalars(
            select(PlayerAvailability.player_id).where(
                PlayerAvailability.team_id == team_id,
                PlayerAvailability.status == AvailabilityStatus.ACTIVE,
                PlayerAvailability.reported_at <= as_of,
            )
        )
    )
    players = {
        p.id: p
        for p in session.scalars(select(Player).where(Player.id.in_([a.player_id for a in aggs])))
    }
    out = [
        PlayerOption(
            player_id=a.player_id,
            name=players[a.player_id].full_name,
            position=players[a.player_id].primary_position,
            minutes=a.minutes,
            minutes_share=round(a.minutes / team_minutes, 3) if team_minutes else None,
            xg_share=round((a.totals.get("xg") or 0.0) / team_xg, 3) if team_xg else None,
            reported_unavailable=a.player_id in reported,
        )
        for a in aggs
    ]
    return sorted(out, key=lambda p: (-p.minutes, p.name))


def _usual_formation(session: Session, season_id: int, team_id: int, as_of: datetime) -> str | None:
    rows = session.scalars(
        select(Lineup.formation)
        .join(Match, Match.id == Lineup.match_id)
        .where(Match.season_id == season_id, Lineup.team_id == team_id, Match.kickoff_at < as_of)
    ).all()
    counts = Counter(f for f in rows if f)
    return counts.most_common(1)[0][0] if counts else None


def options(session: Session, req: SimulationRequest) -> SimulationOptions:
    season_id, home, away, as_of, _ = _resolve(session, req)
    df = arepo.season_frame(session, season_id)
    f = finished(df, before=as_of)
    played = {tid: int((f["team_id"] == tid).sum()) for tid in (home.id, away.id)}
    return SimulationOptions(
        season_id=season_id,
        home_team=_ref(home),
        away_team=_ref(away),
        home_usual_formation=_usual_formation(session, season_id, home.id, as_of),
        away_usual_formation=_usual_formation(session, season_id, away.id, as_of),
        formations=FORMATIONS,
        home_players=_player_options(session, season_id, home.id, as_of, played[home.id]),
        away_players=_player_options(session, season_id, away.id, as_of, played[away.id]),
        as_of=as_of,
    )


def run(session: Session, req: SimulationRequest, *, persist: bool = True) -> SimulationOut:
    season_id, home, away, as_of, match_id = _resolve(session, req)
    df = arepo.season_frame(session, season_id)
    model = strength_model.fit(df, as_of)
    hs, as_ = model.team(home.id), model.team(away.id)
    if hs.matches == 0 or as_.matches == 0:
        raise DataUnavailableError(
            "Dati storici insufficienti: almeno una squadra non ha partite giocate prima della data."
        )
    opts = options(session, req)
    by_id = {p.player_id: ("home", p) for p in opts.home_players} | {
        p.player_id: ("away", p) for p in opts.away_players
    }
    absences = []
    for pid in dict.fromkeys(req.unavailable_player_ids):
        if pid not in by_id:
            raise InvalidScenarioError(
                f"Il giocatore {pid} non ha minuti registrati con nessuna delle due squadre."
            )
        side, p = by_id[pid]
        absences.append(
            Absence(pid, side, p.name, p.position, p.xg_share, p.minutes_share)  # type: ignore[arg-type]
        )
    scenario = Scenario(
        venue=req.venue,
        absences=absences,
        home_formation=req.home_formation,
        away_formation=req.away_formation,
        home_usual_formation=opts.home_usual_formation,
        away_usual_formation=opts.away_usual_formation,
    )

    def lambdas(venue: str) -> tuple[float, float]:
        if venue == "swapped":
            la, lh = model.expected_goals(away.id, home.id)
            return lh, la
        return model.expected_goals(home.id, away.id, neutral=venue == "neutral")

    baseline_adj = adjustments(Scenario())
    lam_h, lam_a = lambdas("home")
    baseline = simulate(lam_h, lam_a, baseline_adj, seed=req.seed, n=req.n_iterations)
    scenario_result = None
    notes: list[str] = []
    if not scenario.is_baseline():
        adj = adjustments(scenario)
        notes = adj.assumptions
        s_h, s_a = lambdas(req.venue)
        scenario_result = simulate(s_h, s_a, adj, seed=req.seed, n=req.n_iterations)

    src = session.scalar(
        select(DataSource)
        .join(Season, Season.source_id == DataSource.id)
        .where(Season.id == season_id)
    )
    is_synthetic = bool(src and src.is_synthetic)
    assumptions = [
        f"Modello {strength_model.MODEL_VERSION}: forze di attacco e difesa calcolate su "
        f"{model.matches_used} partite precedenti, con peso decrescente nel tempo "
        f"(emivita {int(strength_model.HALF_LIFE_DAYS)} giorni).",
        "Produzione offensiva = 60% xG + 40% gol quando gli xG sono disponibili, altrimenti solo gol."
        if model.uses_xg
        else "xG non disponibili: le forze sono calcolate solo sui gol segnati e subiti.",
        f"Campioni piccoli prudenzialmente avvicinati alla media del campionato "
        f"(peso a priori pari a {int(strength_model.PRIOR_MATCHES)} partite).",
        *notes,
    ]
    limitations = list(BASE_LIMITATIONS)
    if is_synthetic:
        limitations.append(
            "Dati di input SINTETICI (Lega Dimostrativa): squadre e numeri inventati."
        )
    if not model.uses_xg:
        limitations.append("Senza xG la stima della forza è più sensibile alla casualità dei gol.")
    if min(hs.matches, as_.matches) < 5:
        limitations.append(
            "Meno di 5 partite disponibili per almeno una squadra: stime molto incerte."
        )

    window = TrainingWindow(
        matches_used=model.matches_used,
        start=model.window_start,
        end=model.window_end,
        as_of=as_of,
        uses_xg=model.uses_xg,
        home_matches=hs.matches,
        away_matches=as_.matches,
    )
    description: dict[str, object] = {
        "venue": req.venue,
        "absences": [asdict(a) for a in absences],
        "home_formation": req.home_formation,
        "away_formation": req.away_formation,
        "home_usual_formation": opts.home_usual_formation,
        "away_usual_formation": opts.away_usual_formation,
    }
    strengths = {
        "home": {"attack": hs.attack, "defence": hs.defence},
        "away": {"attack": as_.attack, "defence": as_.defence},
        "league": {"home_goals": model.league_home_goals, "away_goals": model.league_away_goals},
    }
    run_id = uuid.uuid4()
    created = datetime.now(UTC)
    results: dict[str, Any] = {
        "baseline": asdict(baseline),
        "scenario": asdict(scenario_result) if scenario_result else None,
        "strengths": strengths,
        "is_synthetic_data": is_synthetic,
    }
    if persist:
        row = SimulationRun(
            id=run_id,
            match_id=match_id,
            season_id=season_id,
            home_team_id=home.id,
            away_team_id=away.id,
            scenario=description,
            assumptions=assumptions,
            limitations=limitations,
            model_version=strength_model.MODEL_VERSION,
            seed=req.seed,
            n_iterations=req.n_iterations,
            training_window=window.model_dump(mode="json"),
            results=results,
            is_simulation=True,
        )
        session.add(row)
        session.commit()
        created = row.created_at
    return SimulationOut(
        id=run_id,
        created_at=created,
        match_id=match_id,
        season_id=season_id,
        home_team=_ref(home),
        away_team=_ref(away),
        venue=req.venue,
        model_version=strength_model.MODEL_VERSION,
        seed=req.seed,
        n_iterations=req.n_iterations,
        training_window=window,
        strengths=strengths,
        baseline=Outcome(**asdict(baseline)),
        scenario=Outcome(**asdict(scenario_result)) if scenario_result else None,
        scenario_description=description,
        assumptions=assumptions,
        limitations=limitations,
        is_synthetic_data=is_synthetic,
    )


def get(session: Session, sim_id: uuid.UUID) -> SimulationOut:
    row = session.get(SimulationRun, sim_id)
    if row is None:
        raise NotFoundError("Simulazione non trovata")
    home, away = session.get_one(Team, row.home_team_id), session.get_one(Team, row.away_team_id)
    r = row.results
    return SimulationOut(
        id=row.id,
        created_at=row.created_at,
        match_id=row.match_id,
        season_id=row.season_id,
        home_team=_ref(home),
        away_team=_ref(away),
        venue=str(row.scenario.get("venue", "home")),
        model_version=row.model_version,
        seed=row.seed,
        n_iterations=row.n_iterations,
        training_window=TrainingWindow.model_validate(row.training_window),
        strengths=r["strengths"],
        baseline=Outcome.model_validate(r["baseline"]),
        scenario=Outcome.model_validate(r["scenario"]) if r.get("scenario") else None,
        scenario_description=row.scenario,
        assumptions=row.assumptions,
        limitations=row.limitations,
        is_synthetic_data=bool(r.get("is_synthetic_data")),
    )


def history(session: Session, limit: int = 20) -> list[SimulationSummary]:
    rows = session.scalars(
        select(SimulationRun).order_by(SimulationRun.created_at.desc()).limit(limit)
    ).all()
    teams = {
        t.id: t
        for t in session.scalars(
            select(Team).where(
                Team.id.in_({r.home_team_id for r in rows} | {r.away_team_id for r in rows})
            )
        )
    }
    out = []
    for r in rows:
        shown = r.results.get("scenario") or r.results["baseline"]
        out.append(
            SimulationSummary(
                id=r.id,
                created_at=r.created_at,
                home_team=_ref(teams[r.home_team_id]),
                away_team=_ref(teams[r.away_team_id]),
                venue=str(r.scenario.get("venue", "home")),
                seed=r.seed,
                n_iterations=r.n_iterations,
                has_scenario=r.results.get("scenario") is not None,
                home_win_share=shown["home_win_share"],
                draw_share=shown["draw_share"],
                away_win_share=shown["away_win_share"],
            )
        )
    return out

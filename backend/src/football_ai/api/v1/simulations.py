"""Simulation Lab endpoints. Every response is a SIMULATION, never a real result."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Query

from football_ai.api.deps import Limit, SessionDep
from football_ai.schemas.simulation import (
    SimulationOptions,
    SimulationOut,
    SimulationRequest,
    SimulationSummary,
)
from football_ai.services import simulation as svc

router = APIRouter(prefix="/simulations", tags=["laboratorio simulazioni"])
OptId = Annotated[int | None, Query(ge=1, le=2**62)]


@router.post("", response_model=SimulationOut, status_code=201, summary="Esegue una simulazione")
def create(session: SessionDep, req: SimulationRequest) -> SimulationOut:
    return svc.run(session, req)


@router.get("", response_model=list[SimulationSummary], summary="Storico simulazioni")
def list_(session: SessionDep, limit: Limit = 20) -> list[SimulationSummary]:
    return svc.history(session, limit)


@router.get(
    "/options", response_model=SimulationOptions, summary="Giocatori e moduli per gli scenari"
)
def options_(
    session: SessionDep,
    match_id: OptId = None,
    season_id: OptId = None,
    home_team_id: OptId = None,
    away_team_id: OptId = None,
) -> SimulationOptions:
    req = SimulationRequest(
        match_id=match_id, season_id=season_id, home_team_id=home_team_id, away_team_id=away_team_id
    )
    return svc.options(session, req)


@router.get("/{simulation_id}", response_model=SimulationOut, summary="Dettaglio simulazione")
def get(session: SessionDep, simulation_id: uuid.UUID) -> SimulationOut:
    return svc.get(session, simulation_id)

"""Version 1 of the public HTTP API."""

from fastapi import APIRouter

from football_ai.api.v1 import agents, analyses, analytics, data, health, simulations

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(health.router)
api_router.include_router(data.router)
api_router.include_router(analytics.router)
api_router.include_router(agents.router)
api_router.include_router(simulations.router)
api_router.include_router(analyses.router)

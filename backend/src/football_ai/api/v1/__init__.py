"""Version 1 of the public HTTP API."""

from fastapi import APIRouter

from football_ai.api.v1 import data, health

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(health.router)
api_router.include_router(data.router)

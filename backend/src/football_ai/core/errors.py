"""Domain exceptions and RFC 9457 (problem+json) error handlers."""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from football_ai.core.logging import get_logger

PROBLEM_JSON = "application/problem+json"
log = get_logger(__name__)


class AppError(Exception):
    """Base class for expected, user-facing errors."""

    status_code = 400
    code = "errore_applicazione"
    title = "Errore dell'applicazione"

    def __init__(self, detail: str | None = None) -> None:
        super().__init__(detail or self.title)
        self.detail = detail or self.title


class NotFoundError(AppError):
    status_code = 404
    code = "non_trovato"
    title = "Risorsa non trovata"


class DataUnavailableError(AppError):
    """Raised when requested data is not available from any verified source."""

    status_code = 404
    code = "dati_non_disponibili"
    title = "Dati non disponibili"


class ExternalServiceError(AppError):
    status_code = 502
    code = "servizio_esterno"
    title = "Errore di un servizio esterno"


def _problem(status: int, code: str, title: str, detail: Any, request: Request) -> JSONResponse:
    body = {
        "type": f"about:blank#{code}",
        "title": title,
        "status": status,
        "detail": detail,
        "instance": request.url.path,
        "request_id": getattr(request.state, "request_id", None),
    }
    return JSONResponse(body, status_code=status, media_type=PROBLEM_JSON)


def register_error_handlers(app: FastAPI) -> None:
    """Attach problem+json handlers to the application."""

    @app.exception_handler(AppError)
    async def _app_error(request: Request, exc: AppError) -> JSONResponse:
        return _problem(exc.status_code, exc.code, exc.title, exc.detail, request)

    @app.exception_handler(RequestValidationError)
    async def _validation(request: Request, exc: RequestValidationError) -> JSONResponse:
        errors = [
            {"loc": list(err.get("loc", ())), "msg": err.get("msg"), "type": err.get("type")}
            for err in exc.errors()
        ]
        return _problem(422, "validazione", "Dati di input non validi", errors, request)

    @app.exception_handler(StarletteHTTPException)
    async def _http(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        return _problem(exc.status_code, "http", str(exc.detail), exc.detail, request)

    @app.exception_handler(Exception)
    async def _unhandled(request: Request, exc: Exception) -> JSONResponse:
        log.exception("unhandled_error", path=request.url.path)
        return _problem(500, "errore_interno", "Errore interno", "Errore inatteso.", request)

"""FastAPI application factory.

Run locally with::

    uv run uvicorn football_ai.main:app --reload
"""

from __future__ import annotations

import re
import time
import uuid
from collections.abc import Awaitable, Callable

import structlog
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware

from football_ai import __version__
from football_ai.api.v1 import api_router
from football_ai.core.config import Settings, get_settings
from football_ai.core.errors import register_error_handlers
from football_ai.core.logging import configure_logging, get_logger

_REQUEST_ID_RE = re.compile(r"^[A-Za-z0-9._-]{1,64}$")
log = get_logger(__name__)


def create_app(settings: Settings | None = None) -> FastAPI:
    """Build and configure the FastAPI application."""
    settings = settings or get_settings()
    configure_logging(settings.log_level, json=settings.log_json)

    app = FastAPI(
        title=settings.app_name,
        version=__version__,
        description=(
            "API di analisi calcistica a scopo educativo. "
            "Nessuna funzione di scommessa, quote o pronostici a pagamento."
        ),
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
        allow_headers=["Content-Type", "X-Request-ID"],
        expose_headers=["X-Request-ID"],
    )

    @app.middleware("http")
    async def request_context(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        incoming = request.headers.get("x-request-id", "")
        request_id = incoming if _REQUEST_ID_RE.match(incoming) else uuid.uuid4().hex
        request.state.request_id = request_id
        structlog.contextvars.bind_contextvars(request_id=request_id)
        start = time.perf_counter()
        try:
            response = await call_next(request)
        finally:
            structlog.contextvars.unbind_contextvars("request_id")
        response.headers["X-Request-ID"] = request_id
        log.info(
            "request",
            method=request.method,
            path=request.url.path,
            status=response.status_code,
            duration_ms=round((time.perf_counter() - start) * 1000, 1),
            request_id=request_id,
        )
        return response

    register_error_handlers(app)
    app.include_router(api_router)
    return app


app = create_app()

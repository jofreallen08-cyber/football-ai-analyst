"""HTTP client for providers: database-backed cache, rate limiting, retries, breaker."""

from __future__ import annotations

import asyncio
import hashlib
import json
import random
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from typing import Any

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from football_ai.core.logging import get_logger
from football_ai.models import ProviderCache
from football_ai.providers.base import ProviderError
from football_ai.providers.rate_limit import CircuitBreaker, TokenBucket

log = get_logger(__name__)
RETRY_STATUSES = {429, 500, 502, 503, 504}


def cache_key(source_key: str, url: str, params: dict[str, Any] | None) -> str:
    canonical = json.dumps({"s": source_key, "u": url, "p": params or {}}, sort_keys=True)
    return hashlib.sha256(canonical.encode()).hexdigest()


class CachedHttpClient:
    """GET JSON with cache-first semantics. Secrets go in ``headers`` and are never logged."""

    def __init__(
        self,
        *,
        source_key: str,
        source_id_resolver: Callable[[], int],
        session_factory: Callable[[], Session],
        limiter: TokenBucket,
        breaker: CircuitBreaker | None = None,
        headers: dict[str, str] | None = None,
        transport: httpx.AsyncBaseTransport | None = None,
        max_retries: int = 3,
        backoff_base: float = 1.0,
        timeout: float = 20.0,
    ) -> None:
        self.source_key = source_key
        self._source_id = source_id_resolver
        self._session_factory = session_factory
        self._limiter = limiter
        self._breaker = breaker or CircuitBreaker()
        self._headers = headers or {}
        self._transport = transport
        self._max_retries = max_retries
        self._backoff_base = backoff_base
        self._timeout = timeout
        self.network_calls = 0

    def _cached(self, key: str, now: datetime) -> str | None:
        with self._session_factory() as session:
            row = session.scalar(select(ProviderCache).where(ProviderCache.cache_key == key))
            if row is not None and row.expires_at > now:
                return row.body
        return None

    def _store(self, key: str, url: str, status: int, body: str, ttl: timedelta) -> None:
        now = datetime.now(UTC)
        with self._session_factory() as session:
            row = session.scalar(select(ProviderCache).where(ProviderCache.cache_key == key))
            if row is None:
                row = ProviderCache(cache_key=key, source_id=self._source_id(), url=url)
                session.add(row)
            row.status_code = status
            row.body = body
            row.fetched_at = now
            row.expires_at = now + ttl
            session.commit()

    async def get_json(
        self, url: str, *, params: dict[str, Any] | None = None, ttl: timedelta
    ) -> Any:
        key = cache_key(self.source_key, url, params)
        cached = self._cached(key, datetime.now(UTC))
        if cached is not None:
            log.debug("provider_cache_hit", provider=self.source_key, url=url)
            return json.loads(cached)

        self._breaker.check()
        last_error: str = ""
        async with httpx.AsyncClient(
            headers=self._headers, transport=self._transport, timeout=self._timeout
        ) as client:
            for attempt in range(self._max_retries + 1):
                await self._limiter.acquire()
                self.network_calls += 1
                try:
                    resp = await client.get(url, params=params)
                except httpx.HTTPError as exc:
                    last_error = f"{type(exc).__name__}"
                else:
                    if resp.status_code == 200:
                        self._breaker.record_success()
                        self._store(key, url, 200, resp.text, ttl)
                        log.info("provider_fetch", provider=self.source_key, url=url)
                        try:
                            return resp.json()
                        except ValueError as exc:
                            raise ProviderError("risposta non in formato JSON") from exc
                    if resp.status_code not in RETRY_STATUSES:
                        self._breaker.record_failure()
                        raise ProviderError(f"HTTP {resp.status_code} da {self.source_key}")
                    last_error = f"HTTP {resp.status_code}"
                if attempt < self._max_retries:
                    delay = self._backoff_base * (2**attempt) * (1 + random.random() * 0.25)  # noqa: S311
                    log.warning(
                        "provider_retry",
                        provider=self.source_key,
                        attempt=attempt + 1,
                        error=last_error,
                    )
                    await asyncio.sleep(delay)
        self._breaker.record_failure()
        raise ProviderError(f"{self.source_key}: richiesta fallita dopo i tentativi ({last_error})")

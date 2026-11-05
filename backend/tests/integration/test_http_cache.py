"""CachedHttpClient: cache hits avoid network calls; retries and errors handled."""

from __future__ import annotations

from datetime import timedelta

import httpx
import pytest
from sqlalchemy import delete
from sqlalchemy.orm import sessionmaker

from football_ai.models import DataSource, ProviderCache
from football_ai.providers.base import ProviderError, RateLimitPolicy
from football_ai.providers.http import CachedHttpClient
from football_ai.providers.rate_limit import CircuitBreaker, TokenBucket

pytestmark = pytest.mark.db


@pytest.fixture
def factory(db_engine):
    f = sessionmaker(bind=db_engine)
    with f() as s:
        src = DataSource(key="http-test", name="HTTP test")
        s.add(src)
        s.commit()
        sid = src.id
    yield f, sid
    with f() as s:
        s.execute(delete(ProviderCache).where(ProviderCache.source_id == sid))
        s.execute(delete(DataSource).where(DataSource.id == sid))
        s.commit()


def _client(factory, handler, **kw) -> CachedHttpClient:
    f, sid = factory
    return CachedHttpClient(
        source_key="http-test",
        source_id_resolver=lambda: sid,
        session_factory=f,
        limiter=TokenBucket(RateLimitPolicy(1000, 1)),
        transport=httpx.MockTransport(handler),
        backoff_base=0.0,
        **kw,
    )


async def test_second_call_served_from_cache(factory) -> None:
    calls = []

    def handler(req: httpx.Request) -> httpx.Response:
        calls.append(req.url)
        return httpx.Response(200, json={"ok": 1})

    c = _client(factory, handler)
    assert await c.get_json("https://x.test/a", ttl=timedelta(hours=1)) == {"ok": 1}
    assert await c.get_json("https://x.test/a", ttl=timedelta(hours=1)) == {"ok": 1}
    assert len(calls) == 1 and c.network_calls == 1


async def test_expired_cache_refetches(factory) -> None:
    n = {"i": 0}

    def handler(req: httpx.Request) -> httpx.Response:
        n["i"] += 1
        return httpx.Response(200, json={"v": n["i"]})

    c = _client(factory, handler)
    await c.get_json("https://x.test/b", ttl=timedelta(seconds=-1))
    assert await c.get_json("https://x.test/b", ttl=timedelta(hours=1)) == {"v": 2}


async def test_retries_on_503_then_succeeds(factory) -> None:
    seq = [503, 429, 200]

    def handler(req: httpx.Request) -> httpx.Response:
        code = seq.pop(0)
        return httpx.Response(code, json={"ok": True} if code == 200 else {})

    c = _client(factory, handler)
    assert await c.get_json("https://x.test/c", ttl=timedelta(hours=1)) == {"ok": True}
    assert c.network_calls == 3


async def test_non_retryable_error_raises(factory) -> None:
    c = _client(factory, lambda req: httpx.Response(404))
    with pytest.raises(ProviderError, match="404"):
        await c.get_json("https://x.test/d", ttl=timedelta(hours=1))
    assert c.network_calls == 1


async def test_gives_up_after_retries_and_opens_breaker(factory) -> None:
    def handler(req: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("down")

    c = _client(factory, handler, max_retries=1, breaker=CircuitBreaker(threshold=1))
    with pytest.raises(ProviderError, match="dopo i tentativi"):
        await c.get_json("https://x.test/e", ttl=timedelta(hours=1))
    assert c.network_calls == 2
    from football_ai.providers.rate_limit import CircuitOpenError

    with pytest.raises(CircuitOpenError):
        await c.get_json("https://x.test/e", ttl=timedelta(hours=1))

import pytest

from football_ai.providers.base import RateLimitPolicy
from football_ai.providers.rate_limit import CircuitBreaker, CircuitOpenError, TokenBucket


class FakeClock:
    def __init__(self) -> None:
        self.t = 0.0
        self.slept: list[float] = []

    def __call__(self) -> float:
        return self.t

    async def sleep(self, d: float) -> None:
        self.slept.append(d)
        self.t += d


async def test_bucket_allows_burst_then_waits() -> None:
    clk = FakeClock()
    b = TokenBucket(RateLimitPolicy(requests=2, per_seconds=10), clock=clk, sleep=clk.sleep)
    assert await b.acquire() == 0
    assert await b.acquire() == 0
    waited = await b.acquire()
    assert waited == pytest.approx(5.0)  # 1 token every 5 s


async def test_bucket_refills_over_time() -> None:
    clk = FakeClock()
    b = TokenBucket(RateLimitPolicy(requests=1, per_seconds=1), clock=clk, sleep=clk.sleep)
    await b.acquire()
    clk.t += 1
    assert await b.acquire() == 0


def test_invalid_policy() -> None:
    with pytest.raises(ValueError):
        TokenBucket(RateLimitPolicy(requests=0, per_seconds=1))


def test_circuit_breaker_opens_and_recovers() -> None:
    clk = FakeClock()
    cb = CircuitBreaker(threshold=2, cooldown=30, clock=clk)
    cb.record_failure()
    cb.check()
    cb.record_failure()
    with pytest.raises(CircuitOpenError):
        cb.check()
    clk.t += 31
    cb.check()  # half-open trial allowed
    cb.record_failure()
    with pytest.raises(CircuitOpenError):
        cb.check()
    clk.t += 31
    cb.check()
    cb.record_success()
    cb.record_failure()
    cb.check()

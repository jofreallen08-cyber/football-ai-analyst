"""Async token-bucket rate limiter and a simple circuit breaker."""

from __future__ import annotations

import asyncio
import time
from collections.abc import Awaitable, Callable

from football_ai.providers.base import RateLimitPolicy


class TokenBucket:
    """Allows ``policy.requests`` calls per ``policy.per_seconds``, smoothing bursts."""

    def __init__(
        self,
        policy: RateLimitPolicy,
        clock: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
    ) -> None:
        if policy.requests <= 0 or policy.per_seconds <= 0:
            raise ValueError("politica di rate limit non valida")
        self.capacity = float(policy.requests)
        self.refill_per_second = policy.requests / policy.per_seconds
        self._tokens = self.capacity
        self._clock = clock
        self._sleep = sleep
        self._updated = clock()
        self._lock = asyncio.Lock()

    def _refill(self) -> None:
        now = self._clock()
        elapsed = max(0.0, now - self._updated)
        self._tokens = min(self.capacity, self._tokens + elapsed * self.refill_per_second)
        self._updated = now

    async def acquire(self) -> float:
        """Wait for a token. Returns the number of seconds spent waiting."""
        waited = 0.0
        async with self._lock:
            self._refill()
            while self._tokens < 1:
                delay = (1 - self._tokens) / self.refill_per_second
                await self._sleep(delay)
                waited += delay
                self._refill()
            self._tokens -= 1
        return waited


class CircuitOpenError(Exception):
    """Raised while the circuit is open after repeated failures."""


class CircuitBreaker:
    """Opens after ``threshold`` consecutive failures for ``cooldown`` seconds."""

    def __init__(
        self,
        threshold: int = 5,
        cooldown: float = 60.0,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self.threshold = threshold
        self.cooldown = cooldown
        self._clock = clock
        self._failures = 0
        self._opened_at: float | None = None

    def check(self) -> None:
        if self._opened_at is None:
            return
        if self._clock() - self._opened_at >= self.cooldown:
            self._opened_at = None  # half-open: allow one trial request
            self._failures = self.threshold - 1
            return
        raise CircuitOpenError("servizio temporaneamente sospeso dopo errori ripetuti")

    def record_success(self) -> None:
        self._failures = 0
        self._opened_at = None

    def record_failure(self) -> None:
        self._failures += 1
        if self._failures >= self.threshold:
            self._opened_at = self._clock()

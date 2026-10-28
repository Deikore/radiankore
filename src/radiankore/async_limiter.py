"""Optional process-local admission shared by asynchronous DIAN clients."""

import asyncio
from collections.abc import AsyncIterator, Mapping
from contextlib import asynccontextmanager
from types import MappingProxyType

from radiankore._async_runtime import LoopBound
from radiankore.async_models import count, positive


class AsyncDianLimiter:
    """Limit HTTP concurrency, global start rate and per-service concurrency.

    Service keys are the exact SOAP endpoint or a download origin ending in '/'.
    Share one limiter only within a single process and event loop. Rate is
    disabled by default; no default represents a documented DIAN allowance.
    """

    def __init__(
        self,
        *,
        concurrency: int = 5,
        requests_per_second: float | None = None,
        service_limits: Mapping[str, int] | None = None,
    ) -> None:
        count(concurrency, "concurrency")
        if requests_per_second is not None:
            positive(requests_per_second, "requests_per_second")
        limits = dict(service_limits or {})
        for key, value in limits.items():
            if not isinstance(key, str) or not key:
                raise ValueError("Service keys must be nonempty strings.")
            count(value, "service limit")
        self._affinity = LoopBound()
        self._slots = asyncio.Semaphore(concurrency)
        self._services = {key: asyncio.Semaphore(n) for key, n in limits.items()}
        self._interval = 0.0 if requests_per_second is None else 1 / requests_per_second
        self._next_start = 0.0
        self._cooldowns: dict[str, float] = {}
        self._rate_lock = asyncio.Lock()
        self._concurrency = concurrency
        self._requests_per_second = requests_per_second
        self._service_limits = MappingProxyType(limits)

    @property
    def concurrency(self) -> int:
        """Return the fixed global concurrency limit."""
        return self._concurrency

    @property
    def requests_per_second(self) -> float | None:
        """Return the configured start rate; None disables rate limiting."""
        return self._requests_per_second

    @property
    def service_limits(self) -> Mapping[str, int]:
        """Return an immutable view of the configured service concurrency limits."""
        return self._service_limits

    @asynccontextmanager
    async def _slot(self, service: str) -> AsyncIterator[None]:
        self._affinity.bind()
        # Every user acquires scopes in this order, avoiding lock inversion.
        async with self._slots:
            semaphore = self._services.get(service)
            if semaphore is None:
                yield
            else:
                async with semaphore:
                    yield

    async def _wait(self, service: str) -> None:
        loop = self._affinity.bind()
        while True:
            async with self._rate_lock:
                now = loop.time()
                eligible = max(self._next_start, self._cooldowns.get(service, 0.0))
                delay = eligible - now
                if delay <= 0:
                    self._next_start = now + self._interval
                    self._cooldowns.pop(service, None)
                    return
            await asyncio.sleep(delay)

    def _defer(self, service: str, seconds: float) -> None:
        loop = self._affinity.bind()
        self._cooldowns[service] = max(
            self._cooldowns.get(service, 0.0), loop.time() + seconds
        )

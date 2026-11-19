"""Optional process-local admission shared by asynchronous DIAN clients."""

import asyncio
from collections.abc import AsyncIterator, Mapping
from contextlib import asynccontextmanager
from types import MappingProxyType
from typing import Protocol, runtime_checkable

from radiankore._async_runtime import LoopBound
from radiankore.async_models import count, positive


@runtime_checkable
class AsyncDianRequestAdmission(Protocol):
    """Borrowed application admission for each physical HTTP request.

    Implementations may coordinate processes, but must not retry or send HTTP.
    The caller owns this resource and remains responsible for its shutdown.
    """

    async def wait_for_start(self, *, service: str) -> None:
        """Wait until one HTTP request may start for the service."""
        ...

    async def record_retry_after(self, *, service: str, seconds: float) -> None:
        """Share a provider cooldown without replacing its original error."""
        ...


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
        admission: AsyncDianRequestAdmission | None = None,
    ) -> None:
        count(concurrency, "concurrency")
        if admission is not None and not isinstance(
            admission, AsyncDianRequestAdmission
        ):
            raise TypeError("admission must implement AsyncDianRequestAdmission.")
        self._admission = admission
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
        # Waiters on one service must not reserve global capacity for other services.
        # Every user acquires service then global, avoiding lock inversion.
        semaphore = self._services.get(service)
        if semaphore is None:
            async with self._slots:
                yield
        else:
            async with semaphore, self._slots:
                yield

    async def _wait(self, service: str) -> None:
        if self._admission is not None and self._interval == 0:
            await self._wait_shared(service, self._admission)
            return
        loop = self._affinity.bind()
        while True:
            async with self._rate_lock:
                now = loop.time()
                eligible = max(self._next_start, self._cooldowns.get(service, 0.0))
                delay = eligible - now
                if delay <= 0:
                    if self._admission is not None:
                        # Serialize local permits across an external wait. Otherwise
                        # several granted local slots could start together afterward.
                        await self._admission.wait_for_start(service=service)
                        now = loop.time()
                        if self._cooldowns.get(service, 0.0) > now:
                            continue
                    self._next_start = now + self._interval
                    self._cooldowns.pop(service, None)
                    return
            await asyncio.sleep(delay)

    async def _wait_shared(
        self, service: str, admission: AsyncDianRequestAdmission
    ) -> None:
        # With no local start-rate budget, callbacks may wait concurrently. A
        # shared coordinator can perform I/O or authority revalidation; holding
        # the local rate lock around it would serialize unrelated operations.
        loop = self._affinity.bind()
        while True:
            delay = self._cooldowns.get(service, 0.0) - loop.time()
            if delay > 0:
                await asyncio.sleep(delay)
                continue
            await admission.wait_for_start(service=service)
            # These synchronous reads/updates share the owner loop with _defer.
            # A cooldown received during the callback invalidates its unused permit.
            if self._cooldowns.get(service, 0.0) > loop.time():
                continue
            self._cooldowns.pop(service, None)
            return

    def _defer(self, service: str, seconds: float) -> None:
        loop = self._affinity.bind()
        self._cooldowns[service] = max(
            self._cooldowns.get(service, 0.0), loop.time() + seconds
        )

    async def _record_retry_after(self, service: str, seconds: float) -> None:
        self._defer(service, seconds)
        if self._admission is not None:
            await self._admission.record_retry_after(service=service, seconds=seconds)

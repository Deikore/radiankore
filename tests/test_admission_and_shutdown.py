"""Pool close failures and independent service admission must not strand work."""

import asyncio

import httpx
import pytest

from radiankore import AsyncDianLimiter
from radiankore._soap import transport


@pytest.mark.parametrize("both_fail", [False, True])
def test_sync_close_attempts_every_pool_and_preserves_first_failure(
    monkeypatch: pytest.MonkeyPatch, both_fail: bool
) -> None:
    clients: list[httpx.Client] = []

    def create(timeout: float) -> httpx.Client:
        client = httpx.Client(
            transport=httpx.MockTransport(
                lambda request: httpx.Response(200, content=b"ok")
            )
        )
        clients.append(client)
        return client

    monkeypatch.setattr(transport, "create_http_client", create)
    pool = transport.SoapTransport(timeout=1, reuse_connections=True)
    pool.post("https://synthetic.invalid/", b"", action="action")
    pool.get("https://synthetic.invalid/archive")
    originals = [client.close for client in clients]
    calls: list[str] = []
    first_error = OSError("synthetic SOAP close failure")

    def first() -> None:
        calls.append("soap")
        raise first_error

    def second() -> None:
        calls.append("download")
        if both_fail:
            raise RuntimeError("synthetic download close failure")
        originals[1]()

    monkeypatch.setattr(clients[0], "close", first)
    monkeypatch.setattr(clients[1], "close", second)
    try:
        with pytest.raises(OSError) as error:
            pool.close()
        assert error.value is first_error
        assert calls == ["soap", "download"]
        pool.close()
        assert calls == ["soap", "download"]
        with pytest.raises(RuntimeError, match="closed"):
            pool.get("https://synthetic.invalid/archive")
    finally:
        for close in originals:
            close()


def test_service_waiters_leave_global_capacity_available() -> None:
    async def exercise() -> None:
        limiter = AsyncDianLimiter(concurrency=2, service_limits={"A": 1})
        started, waiting, admitted, release = (asyncio.Event() for _ in range(4))

        async def first_service() -> None:
            async with limiter._slot("A"):
                started.set()
                await release.wait()

        async def queued_service() -> None:
            waiting.set()
            async with limiter._slot("A"):
                pass

        async def other_service() -> None:
            async with limiter._slot("B"):
                admitted.set()

        first = asyncio.create_task(first_service())
        await started.wait()
        second = asyncio.create_task(queued_service())
        await waiting.wait()
        other = asyncio.create_task(other_service())
        try:
            async with asyncio.timeout(5):
                await admitted.wait()
            assert not first.done() and not second.done()
        finally:
            release.set()
            await asyncio.gather(first, second, other)

    asyncio.run(exercise())


@pytest.mark.parametrize("scope", ["service", "global"])
def test_cancelled_admission_releases_every_acquired_scope(scope: str) -> None:
    async def exercise() -> None:
        limiter = AsyncDianLimiter(concurrency=1, service_limits={"A": 1})
        waiting = asyncio.Event()

        async def queued() -> None:
            waiting.set()
            async with limiter._slot("A"):
                raise AssertionError("Admission should still be blocked")

        async with limiter._slot("A" if scope == "service" else "B"):
            task = asyncio.create_task(queued())
            await waiting.wait()
            task.cancel()
            with pytest.raises(asyncio.CancelledError):
                await task
        async with asyncio.timeout(5):
            for service in ("A", "B", "A"):
                async with limiter._slot(service):
                    pass
        with pytest.raises(ValueError):
            async with limiter._slot("A"):
                raise ValueError("synthetic body failure")
        async with asyncio.timeout(5), limiter._slot("A"):
            pass

    asyncio.run(exercise())

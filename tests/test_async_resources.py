"""Resource bounds and cancellation must track physical work, not just waiters."""

import asyncio
import threading
import time
from collections.abc import AsyncIterator
from itertools import pairwise
from pathlib import Path

import httpx
import pytest

from radiankore import (
    AsyncDianClient,
    AsyncDianLimiter,
    DianTimeouts,
    DianTransportError,
    DigitalCertificate,
)
from radiankore._async_runtime import BoundedProcessor
from radiankore._soap import async_transport
from tests.async_support import install_http
from tests.test_signing import _verify


def test_concurrency_and_cookie_isolation(
    digital_certificate: DigitalCertificate,
    monkeypatch: pytest.MonkeyPatch,
    soap_response: bytes,
) -> None:
    active = maximum = calls = 0

    async def handle(request: httpx.Request) -> httpx.Response:
        nonlocal active, maximum, calls
        assert "cookie" not in request.headers
        _verify(request.content, digital_certificate)
        active += 1
        calls += 1
        maximum = max(active, maximum)
        try:
            await asyncio.sleep(0.01)
            return httpx.Response(
                200, content=soap_response, headers={"Set-Cookie": "secret=test"}
            )
        finally:
            active -= 1

    clients = install_http(monkeypatch, handle)

    async def exercise() -> None:
        async with AsyncDianClient(digital_certificate, concurrency=3) as client:
            await asyncio.gather(
                *(client.get_invoice_events(str(i)) for i in range(20))
            )
        assert 1 < maximum <= 3 and active == 0 and calls == 20
        assert len(clients) == 1 and clients[0].is_closed

    asyncio.run(exercise())


def test_shared_limiter_service_cap_and_rate(
    encrypted_pfx_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    soap_response: bytes,
) -> None:
    starts: list[float] = []
    active = maximum = 0

    async def handle(request: httpx.Request) -> httpx.Response:
        nonlocal active, maximum
        starts.append(time.monotonic())
        active += 1
        maximum = max(maximum, active)
        await asyncio.sleep(0.025)
        active -= 1
        return httpx.Response(200, content=soap_response)

    install_http(monkeypatch, handle)

    async def exercise() -> None:
        limiter = AsyncDianLimiter(
            concurrency=2,
            requests_per_second=50,
            service_limits={"https://vpfe.dian.gov.co/WcfDianCustomerServices.svc": 1},
        )
        # Independent loads, not shared native key objects.
        async with (
            await AsyncDianClient.from_file(
                encrypted_pfx_path, password="test-password", limiter=limiter
            ) as first,
            await AsyncDianClient.from_file(
                encrypted_pfx_path, password="test-password", limiter=limiter
            ) as second,
        ):
            await asyncio.gather(
                first.get_invoice_events("1"),
                second.get_invoice_events("2"),
                first.get_invoice_events("3"),
                second.get_invoice_events("4"),
            )
        assert maximum == 1
        assert all(b - a >= 0.018 for a, b in pairwise(starts))

    asyncio.run(exercise())


def test_retry_after_pauses_next_call_but_does_not_retry(
    digital_certificate: DigitalCertificate,
    monkeypatch: pytest.MonkeyPatch,
    soap_response: bytes,
) -> None:
    starts: list[float] = []

    async def handle(request: httpx.Request) -> httpx.Response:
        starts.append(time.monotonic())
        if len(starts) == 1:
            return httpx.Response(429, content=b"busy", headers={"Retry-After": "1"})
        return httpx.Response(200, content=soap_response)

    install_http(monkeypatch, handle)

    async def exercise() -> None:
        async with AsyncDianClient(digital_certificate) as client:
            with pytest.raises(DianTransportError) as error:
                await client.get_invoice_events("first")
            assert error.value.retry_after == 1
            await client.get_invoice_events("second")
        assert len(starts) == 2 and starts[1] - starts[0] >= 0.95

    asyncio.run(exercise())


def test_cancelled_processor_keeps_physical_slot() -> None:
    first_started = threading.Event()
    release = threading.Event()
    second_started = threading.Event()

    def first() -> None:
        first_started.set()
        assert release.wait(5)

    def second() -> None:
        second_started.set()

    async def exercise() -> None:
        processor = BoundedProcessor(1)
        first_task = asyncio.create_task(processor.run(first))
        try:
            while not first_started.is_set():
                await asyncio.sleep(0.001)
            first_task.cancel()
            with pytest.raises(asyncio.CancelledError):
                await first_task
            second_task = asyncio.create_task(processor.run(second))
            await asyncio.sleep(0.02)
            assert not second_started.is_set()
        finally:
            release.set()
        await second_task
        await processor.aclose()
        assert second_started.is_set()

    asyncio.run(exercise())


def test_cancelled_initializer_is_owned_until_close(
    digital_certificate: DigitalCertificate,
    monkeypatch: pytest.MonkeyPatch,
    soap_response: bytes,
) -> None:
    started = threading.Event()
    release = threading.Event()
    original = async_transport.create_async_http_client

    async def handle(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=soap_response)

    clients = install_http(monkeypatch, handle)

    def slow(timeouts: DianTimeouts, concurrency: int) -> httpx.AsyncClient:
        started.set()
        assert release.wait(5)
        return original(timeouts, concurrency)

    monkeypatch.setattr(async_transport, "create_async_http_client", slow)

    async def exercise() -> None:
        client = AsyncDianClient(digital_certificate)
        operation = asyncio.create_task(client.get_invoice_events("test"))
        try:
            while not started.is_set():
                await asyncio.sleep(0.001)
            operation.cancel()
            with pytest.raises(asyncio.CancelledError):
                await operation
            closing = asyncio.create_task(client.aclose())
            await asyncio.sleep(0.01)
            assert not closing.done()
            closing.cancel()
            with pytest.raises(asyncio.CancelledError):
                await closing
        finally:
            release.set()
        await client.aclose()
        assert len(clients) == 1 and clients[0].is_closed

    asyncio.run(exercise())


def test_close_drains_inflight_network(
    digital_certificate: DigitalCertificate,
    monkeypatch: pytest.MonkeyPatch,
    soap_response: bytes,
) -> None:
    async def exercise() -> None:
        started, release = asyncio.Event(), asyncio.Event()

        async def handle(request: httpx.Request) -> httpx.Response:
            started.set()
            await release.wait()
            return httpx.Response(200, content=soap_response)

        clients = install_http(monkeypatch, handle)
        client = AsyncDianClient(digital_certificate)
        operation = asyncio.create_task(client.get_invoice_events("test"))
        await started.wait()
        closing = asyncio.create_task(client.aclose())
        await asyncio.sleep(0)
        assert not closing.done()
        with pytest.raises(RuntimeError, match="closed"):
            await client.get_invoice_events("late")
        release.set()
        await operation
        await closing
        assert clients[0].is_closed

    asyncio.run(exercise())


def test_total_timeout_covers_admission(
    digital_certificate: DigitalCertificate,
    monkeypatch: pytest.MonkeyPatch,
    soap_response: bytes,
) -> None:
    async def exercise() -> None:
        limiter = AsyncDianLimiter(concurrency=1)
        async with (
            AsyncDianClient(
                digital_certificate, limiter=limiter, timeouts=DianTimeouts(total=0.03)
            ) as client,
            limiter._slot(client.environment.endpoint),
        ):
            with pytest.raises(DianTransportError) as error:
                await client.get_invoice_events("blocked")
            assert isinstance(error.value.__cause__, TimeoutError)

    asyncio.run(exercise())


def test_loop_and_process_affinity(
    digital_certificate: DigitalCertificate, monkeypatch: pytest.MonkeyPatch
) -> None:
    client = AsyncDianClient(digital_certificate)
    asyncio.run(client.aclose())
    with pytest.raises(RuntimeError, match="event loops"):
        asyncio.run(client.aclose())

    import os

    other = AsyncDianClient(digital_certificate)
    pid = os.getpid()
    with monkeypatch.context() as patch:
        patch.setattr(os, "getpid", lambda: pid + 1)
        with pytest.raises(RuntimeError, match="processes"):
            asyncio.run(other.aclose())
    asyncio.run(other.aclose())


def test_cancelled_body_closes_stream_and_pool_remains_usable(
    digital_certificate: DigitalCertificate,
    monkeypatch: pytest.MonkeyPatch,
    soap_response: bytes,
) -> None:
    async def exercise() -> None:
        reading = asyncio.Event()
        closed = asyncio.Event()
        calls = 0

        class SlowBody(httpx.AsyncByteStream):
            async def __aiter__(self) -> AsyncIterator[bytes]:
                yield b"partial"
                reading.set()
                await asyncio.sleep(10)

            async def aclose(self) -> None:
                closed.set()

        async def handle(request: httpx.Request) -> httpx.Response:
            nonlocal calls
            calls += 1
            if calls == 1:
                return httpx.Response(200, stream=SlowBody())
            return httpx.Response(200, content=soap_response)

        install_http(monkeypatch, handle)
        async with AsyncDianClient(digital_certificate) as client:
            pending = asyncio.create_task(client.get_invoice_events("interrupted"))
            await reading.wait()
            pending.cancel()
            with pytest.raises(asyncio.CancelledError):
                await pending
            assert closed.is_set()
            assert (await client.get_invoice_events("again")).events
        assert calls == 2

    asyncio.run(exercise())


def test_cancelled_processing_close_still_drains_physical_job() -> None:
    started = threading.Event()
    release = threading.Event()

    def work() -> None:
        started.set()
        assert release.wait(5)

    async def exercise() -> None:
        processor = BoundedProcessor(1)
        operation = asyncio.create_task(processor.run(work))
        try:
            while not started.is_set():
                await asyncio.sleep(0.001)
            operation.cancel()
            with pytest.raises(asyncio.CancelledError):
                await operation
            closing = asyncio.create_task(processor.aclose())
            await asyncio.sleep(0)
            closing.cancel()
            with pytest.raises(asyncio.CancelledError):
                await closing
        finally:
            release.set()
        await processor.aclose()
        assert processor._executor is None and not processor._pending

    asyncio.run(exercise())


def test_retry_after_pauses_admission_before_error_body_finishes(
    digital_certificate: DigitalCertificate,
    soap_response: bytes,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def exercise() -> None:
        reading = asyncio.Event()
        release = asyncio.Event()
        calls = 0

        class SlowError(httpx.AsyncByteStream):
            async def __aiter__(self) -> AsyncIterator[bytes]:
                reading.set()
                await release.wait()
                yield b"synthetic HTTP error"

        async def handle(request: httpx.Request) -> httpx.Response:
            nonlocal calls
            calls += 1
            if calls == 1:
                return httpx.Response(
                    429, headers={"Retry-After": "1"}, stream=SlowError()
                )
            return httpx.Response(200, content=soap_response)

        install_http(monkeypatch, handle)
        async with AsyncDianClient(digital_certificate, concurrency=2) as client:
            async with asyncio.timeout(5):
                first = asyncio.create_task(client.get_invoice_events("first"))
                await reading.wait()
                second = asyncio.create_task(client.get_invoice_events("second"))
                try:
                    await asyncio.sleep(0.05)
                    assert calls == 1  # The error body is still blocked.
                finally:
                    release.set()
                with pytest.raises(DianTransportError) as error:
                    await first
                assert error.value.status_code == 429
                assert error.value.retry_after == 1
                assert (await second).events
                assert calls == 2  # One attempt per call; no automatic retry.

    asyncio.run(exercise())

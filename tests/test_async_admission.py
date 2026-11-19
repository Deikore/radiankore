"""Borrowed shared HTTP admission preserves local limits and provider outcomes."""

import asyncio
import time
from itertools import pairwise

import httpx
import pytest

from radiankore import (
    AsyncDianClient,
    AsyncDianLimiter,
    AsyncDianRequestAdmission,
    DianTransportError,
    DigitalCertificate,
    Environment,
)
from tests.async_support import RecordingAdmission, install_http


def test_admission_contract_and_invalid_provider() -> None:
    assert isinstance(RecordingAdmission(), AsyncDianRequestAdmission)
    with pytest.raises(TypeError, match="AsyncDianRequestAdmission"):
        AsyncDianLimiter(admission=object())  # type: ignore[arg-type]


@pytest.mark.parametrize("cancel", [False, True])
def test_external_wait_blocks_http_and_does_not_own_resource(
    digital_certificate: DigitalCertificate,
    monkeypatch: pytest.MonkeyPatch,
    soap_response: bytes,
    cancel: bool,
) -> None:
    async def exercise() -> None:
        waiting = asyncio.Event()
        release = asyncio.Event()
        calls = 0

        class Admission(RecordingAdmission):
            async def wait_for_start(self, *, service: str) -> None:
                await super().wait_for_start(service=service)
                waiting.set()
                await release.wait()

        async def handle(request: httpx.Request) -> httpx.Response:
            nonlocal calls
            calls += 1
            return httpx.Response(200, content=soap_response)

        clients = install_http(monkeypatch, handle)
        admission = Admission()
        async with AsyncDianClient(
            digital_certificate, limiter=AsyncDianLimiter(admission=admission)
        ) as client:
            task = asyncio.create_task(client.get_invoice_events("synthetic"))
            await waiting.wait()
            assert calls == 0
            if cancel:
                task.cancel()
                with pytest.raises(asyncio.CancelledError):
                    await task
            else:
                release.set()
                assert (await task).events
        assert calls == (0 if cancel else 1)
        assert admission.starts == [Environment.PRODUCTION.endpoint]
        assert not admission.closed
        assert all(client.is_closed for client in clients)

    asyncio.run(exercise())


def test_failed_admission_is_fail_closed(
    digital_certificate: DigitalCertificate, monkeypatch: pytest.MonkeyPatch
) -> None:
    class Admission(RecordingAdmission):
        async def wait_for_start(self, *, service: str) -> None:
            raise RuntimeError("shared control unavailable")

    async def handle(request: httpx.Request) -> httpx.Response:
        pytest.fail("No HTTP request may start without shared admission")

    install_http(monkeypatch, handle)

    async def exercise() -> None:
        async with AsyncDianClient(
            digital_certificate, limiter=AsyncDianLimiter(admission=Admission())
        ) as client:
            with pytest.raises(RuntimeError, match="shared control unavailable"):
                await client.get_invoice_events("synthetic")

    asyncio.run(exercise())


@pytest.mark.parametrize("feedback_fails", [False, True])
def test_retry_after_feedback_keeps_original_http_error(
    digital_certificate: DigitalCertificate,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
    feedback_fails: bool,
) -> None:
    class Admission(RecordingAdmission):
        async def record_retry_after(self, *, service: str, seconds: float) -> None:
            await super().record_retry_after(service=service, seconds=seconds)
            if feedback_fails:
                raise RuntimeError("sensitive callback context must not be logged")

    calls = 0

    async def handle(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(503, content=b"busy", headers={"Retry-After": "2"})

    install_http(monkeypatch, handle)
    admission = Admission()

    async def exercise() -> None:
        async with AsyncDianClient(
            digital_certificate, limiter=AsyncDianLimiter(admission=admission)
        ) as client:
            with pytest.raises(DianTransportError) as raised:
                await client.get_invoice_events("synthetic")
            assert raised.value.status_code == 503
            assert raised.value.retry_after == 2
            assert isinstance(raised.value.__cause__, httpx.HTTPStatusError)
        assert calls == 1
        assert admission.cooldowns == [(Environment.PRODUCTION.endpoint, 2)]
        assert not admission.closed

    asyncio.run(exercise())
    assert bool(caplog.records) == feedback_fails
    assert "sensitive" not in caplog.text
    assert "https://" not in caplog.text


def test_external_wait_preserves_local_rate_and_concurrent_cooldown() -> None:
    async def exercise() -> None:
        starts: list[float] = []
        count = 0

        class Admission(RecordingAdmission):
            async def wait_for_start(self, *, service: str) -> None:
                nonlocal count
                count += 1
                await asyncio.sleep(0.001)
                if count == 1:
                    limiter._defer(service, 0.005)

        limiter = AsyncDianLimiter(requests_per_second=100, admission=Admission())

        async def operation() -> None:
            await limiter._wait("https://synthetic.invalid/")
            starts.append(time.monotonic())

        await asyncio.gather(*(operation() for _ in range(3)))
        assert count == 4  # Changed cooldown invalidates the unused first permit.
        assert all(b - a >= 0.009 for a, b in pairwise(starts))

    asyncio.run(exercise())


def test_one_client_can_admit_five_requests_concurrently_without_local_rps(
    digital_certificate: DigitalCertificate,
    monkeypatch: pytest.MonkeyPatch,
    soap_response: bytes,
) -> None:
    async def exercise() -> None:
        all_waiting = asyncio.Event()
        all_sending = asyncio.Event()
        active_callbacks = callback_peak = active_http = http_peak = 0

        class Admission(RecordingAdmission):
            async def wait_for_start(self, *, service: str) -> None:
                nonlocal active_callbacks, callback_peak
                active_callbacks += 1
                callback_peak = max(callback_peak, active_callbacks)
                if active_callbacks == 5:
                    all_waiting.set()
                try:
                    await all_waiting.wait()
                finally:
                    active_callbacks -= 1

        async def handle(request: httpx.Request) -> httpx.Response:
            nonlocal active_http, http_peak
            active_http += 1
            http_peak = max(http_peak, active_http)
            if active_http == 5:
                all_sending.set()
            try:
                await all_sending.wait()
                return httpx.Response(200, content=soap_response)
            finally:
                active_http -= 1

        install_http(monkeypatch, handle)
        async with AsyncDianClient(
            digital_certificate,
            concurrency=5,
            limiter=AsyncDianLimiter(concurrency=5, admission=Admission()),
        ) as client:
            async with asyncio.timeout(2):
                results = await asyncio.gather(
                    *(client.get_invoice_events(str(index)) for index in range(5))
                )
            assert len(results) == 5 and all(result.events for result in results)
        assert callback_peak == http_peak == 5
        assert active_callbacks == active_http == 0

    asyncio.run(exercise())


def test_shared_wait_without_local_rps_rechecks_cooldown_received_during_callback() -> (
    None
):
    async def exercise() -> None:
        waits = 0
        first_callback = asyncio.Event()
        release = asyncio.Event()
        admitted = asyncio.Event()

        class Admission(RecordingAdmission):
            async def wait_for_start(self, *, service: str) -> None:
                nonlocal waits
                waits += 1
                if waits == 1:
                    first_callback.set()
                    await release.wait()

        limiter = AsyncDianLimiter(admission=Admission())

        async def request() -> None:
            await limiter._wait("https://synthetic.invalid/")
            admitted.set()

        task = asyncio.create_task(request())
        await first_callback.wait()
        limiter._defer("https://synthetic.invalid/", 0.03)
        release.set()
        await asyncio.sleep(0.005)
        assert not admitted.is_set()
        await task
        assert admitted.is_set() and waits == 2

    asyncio.run(exercise())

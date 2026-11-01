"""Concurrent event preparation/submission, native work and stream ownership."""

import asyncio
import threading
from collections.abc import AsyncIterator, Callable
from datetime import UTC, datetime

import httpx
import pytest
from lxml import etree

from radiankore import (
    AsyncDianClient,
    DianTimeouts,
    DianTransportError,
    DigitalCertificate,
    Environment,
)
from radiankore._soap import operations
from radiankore._soap.events import (
    build_radian_application_response,
    pack_event,
    sign_application_response,
)
from radiankore.catalogs import EventType
from radiankore.models.events import InvoiceResponseEvent, RadianEvent, RadianSoftware
from tests.async_support import install_http
from tests.test_send_radian_event import result_xml
from tests.test_signing import _verify


async def thread_started(event: threading.Event) -> None:
    """Observe native work without blocking the event loop or using extra workers."""
    async with asyncio.timeout(5):
        while not event.is_set():
            await asyncio.sleep(0.001)


@pytest.mark.parametrize("stage", ["build", "zip"])
def test_event_build_and_zip_do_not_block_other_soap_signatures(
    digital_certificate: DigitalCertificate,
    radian_event_factory: Callable[[str], RadianEvent],
    radian_software: RadianSoftware,
    verify_event_signature: Callable[[bytes, DigitalCertificate], None],
    soap_response: bytes,
    monkeypatch: pytest.MonkeyPatch,
    stage: str,
) -> None:
    started, release = threading.Event(), threading.Event()
    original_build = build_radian_application_response
    original_pack = pack_event
    loop_thread = threading.get_ident()

    def pause() -> None:
        assert threading.get_ident() != loop_thread
        started.set()
        assert release.wait(5)

    def build(
        event: RadianEvent, *, software: RadianSoftware, environment: Environment
    ) -> etree._Element:
        pause()
        return original_build(event, software=software, environment=environment)

    def pack(xml_bytes: bytes, *, xml_name: str) -> bytes:
        pause()
        return original_pack(xml_bytes, xml_name=xml_name)

    if stage == "build":
        monkeypatch.setattr(operations, "build_radian_application_response", build)
    else:
        monkeypatch.setattr(operations, "pack_event", pack)

    async def handle(request: httpx.Request) -> httpx.Response:
        _verify(request.content, digital_certificate)
        return httpx.Response(200, content=soap_response)

    clients = install_http(monkeypatch, handle)

    async def exercise() -> None:
        async with AsyncDianClient(digital_certificate, processing_workers=2) as client:
            preparation = asyncio.create_task(
                client.prepare_radian_event(
                    event=radian_event_factory("441"), software=radian_software
                )
            )
            try:
                await thread_started(started)
                async with asyncio.timeout(5):
                    assert (await client.get_invoice_events("synthetic")).events
                assert not preparation.done()
            finally:
                release.set()
            prepared = await preparation
            verify_event_signature(prepared.xml_bytes, digital_certificate)
        assert len(clients) == 1 and clients[0].is_closed

    asyncio.run(exercise())


def test_native_ubl_signatures_remain_serialized(
    digital_certificate: DigitalCertificate,
    radian_event_factory: Callable[[str], RadianEvent],
    radian_software: RadianSoftware,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    started, release, second_built = (
        threading.Event(),
        threading.Event(),
        threading.Event(),
    )
    original_build = build_radian_application_response
    original_sign = sign_application_response
    calls = active = maximum = 0
    state_lock = threading.Lock()

    def build(
        event: RadianEvent, *, software: RadianSoftware, environment: Environment
    ) -> etree._Element:
        nonlocal calls
        root = original_build(event, software=software, environment=environment)
        with state_lock:
            calls += 1
            if calls == 2:
                second_built.set()
        return root

    def sign(
        root: etree._Element,
        certificate: DigitalCertificate,
        *,
        signer_role: str,
        signing_time: datetime | None = None,
    ) -> None:
        nonlocal active, maximum
        with state_lock:
            active += 1
            maximum = max(maximum, active)
        try:
            started.set()
            assert release.wait(5)
            original_sign(
                root,
                certificate=certificate,
                signer_role=signer_role,
                signing_time=signing_time,
            )
        finally:
            with state_lock:
                active -= 1

    monkeypatch.setattr(operations, "build_radian_application_response", build)
    monkeypatch.setattr(operations, "sign_application_response", sign)

    async def exercise() -> None:
        async with AsyncDianClient(digital_certificate, processing_workers=2) as client:
            first = asyncio.create_task(
                client.prepare_radian_event(
                    event=radian_event_factory("441"), software=radian_software
                )
            )
            try:
                await thread_started(started)
                second = asyncio.create_task(
                    client.prepare_radian_event(
                        event=radian_event_factory("441"), software=radian_software
                    )
                )
                await thread_started(second_built)
            finally:
                release.set()
            await asyncio.gather(first, second)
        assert maximum == 1 and active == 0

    asyncio.run(exercise())


@pytest.mark.parametrize("interrupt", ["cancel", "timeout"])
def test_interrupted_event_preparation_is_drained_before_close(
    digital_certificate: DigitalCertificate,
    radian_event_factory: Callable[[str], RadianEvent],
    radian_software: RadianSoftware,
    monkeypatch: pytest.MonkeyPatch,
    interrupt: str,
) -> None:
    started, release = threading.Event(), threading.Event()
    original = pack_event

    def pack(xml_bytes: bytes, *, xml_name: str) -> bytes:
        started.set()
        assert release.wait(5)
        return original(xml_bytes, xml_name=xml_name)

    monkeypatch.setattr(operations, "pack_event", pack)

    async def exercise() -> None:
        client = AsyncDianClient(
            digital_certificate,
            processing_workers=1,
            timeouts=DianTimeouts(total=0.5 if interrupt == "timeout" else None),
        )
        preparation = asyncio.create_task(
            client.prepare_radian_event(
                event=radian_event_factory("441"), software=radian_software
            )
        )
        try:
            await thread_started(started)
            if interrupt == "cancel":
                preparation.cancel()
                with pytest.raises(asyncio.CancelledError):
                    await preparation
            else:
                with pytest.raises(DianTransportError):
                    await preparation
            assert len(client._processor._pending) == 1
            closing = asyncio.create_task(client.aclose())
            await asyncio.sleep(0)
            assert not closing.done()
        finally:
            release.set()
            await client.aclose()
        await closing
        assert not client._processor._pending
        assert not client._transport._clients  # Preparation never created an HTTP pool.

    asyncio.run(exercise())


def test_invoice_signing_date_is_read_after_waiting_for_the_certificate(
    digital_certificate: DigitalCertificate,
    invoice_event_factory: Callable[[EventType], InvoiceResponseEvent],
    radian_software: RadianSoftware,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    built = threading.Event()
    original = build_radian_application_response
    clock_reads: list[datetime] = []

    class Clock:
        @staticmethod
        def now(tz: object) -> datetime:
            stamp = datetime(2026, 10, 23, 5, 0, tzinfo=UTC)
            clock_reads.append(stamp)
            return stamp

    def build(
        event: RadianEvent, *, software: RadianSoftware, environment: Environment
    ) -> etree._Element:
        root = original(event, software=software, environment=environment)
        built.set()
        return root

    monkeypatch.setattr(operations, "datetime", Clock)
    monkeypatch.setattr(operations, "build_radian_application_response", build)

    async def exercise() -> None:
        async with AsyncDianClient(digital_certificate) as client:
            # Simulate another native signature crossing Colombian midnight.
            with client._crypto_lock:
                preparation = asyncio.create_task(
                    client.prepare_radian_event(
                        event=invoice_event_factory(EventType.EXPRESS_ACCEPTANCE),
                        software=radian_software,
                    )
                )
                await thread_started(built)
                assert not clock_reads
            with pytest.raises(ValueError, match="signing date"):
                await preparation
            assert len(clock_reads) == 1

    asyncio.run(exercise())


def test_cancelled_event_response_closes_stream_without_automatic_resubmission(
    digital_certificate: DigitalCertificate,
    radian_event_factory: Callable[[str], RadianEvent],
    radian_software: RadianSoftware,
    wrap_soap: Callable[[etree._Element], bytes],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def exercise() -> None:
        reading, closed = asyncio.Event(), asyncio.Event()
        requests: list[bytes] = []

        class SlowBody(httpx.AsyncByteStream):
            async def __aiter__(self) -> AsyncIterator[bytes]:
                reading.set()
                await asyncio.Event().wait()
                yield b"unreachable"

            async def aclose(self) -> None:
                closed.set()

        async def handle(request: httpx.Request) -> httpx.Response:
            requests.append(request.content)
            _verify(request.content, digital_certificate)
            if len(requests) == 1:
                return httpx.Response(200, stream=SlowBody())
            return httpx.Response(200, content=result_xml(wrap_soap))

        clients = install_http(monkeypatch, handle)
        async with AsyncDianClient(digital_certificate) as client:
            prepared = await client.prepare_radian_event(
                event=radian_event_factory("441"), software=radian_software
            )
            sending = asyncio.create_task(client.send_radian_event(prepared))
            async with asyncio.timeout(5):
                await reading.wait()
            sending.cancel()
            with pytest.raises(asyncio.CancelledError):
                await sending
            assert closed.is_set() and len(requests) == 1
            result = await client.send_radian_event(prepared)  # Explicit second call.
            assert result is not None and result.status_code == "99"
        assert len(requests) == 2 and clients[0].is_closed

    asyncio.run(exercise())


def test_concurrent_event_posts_are_bounded_and_close_drains_them(
    digital_certificate: DigitalCertificate,
    radian_event_factory: Callable[[str], RadianEvent],
    radian_software: RadianSoftware,
    wrap_soap: Callable[[etree._Element], bytes],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def forbidden(*args: object, **kwargs: object) -> None:
        raise AssertionError("Async event sends must never use synchronous HTTP")

    monkeypatch.setattr(httpx.Client, "send", forbidden)

    async def exercise() -> None:
        reached, release = asyncio.Event(), asyncio.Event()
        active = maximum = calls = 0

        async def handle(request: httpx.Request) -> httpx.Response:
            nonlocal active, maximum, calls
            _verify(request.content, digital_certificate)
            active += 1
            calls += 1
            maximum = max(maximum, active)
            if active == 2:
                reached.set()
            try:
                await release.wait()
                return httpx.Response(200, content=result_xml(wrap_soap))
            finally:
                active -= 1

        clients = install_http(monkeypatch, handle)
        client = AsyncDianClient(digital_certificate, concurrency=2)
        prepared = await client.prepare_radian_event(
            event=radian_event_factory("441"), software=radian_software
        )
        sends = [
            asyncio.create_task(client.send_radian_event(prepared)) for _ in range(6)
        ]
        try:
            async with asyncio.timeout(5):
                await reached.wait()
            closing = asyncio.create_task(client.aclose())
            await asyncio.sleep(0)
            assert not closing.done()
            with pytest.raises(RuntimeError, match="closed"):
                await client.send_radian_event(prepared)
        finally:
            release.set()
            results = await asyncio.gather(*sends)
            await client.aclose()
        await closing
        assert all(
            result is not None and result.status_code == "99" for result in results
        )
        assert calls == 6 and maximum == 2 and active == 0
        assert len(clients) == 1 and clients[0].is_closed

    asyncio.run(exercise())

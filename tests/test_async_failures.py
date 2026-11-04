"""Async failure paths retain causes, close resources and never retry HTTP."""

import asyncio
from base64 import b64encode
from collections.abc import Callable
from unittest.mock import AsyncMock

import httpx
import pytest
from lxml import etree

from radiankore import AsyncDianClient, DianTransportError, DigitalCertificate
from radiankore.catalogs import IdentificationType
from tests.async_support import install_http


def test_failed_pool_initialization_notifies_all_waiters_and_can_be_repeated(
    digital_certificate: DigitalCertificate,
    monkeypatch: pytest.MonkeyPatch,
    soap_response: bytes,
) -> None:
    async def handle(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=soap_response)

    clients = install_http(monkeypatch, handle)

    async def exercise() -> None:
        async with AsyncDianClient(digital_certificate) as client:
            error = RuntimeError("synthetic TLS initialization failure")
            # Keep both waiters attached to the same owned initializer.
            entered, release = asyncio.Event(), asyncio.Event()
            original = client._processor.run

            async def fail(function: Callable[..., object], *args: object) -> object:
                entered.set()
                await release.wait()
                raise error

            with monkeypatch.context() as patch:
                patch.setattr(client._processor, "run", fail)
                first = asyncio.create_task(client._transport.ready("soap"))
                await entered.wait()
                second = asyncio.create_task(client._transport.ready("soap"))
                await asyncio.sleep(0)
                release.set()
                results = await asyncio.gather(first, second, return_exceptions=True)
                assert all(result is error for result in results)
                assert not client._transport._clients
            assert client._processor.run == original
            assert (await client.get_invoice_events("synthetic")).events
        assert len(clients) == 1 and clients[0].is_closed

    asyncio.run(exercise())


def test_close_attempts_every_pool_and_drains_processor_after_a_close_failure(
    digital_certificate: DigitalCertificate,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def exercise() -> None:
        client = AsyncDianClient(digital_certificate)
        pools = await asyncio.gather(
            *(client._transport.ready(k) for k in ("soap", "download"))
        )
        originals = [p.aclose for p in pools]
        error = OSError("synthetic close failure")
        closed = AsyncMock(side_effect=error)
        monkeypatch.setattr(pools[0], "aclose", closed)
        try:
            with pytest.raises(OSError) as caught:
                await client.aclose()
            assert caught.value is error
            assert pools[1].is_closed
            assert not client._transport._clients
            assert client._processor._closed and not client._processor._pending
            assert client._processor._executor is None
        finally:
            for close in originals:
                await close()

    asyncio.run(exercise())


@pytest.mark.parametrize("status", [404, 500])
def test_acquirer_alone_maps_404_to_none(
    digital_certificate: DigitalCertificate,
    monkeypatch: pytest.MonkeyPatch,
    status: int,
) -> None:
    async def handle(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status, content=b"not SOAP")

    clients = install_http(monkeypatch, handle)

    async def exercise() -> None:
        async with AsyncDianClient(digital_certificate) as client:
            query = client.get_acquirer(
                identification_type=IdentificationType.NIT,
                identification_number="900000001",
            )
            if status == 404:
                assert await query is None
            else:
                with pytest.raises(DianTransportError) as caught:
                    await query
                assert caught.value.status_code == status
            with pytest.raises(DianTransportError):
                await client.get_invoice_events("synthetic")
        assert clients[0].is_closed

    asyncio.run(exercise())


@pytest.mark.parametrize("failure", ["http", "network"])
def test_download_errors_preserve_causes_and_close_pools(
    digital_certificate: DigitalCertificate,
    monkeypatch: pytest.MonkeyPatch,
    wrap_soap: Callable[[etree._Element], bytes],
    failure: str,
) -> None:
    from radiankore._soap.namespaces import EXCHANGE_EMAIL_RESPONSE, WCF

    root = etree.Element(f"{{{WCF}}}GetExchangeEmailsResponse")
    result = etree.SubElement(root, f"{{{WCF}}}GetExchangeEmailsResult")
    etree.SubElement(
        result, f"{{{EXCHANGE_EMAIL_RESPONSE}}}CsvBase64Bytes"
    ).text = b64encode(b"https://download.invalid/archive.zip").decode()
    calls: list[str] = []

    async def handle(request: httpx.Request) -> httpx.Response:
        calls.append(request.method)
        if request.method == "POST":
            return httpx.Response(200, content=wrap_soap(root))
        if failure == "network":
            raise httpx.ReadError("synthetic download failure", request=request)
        return httpx.Response(503, headers={"Retry-After": "0"})

    clients = install_http(monkeypatch, handle)

    async def exercise() -> None:
        async with AsyncDianClient(digital_certificate) as client:
            with pytest.raises(DianTransportError) as caught:
                await client.get_exchange_emails()
            expected = (
                httpx.ReadError if failure == "network" else httpx.HTTPStatusError
            )
            assert isinstance(caught.value.__cause__, expected)
        assert calls == ["POST", "GET"]
        assert len(clients) == 2 and all(c.is_closed for c in clients)

    asyncio.run(exercise())


@pytest.mark.parametrize("payload", [b"", b"<empty/>"])
def test_exchange_email_response_without_download_never_opens_download_pool(
    digital_certificate: DigitalCertificate,
    monkeypatch: pytest.MonkeyPatch,
    wrap_soap: Callable[[etree._Element], bytes],
    payload: bytes,
) -> None:
    from radiankore._soap.namespaces import WCF

    root = etree.Element(f"{{{WCF}}}GetExchangeEmailsResponse")
    if payload:
        etree.SubElement(root, f"{{{WCF}}}GetExchangeEmailsResult")

    async def handle(request: httpx.Request) -> httpx.Response:
        assert request.method == "POST"
        return httpx.Response(200, content=wrap_soap(root))

    clients = install_http(monkeypatch, handle)

    async def exercise() -> None:
        async with AsyncDianClient(digital_certificate) as client:
            result = await client.get_exchange_emails()
            assert (
                result is None
                if not payload
                else result is not None and result.download_url is None
            )
        assert len(clients) == 1 and clients[0].is_closed

    asyncio.run(exercise())


def test_inner_timeout_is_not_reclassified_as_total_deadline(
    digital_certificate: DigitalCertificate,
) -> None:
    async def exercise() -> None:
        async with AsyncDianClient(digital_certificate) as client:
            error = TimeoutError("native processing timeout")
            with pytest.raises(TimeoutError) as caught:
                async with client._operation():
                    raise error
            assert caught.value is error
            assert client._active == 0 and client._idle.is_set()

    asyncio.run(exercise())


@pytest.mark.parametrize("expires_again", [False, True])
def test_aged_soap_envelope_is_refreshed_before_transmission(
    digital_certificate: DigitalCertificate,
    monkeypatch: pytest.MonkeyPatch,
    soap_response: bytes,
    expires_again: bool,
) -> None:
    calls: list[bytes] = []

    async def handle(request: httpx.Request) -> httpx.Response:
        calls.append(request.content)
        assert request.content == b"fresh envelope"
        return httpx.Response(200, content=soap_response)

    install_http(monkeypatch, handle)

    async def exercise() -> None:
        async with AsyncDianClient(digital_certificate) as client:
            await client._transport.ready("soap")
            stamps = iter([0.0, 240.0, 240.0, 480.0 if expires_again else 241.0])

            # Scope the fake monotonic clock to _request, not asyncio's scheduler.
            class Clock:
                @staticmethod
                def time() -> float:
                    return next(stamps)

            signed = AsyncMock(side_effect=[b"stale envelope", b"fresh envelope"])
            with monkeypatch.context() as patch:
                patch.setattr(client._processor, "run", signed)
                patch.setattr(client._affinity, "bind", lambda: Clock())
                if expires_again:
                    with pytest.raises(DianTransportError, match="fresh SOAP"):
                        await client._request(
                            "GetStatusEvent", (("trackId", "synthetic"),)
                        )
                else:
                    assert await client._request("GetStatusEvent", ()) == soap_response
            assert signed.await_count == 2
        assert len(calls) == (0 if expires_again else 1)

    asyncio.run(exercise())


def test_cookie_policy_never_returns_a_preexisting_cookie() -> None:
    from urllib.request import Request

    from radiankore._soap.async_transport import _RejectCookies

    jar = httpx.Cookies({"session": "synthetic"}).jar
    jar.set_policy(_RejectCookies())
    request = Request("https://synthetic.invalid/")
    jar.add_cookie_header(request)
    assert not request.has_header("Cookie")

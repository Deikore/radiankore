"""Active response bounds, factory propagation and bounded decompression."""

import asyncio
import gzip
from base64 import b64encode
from collections.abc import AsyncIterator, Callable, Iterator
from dataclasses import FrozenInstanceError
from io import BytesIO
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

import httpx
import pytest
from lxml import etree

from radiankore import (
    AsyncDianClient,
    AsyncDianLimiter,
    DianResponseError,
    DianResponseLimits,
    DianTimeouts,
    DianTransportError,
    DigitalCertificate,
)
from radiankore._async_runtime import BoundedProcessor
from radiankore._soap import transport
from radiankore._soap.async_transport import AsyncSoapTransport
from radiankore._soap.exchange_emails_response import (
    extract_exchange_emails_csv,
    parse_exchange_emails_csv,
)
from radiankore._soap.namespaces import EXCHANGE_EMAIL_RESPONSE, WCF
from radiankore.client import DianClient
from tests.async_support import install_http


def test_defaults_partial_configuration_and_immutability() -> None:
    defaults = DianResponseLimits()
    assert (defaults.soap_bytes, defaults.download_bytes, defaults.csv_bytes) == (
        16 * 1024 * 1024,
        64 * 1024 * 1024,
        128 * 1024 * 1024,
    )
    partial = DianResponseLimits(csv_bytes=None)
    assert partial.soap_bytes == defaults.soap_bytes
    assert partial.download_bytes == defaults.download_bytes
    assert partial.csv_bytes is None
    with pytest.raises(FrozenInstanceError):
        defaults.soap_bytes = None  # type: ignore[misc]
    assert not hasattr(defaults, "__dict__")


@pytest.mark.parametrize("name", ["soap_bytes", "download_bytes", "csv_bytes"])
@pytest.mark.parametrize("value", [True, False, 1.0, "1", 0, -1])
def test_invalid_limits(name: str, value: object) -> None:
    with pytest.raises(ValueError if type(value) is int else TypeError):
        DianResponseLimits(**{name: value})  # type: ignore[arg-type]


@pytest.mark.parametrize("factory", ["path", "pfx", "certificate"])
@pytest.mark.parametrize("limited", [False, True])
def test_sync_factories_propagate_limits(
    factory: str,
    limited: bool,
    encrypted_pfx_path: Path,
    digital_certificate: DigitalCertificate,
    mock_http: tuple[list[httpx.Client], list[httpx.Request]],
) -> None:
    limits = DianResponseLimits(soap_bytes=1) if limited else None
    if factory == "path":
        client = DianClient(
            encrypted_pfx_path, password="test-password", response_limits=limits
        )
    elif factory == "pfx":
        client = DianClient.from_pfx(
            encrypted_pfx_path.read_bytes(),
            password="test-password",
            response_limits=limits,
        )
    else:
        client = DianClient.from_certificate(
            digital_certificate, response_limits=limits
        )
    with client:
        assert client._response_limits == (limits or DianResponseLimits())
        if limited:
            with pytest.raises(DianTransportError, match=r"SOAP.*1-byte"):
                client.get_invoice_events("synthetic")
        else:
            assert client.get_invoice_events("synthetic").events
    assert all(c.is_closed for c in mock_http[0])


@pytest.mark.parametrize("factory", ["constructor", "file", "pfx", "certificate"])
@pytest.mark.parametrize("limited", [False, True])
def test_async_factories_propagate_limits(
    factory: str,
    limited: bool,
    encrypted_pfx_path: Path,
    digital_certificate: DigitalCertificate,
    soap_response: bytes,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def handle(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=soap_response)

    clients = install_http(monkeypatch, handle)
    limits = DianResponseLimits(soap_bytes=1) if limited else None

    async def exercise() -> None:
        if factory == "constructor":
            client = AsyncDianClient(digital_certificate, response_limits=limits)
        elif factory == "certificate":
            client = AsyncDianClient.from_certificate(
                digital_certificate, response_limits=limits
            )
        elif factory == "file":
            client = await AsyncDianClient.from_file(
                encrypted_pfx_path, password="test-password", response_limits=limits
            )
        else:
            client = await AsyncDianClient.from_pfx(
                encrypted_pfx_path.read_bytes(),
                password="test-password",
                response_limits=limits,
            )
        async with client:
            assert client._response_limits == (limits or DianResponseLimits())
            if limited:
                with pytest.raises(DianTransportError, match=r"SOAP.*1-byte"):
                    await client.get_invoice_events("synthetic")
            else:
                assert (await client.get_invoice_events("synthetic")).events
        assert all(c.is_closed for c in clients)

    asyncio.run(exercise())


def test_invalid_client_configuration_precedes_certificate_io(
    digital_certificate: DigitalCertificate,
) -> None:
    with pytest.raises(TypeError, match="response_limits"):
        DianClient("missing-file.pfx", response_limits=1)  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="response_limits"):
        DianClient.from_pfx(b"invalid", response_limits=1)  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="response_limits"):
        DianClient.from_certificate(digital_certificate, response_limits=1)  # type: ignore[arg-type]

    async def exercise() -> None:
        with pytest.raises(TypeError, match="response_limits"):
            AsyncDianClient(digital_certificate, response_limits=1)  # type: ignore[arg-type]
        with pytest.raises(TypeError, match="response_limits"):
            AsyncDianClient.from_certificate(digital_certificate, response_limits=1)  # type: ignore[arg-type]
        with pytest.raises(TypeError, match="response_limits"):
            await AsyncDianClient.from_file("missing-file.pfx", response_limits=1)  # type: ignore[arg-type]
        with pytest.raises(TypeError, match="response_limits"):
            await AsyncDianClient.from_pfx(b"invalid", response_limits=1)  # type: ignore[arg-type]

    asyncio.run(exercise())


class Body(httpx.SyncByteStream, httpx.AsyncByteStream):
    """Expose read counts and closure without allocating a complete response."""

    def __init__(self, chunks: tuple[bytes, ...]) -> None:
        self.chunks = chunks
        self.reads = 0
        self.closed = False

    def __iter__(self) -> Iterator[bytes]:
        for chunk in self.chunks:
            self.reads += 1
            yield chunk

    async def __aiter__(self) -> AsyncIterator[bytes]:
        for chunk in self:
            yield chunk

    def close(self) -> None:
        self.closed = True

    async def aclose(self) -> None:
        self.close()


@pytest.mark.parametrize("asynchronous", [False, True])
@pytest.mark.parametrize("kind", ["SOAP", "download"])
@pytest.mark.parametrize("maximum", [15, 16, None])
@pytest.mark.parametrize("compressed", [False, True])
@pytest.mark.parametrize("length_header", [False, True])
def test_decoded_body_limits_ignore_content_length(
    asynchronous: bool,
    kind: str,
    maximum: int | None,
    compressed: bool,
    length_header: bool,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    payload = b"0123456789abcdef"
    encoded = gzip.compress(payload) if compressed else payload
    bodies: list[Body] = []

    def response() -> httpx.Response:
        body = Body((encoded[:4], encoded[4:]))
        bodies.append(body)
        # A misleading length must not bypass the bound or reject a valid body.
        headers = {"Content-Length": "1"} if length_header else {}
        if compressed:
            headers["Content-Encoding"] = "gzip"
        return httpx.Response(200, stream=body, headers=headers)

    limits = DianResponseLimits(soap_bytes=maximum, download_bytes=maximum)
    if asynchronous:

        async def handle(request: httpx.Request) -> httpx.Response:
            return response()

        clients = install_http(monkeypatch, handle)

        async def exercise() -> None:
            processor = BoundedProcessor(1)
            pool = AsyncSoapTransport(
                processor, DianTimeouts(), 1, AsyncDianLimiter(), limits
            )
            try:
                if kind == "SOAP":
                    call = pool.post("https://synthetic.invalid/", b"request", "action")
                else:
                    call = pool.get(
                        "https://synthetic.invalid/archive",
                        "https://synthetic.invalid/",
                    )
                if maximum == 15:
                    with pytest.raises(DianTransportError, match=f"{kind}.*limit"):
                        await call
                else:
                    assert await call == payload
            finally:
                await pool.aclose()
                await processor.aclose()
            assert all(c.is_closed for c in clients)

        asyncio.run(exercise())
    else:
        monkeypatch.setattr(
            transport,
            "create_http_client",
            lambda timeout: httpx.Client(
                transport=httpx.MockTransport(lambda request: response())
            ),
        )
        pool_sync = transport.SoapTransport(timeout=1, response_limits=limits)
        try:
            if maximum == 15:
                with pytest.raises(DianTransportError, match=f"{kind}.*limit"):
                    if kind == "SOAP":
                        pool_sync.post(
                            "https://synthetic.invalid/", b"request", action="action"
                        )
                    else:
                        pool_sync.get("https://synthetic.invalid/archive")
            else:
                actual = (
                    pool_sync.post(
                        "https://synthetic.invalid/", b"request", action="action"
                    )
                    if kind == "SOAP"
                    else pool_sync.get("https://synthetic.invalid/archive")
                )
                assert actual == payload
        finally:
            pool_sync.close()
    assert bodies and all(body.closed for body in bodies)


@pytest.mark.parametrize("asynchronous", [False, True])
def test_oversize_stops_reading_and_reused_pool_remains_usable(
    asynchronous: bool, monkeypatch: pytest.MonkeyPatch
) -> None:
    oversized = Body((b"x" * 32768,) * 20)
    calls = 0

    def response() -> httpx.Response:
        nonlocal calls
        calls += 1
        return (
            httpx.Response(200, stream=oversized)
            if calls == 1
            else httpx.Response(200, content=b"ok")
        )

    limits = DianResponseLimits(soap_bytes=10)
    if asynchronous:

        async def handle(request: httpx.Request) -> httpx.Response:
            return response()

        clients = install_http(monkeypatch, handle)

        async def exercise() -> None:
            processor = BoundedProcessor(1)
            pool = AsyncSoapTransport(
                processor, DianTimeouts(), 1, AsyncDianLimiter(), limits
            )
            try:
                with pytest.raises(DianTransportError):
                    await pool.post("https://synthetic.invalid", b"", "action")
                assert (
                    await pool.post("https://synthetic.invalid", b"", "action") == b"ok"
                )
            finally:
                await pool.aclose()
                await processor.aclose()
            assert len(clients) == 1 and clients[0].is_closed

        asyncio.run(exercise())
    else:
        monkeypatch.setattr(
            transport,
            "create_http_client",
            lambda timeout: httpx.Client(
                transport=httpx.MockTransport(lambda request: response())
            ),
        )
        pool_sync = transport.SoapTransport(
            timeout=1, reuse_connections=True, response_limits=limits
        )
        try:
            with pytest.raises(DianTransportError):
                pool_sync.post("https://synthetic.invalid", b"", action="action")
            assert (
                pool_sync.post("https://synthetic.invalid", b"", action="action")
                == b"ok"
            )
        finally:
            pool_sync.close()
    assert 0 < oversized.reads < 20 and oversized.closed
    assert calls == 2


def csv_zip(content: bytes) -> bytes:
    buffer = BytesIO()
    with ZipFile(buffer, "w", compression=ZIP_DEFLATED) as archive:
        archive.writestr("directory.csv", content)
    return buffer.getvalue()


@pytest.mark.parametrize("maximum", [7, 8, None])
def test_csv_limit_counts_expanded_bytes_before_utf8_decoding(
    maximum: int | None,
) -> None:
    content = "name\ná\n".encode()  # Eight bytes, seven Unicode characters.
    archive = csv_zip(content)
    limits = DianResponseLimits(csv_bytes=maximum)
    if maximum == 7:
        with pytest.raises(DianResponseError, match=r"CSV.*limit"):
            parse_exchange_emails_csv(archive, limits)
    else:
        assert parse_exchange_emails_csv(archive, limits) == ({"name": "á"},)


def test_declared_oversized_csv_is_rejected_before_decompression(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    archive = csv_zip(b"x" * 10000)

    def forbidden(*args: object, **kwargs: object) -> None:
        raise AssertionError("Oversized member should not be opened")

    monkeypatch.setattr(ZipFile, "open", forbidden)
    with pytest.raises(DianResponseError, match=r"CSV.*limit"):
        extract_exchange_emails_csv(archive, DianResponseLimits(csv_bytes=100))


def test_actual_csv_read_is_bounded_even_if_metadata_understates_size(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    archive = csv_zip(b"")
    member = BytesIO(b"larger than allowed")
    monkeypatch.setattr(ZipFile, "open", lambda *args, **kwargs: member)
    with pytest.raises(DianResponseError, match=r"CSV.*limit"):
        extract_exchange_emails_csv(archive, DianResponseLimits(csv_bytes=5))
    assert member.closed


@pytest.mark.parametrize("asynchronous", [False, True])
@pytest.mark.parametrize("boundary", ["download", "csv"])
def test_exchange_email_limits_reach_each_processing_stage(
    asynchronous: bool,
    boundary: str,
    digital_certificate: DigitalCertificate,
    wrap_soap: Callable[[etree._Element], bytes],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    response = etree.Element(f"{{{WCF}}}GetExchangeEmailsResponse")
    result = etree.SubElement(response, f"{{{WCF}}}GetExchangeEmailsResult")
    etree.SubElement(
        result, f"{{{EXCHANGE_EMAIL_RESPONSE}}}CsvBase64Bytes"
    ).text = b64encode(b"https://synthetic.invalid/archive").decode()
    metadata = wrap_soap(response)
    archive = csv_zip(b"name\nvalue\n")
    limits = (
        DianResponseLimits(download_bytes=1)
        if boundary == "download"
        else DianResponseLimits(csv_bytes=1)
    )
    expected = DianTransportError if boundary == "download" else DianResponseError

    def handle(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200, content=metadata if request.method == "POST" else archive
        )

    if asynchronous:

        async def async_handle(request: httpx.Request) -> httpx.Response:
            return handle(request)

        clients = install_http(monkeypatch, async_handle)

        async def exercise() -> None:
            async with AsyncDianClient(
                digital_certificate, response_limits=limits
            ) as client:
                with pytest.raises(expected):
                    await client.get_exchange_emails()
            assert len(clients) == 2 and all(c.is_closed for c in clients)

        asyncio.run(exercise())
    else:
        monkeypatch.setattr(
            transport,
            "create_http_client",
            lambda timeout: httpx.Client(transport=httpx.MockTransport(handle)),
        )
        with (
            DianClient.from_certificate(
                digital_certificate, response_limits=limits
            ) as client,
            pytest.raises(expected),
        ):
            client.get_exchange_emails()


def test_documented_limit_configuration_executes(
    digital_certificate: DigitalCertificate,
    soap_response: bytes,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from tests.documentation_support import namespace

    guide = Path(__file__).resolve().parents[1] / "docs/guides/response-limits.md"
    values = namespace(guide)
    configured = values["limits"]
    assert isinstance(configured, DianResponseLimits)
    assert configured.soap_bytes == 32 * 1024 * 1024
    assert configured.download_bytes == 64 * 1024 * 1024
    assert configured.csv_bytes is None
    assert values["unlimited"] == DianResponseLimits(
        soap_bytes=None, download_bytes=None, csv_bytes=None
    )

    def handle(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=soap_response)

    async def async_handle(request: httpx.Request) -> httpx.Response:
        return handle(request)

    monkeypatch.setattr(
        transport,
        "create_http_client",
        lambda timeout: httpx.Client(transport=httpx.MockTransport(handle)),
    )
    install_http(monkeypatch, async_handle)
    assert values["query_with_limits"](digital_certificate, "synthetic").events

    async def exercise() -> None:
        assert (
            await values["query_with_limits_async"](digital_certificate, "synthetic")
        ).events

    asyncio.run(exercise())

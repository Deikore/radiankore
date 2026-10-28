"""Public async queries preserve sync contracts without contacting DIAN."""

import asyncio
from base64 import b64encode
from collections.abc import Callable
from io import BytesIO
from pathlib import Path
from zipfile import ZipFile

import httpx
import pytest
from lxml import etree

from radiankore import (
    AsyncDianClient,
    DianResponseError,
    DianSoapFaultError,
    DianTimeouts,
    DianTransportError,
    DigitalCertificate,
    DigitalCertificateError,
    Environment,
)
from radiankore._soap.namespaces import EXCHANGE_EMAIL_RESPONSE, WCF
from radiankore.catalogs import IdentificationType
from tests.async_support import install_http
from tests.test_signing import _verify


def test_eight_queries_and_isolated_download(
    digital_certificate: DigitalCertificate,
    monkeypatch: pytest.MonkeyPatch,
    soap_response: bytes,
    acquirer_response: bytes,
    document_info_response: bytes,
    reference_notes_response: bytes,
    xml_document_response: bytes,
    document_status_response: bytes,
    wrap_soap: Callable[[etree._Element], bytes],
) -> None:
    buffer = BytesIO()
    with ZipFile(buffer, "w") as archive:
        archive.writestr("directory.csv", "email\nsynthetic@example.invalid\n")
    exchange = etree.Element(f"{{{WCF}}}GetExchangeEmailsResponse")
    result = etree.SubElement(exchange, f"{{{WCF}}}GetExchangeEmailsResult")
    url = "https://download.invalid/file.zip?signature=synthetic"
    etree.SubElement(
        result, f"{{{EXCHANGE_EMAIL_RESPONSE}}}CsvBase64Bytes"
    ).text = b64encode(url.encode()).decode()
    numbering = etree.Element(f"{{{WCF}}}GetNumberingRangeResponse")
    responses = {
        "GetStatusEvent": soap_response,
        "GetAcquirer": acquirer_response,
        "GetDocumentInfo": document_info_response,
        "GetReferenceNotes": reference_notes_response,
        "GetXmlByDocumentKey": xml_document_response,
        "GetStatus": document_status_response,
        "GetExchangeEmails": wrap_soap(exchange),
        "GetNumberingRange": wrap_soap(numbering),
    }
    requests: list[httpx.Request] = []

    async def handle(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        assert "cookie" not in request.headers
        if request.method == "GET":
            assert str(request.url) == url
            assert b"BinarySecurityToken" not in request.content
            return httpx.Response(200, content=buffer.getvalue())
        _verify(request.content, digital_certificate)
        operation = request.headers["content-type"].split("/")[-1].rstrip('"')
        return httpx.Response(
            200, content=responses[operation], headers={"Set-Cookie": "secret=test"}
        )

    clients = install_http(monkeypatch, handle)

    async def exercise() -> None:
        async with AsyncDianClient.from_certificate(digital_certificate) as client:
            assert client.environment is Environment.PRODUCTION
            assert client.certificate is digital_certificate
            events = await client.get_invoice_events("  CUFE  ")
            assert len(events.events) == 9
            assert (
                await client.get_acquirer(
                    identification_type=IdentificationType.NIT,
                    identification_number="000123",
                )
                is not None
            )
            assert await client.get_document_info("uuid") is not None
            assert await client.get_reference_notes("track") is not None
            assert await client.get_xml_by_document_key("key") is not None
            assert await client.get_status("status") is not None
            assert (
                await client.get_numbering_range(
                    account_code="0001", account_code_t="0002", software_code="test"
                )
                is None
            )
            emails = await client.get_exchange_emails()
            assert emails and emails.csv == ({"email": "synthetic@example.invalid"},)
            assert len(clients) == 2
            assert all(not list(c.cookies.jar) for c in clients)
        assert len(requests) == 9 and all(c.is_closed for c in clients)
        await client.aclose()
        with pytest.raises(RuntimeError, match="closed"):
            await client.get_invoice_events("after close")

    asyncio.run(exercise())


@pytest.mark.parametrize("status", [200, 400, 500])
def test_soap_fault_precedence(
    digital_certificate: DigitalCertificate,
    monkeypatch: pytest.MonkeyPatch,
    soap_fault: bytes,
    status: int,
) -> None:
    calls = 0

    async def handle(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(status, content=soap_fault)

    clients = install_http(monkeypatch, handle)

    async def exercise() -> None:
        async with AsyncDianClient(digital_certificate) as client:
            with pytest.raises(DianSoapFaultError):
                await client.get_invoice_events("test")
        assert calls == 1 and clients[0].is_closed

    asyncio.run(exercise())


@pytest.mark.parametrize("status", [301, 404, 429, 500, 503])
def test_http_errors_never_retry_or_redirect(
    digital_certificate: DigitalCertificate,
    monkeypatch: pytest.MonkeyPatch,
    status: int,
) -> None:
    calls = 0

    async def handle(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(
            status,
            content=b"<html>synthetic</html>",
            headers={"Retry-After": "0", "Location": "https://redirect.invalid/"},
        )

    install_http(monkeypatch, handle)

    async def exercise() -> None:
        async with AsyncDianClient(digital_certificate) as client:
            with pytest.raises(DianTransportError) as error:
                await client.get_invoice_events("test")
            assert error.value.status_code == status
            assert error.value.retry_after == 0
            assert isinstance(error.value.__cause__, httpx.HTTPStatusError)
        assert calls == 1

    asyncio.run(exercise())


def test_only_acquirer_maps_404(
    digital_certificate: DigitalCertificate, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def handle(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, content=b"absent")

    install_http(monkeypatch, handle)

    async def exercise() -> None:
        async with AsyncDianClient(digital_certificate) as client:
            assert (
                await client.get_acquirer(
                    identification_type=IdentificationType.NIT,
                    identification_number="001",
                )
                is None
            )
            with pytest.raises(DianTransportError):
                await client.get_status("missing")

    asyncio.run(exercise())


@pytest.mark.parametrize("kind", ["network", "xml", "dtd", "slow"])
def test_failure_types_and_total_timeout(
    digital_certificate: DigitalCertificate,
    monkeypatch: pytest.MonkeyPatch,
    kind: str,
) -> None:
    calls = 0

    async def handle(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        if kind == "network":
            raise httpx.ReadTimeout("synthetic", request=request)
        if kind == "slow":
            await asyncio.sleep(1)
        data = (
            b'<!DOCTYPE test [<!ENTITY x "test">]><test/>' if kind == "dtd" else b"bad"
        )
        return httpx.Response(200, content=data)

    clients = install_http(monkeypatch, handle)

    async def exercise() -> None:
        async with AsyncDianClient(
            digital_certificate,
            timeouts=DianTimeouts(total=0.2 if kind == "slow" else 60),
        ) as client:
            if kind == "slow":
                await client._transport.ready("soap")
                monkeypatch.setattr(client, "_signed", lambda *args: b"synthetic")
            expected = (
                DianTransportError if kind in {"network", "slow"} else DianResponseError
            )
            with pytest.raises(expected) as error:
                await client.get_invoice_events("test")
            if kind == "slow":
                assert isinstance(error.value.__cause__, TimeoutError)
        assert calls == 1 and clients[0].is_closed

    asyncio.run(exercise())


def test_async_factories(
    encrypted_pfx_path: Path,
    digital_certificate: DigitalCertificate,
) -> None:
    data = encrypted_pfx_path.read_bytes()

    async def exercise() -> None:
        async with await AsyncDianClient.from_file(
            encrypted_pfx_path, password="test-password"
        ) as client:
            assert client.certificate.certificate == digital_certificate.certificate
        async with await AsyncDianClient.from_pfx(data, password="test-password"):
            pass
        with pytest.raises(DigitalCertificateError):
            await AsyncDianClient.from_pfx(data, password="wrong")
        with pytest.raises(ValueError):
            await AsyncDianClient.from_file("does-not-exist", concurrency=0)

    asyncio.run(exercise())


@pytest.mark.parametrize("bad", [True, 0, -1, float("nan"), float("inf")])
def test_timeout_validation(bad: float) -> None:
    with pytest.raises((TypeError, ValueError)):
        DianTimeouts(read=bad)


def test_invalid_query_arguments_do_not_initialize_http(
    digital_certificate: DigitalCertificate, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def forbidden(request: httpx.Request) -> httpx.Response:
        raise AssertionError("Invalid arguments must not reach HTTP")

    clients = install_http(monkeypatch, forbidden)

    async def exercise() -> None:
        async with AsyncDianClient(digital_certificate) as client:
            with pytest.raises(ValueError):
                await client.get_invoice_events("  ")
            with pytest.raises(ValueError):
                await client.get_numbering_range(
                    account_code="1x", account_code_t="002", software_code="test"
                )
            with pytest.raises(TypeError):
                await client.get_acquirer(
                    identification_type="31",  # type: ignore[arg-type]
                    identification_number="001",
                )
        assert not clients

    asyncio.run(exercise())


def test_documented_async_examples_execute(
    encrypted_pfx_path: Path,
    digital_certificate: DigitalCertificate,
    monkeypatch: pytest.MonkeyPatch,
    soap_response: bytes,
) -> None:
    from typing import Any

    from tests.test_documentation_examples import python_blocks

    guide = Path(__file__).resolve().parents[1] / "docs/guides/async.md"
    if not guide.is_file():
        pytest.skip("Documentation is excluded from distributions.")
    namespace: dict[str, Any] = {}
    for block in python_blocks(guide):
        exec(compile(block, str(guide), "exec"), namespace)

    async def handle(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=soap_response)

    install_http(monkeypatch, handle)
    data = encrypted_pfx_path.read_bytes()

    async def exercise() -> None:
        response = await namespace["consultar"](data, "test-password", "test")
        assert len(response.events) == 9
        async with AsyncDianClient(digital_certificate) as client:
            rows = [
                row async for row in namespace["resultados"](client, ["1", "1", "2"])
            ]
            assert {index for index, value in rows} == {0, 1, 2}
            assert all(value.events for index, value in rows)

    asyncio.run(exercise())

"""Synthetic exchange-email SOAP and immediate archive-download regressions."""

from base64 import b64encode
from collections.abc import Callable, Iterator
from dataclasses import FrozenInstanceError
from io import BytesIO
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZIP_STORED, ZipFile

import httpx
import pytest
import xmlsec
from cryptography.hazmat.primitives.serialization import Encoding
from lxml import etree

from radiankore import (
    DianClient,
    DianResponseError,
    DianSoapFaultError,
    DianTransportError,
    Environment,
)
from radiankore._soap import transport
from radiankore._soap.exchange_emails_response import (
    extract_exchange_emails_csv,
    parse_exchange_emails_csv,
    parse_exchange_emails_response,
)
from radiankore._soap.namespaces import (
    DS,
    EXCHANGE_EMAIL_RESPONSE,
    SOAP,
    WCF,
    WSA,
    XSI,
)
from radiankore.models.responses import ExchangeEmailsResult

URL = "https://downloads.example.invalid/directory.zip?sig=abc%2F123%2B456&expires=10"


@pytest.fixture
def exchange_response(
    wrap_soap: Callable[[etree._Element], bytes],
) -> Callable[[dict[str, str | None]], bytes]:
    def build(fields: dict[str, str | None]) -> bytes:
        response = etree.Element(f"{{{WCF}}}GetExchangeEmailsResponse")
        result = etree.SubElement(response, f"{{{WCF}}}GetExchangeEmailsResult")
        for name, value in fields.items():
            node = etree.SubElement(result, f"{{{EXCHANGE_EMAIL_RESPONSE}}}{name}")
            if value is None:
                node.set(f"{{{XSI}}}nil", "true")
            else:
                node.text = value
        return wrap_soap(response)

    return build


@pytest.mark.parametrize(
    "value, expected", [("true", True), ("1", True), ("false", False), ("0", False)]
)
def test_metadata_and_url(
    exchange_response: Callable[[dict[str, str | None]], bytes],
    value: str,
    expected: bool,
) -> None:
    encoded = b64encode(URL.encode()).decode()
    result = parse_exchange_emails_response(
        exchange_response(
            {
                "Success": f" {value} ",
                "StatusCode": " BUSINESS-CODE ",
                "Message": " Synthetic result ",
                "CsvBase64Bytes": f"\n{encoded[:16]}\t{encoded[16:]}\n",
            }
        )
    )
    assert result == ExchangeEmailsResult(
        success=expected,
        status_code="BUSINESS-CODE",
        message="Synthetic result",
        download_url=URL,
    )
    assert result.csv is None
    assert URL not in repr(result)


@pytest.mark.parametrize(
    "fields",
    [
        {},
        {"CsvBase64Bytes": None},
        {"CsvBase64Bytes": ""},
        {"CsvBase64Bytes": " \n\t"},
        {"CsvBase64Bytes": b64encode(b" \n ").decode()},
    ],
)
def test_missing_url(
    exchange_response: Callable[[dict[str, str | None]], bytes],
    fields: dict[str, str | None],
) -> None:
    assert (
        parse_exchange_emails_response(exchange_response(fields))
        == ExchangeEmailsResult()
    )


@pytest.mark.parametrize("value", [None, "", "TRUE", "False", "2", "yes"])
def test_invalid_success(
    exchange_response: Callable[[dict[str, str | None]], bytes], value: str | None
) -> None:
    with pytest.raises(DianResponseError):
        parse_exchange_emails_response(exchange_response({"Success": value}))


@pytest.mark.parametrize(
    "value",
    [
        b"http://example.invalid/x.zip",
        b"/relative.zip",
        b"https:///missing-host",
        b"https://user@example.invalid/x",
        b"https://user:pass@example.invalid/x",
        b"https://example.invalid/x#fragment",
        b"https://example.invalid/x#",
        b"https://example.invalid/a b",
        b"https://example.invalid/a\x00b",
        b"https://example.invalid:bad/x",
        b"https://example.invalid:99999/x",
        b"https://[bad/x",
        b"\xff",
        b"https://[v1.foo]/x",
        "https://☃.invalid/x".encode(),
        b"https://example.invalid/\x7f",
    ],
)
def test_invalid_download_url(
    exchange_response: Callable[[dict[str, str | None]], bytes], value: bytes
) -> None:
    with pytest.raises(DianResponseError) as error:
        parse_exchange_emails_response(
            exchange_response({"CsvBase64Bytes": b64encode(value).decode()})
        )
    assert isinstance(
        error.value.__cause__, (ValueError, UnicodeError, httpx.InvalidURL)
    )


@pytest.mark.parametrize("value", ["!!!", "a", "é"])
def test_invalid_base64(
    exchange_response: Callable[[dict[str, str | None]], bytes], value: str
) -> None:
    with pytest.raises(DianResponseError) as error:
        parse_exchange_emails_response(exchange_response({"CsvBase64Bytes": value}))
    assert error.value.__cause__ is not None


@pytest.mark.parametrize(
    "kind", ["missing", "nil", "duplicate", "wrong-operation", "wrong-namespace"]
)
def test_result_shape(wrap_soap: Callable[[etree._Element], bytes], kind: str) -> None:
    response = etree.Element(f"{{{WCF}}}GetExchangeEmailsResponse")
    if kind != "missing":
        result = etree.SubElement(response, f"{{{WCF}}}GetExchangeEmailsResult")
        if kind == "nil":
            result.set(f"{{{XSI}}}nil", "1")
        elif kind == "duplicate":
            etree.SubElement(response, f"{{{WCF}}}GetExchangeEmailsResult")
        elif kind == "wrong-operation":
            response.tag = f"{{{WCF}}}OtherResponse"
        else:
            response.tag = "GetExchangeEmailsResponse"
    if kind in {"missing", "nil"}:
        assert parse_exchange_emails_response(wrap_soap(response)) is None
    else:
        with pytest.raises(DianResponseError):
            parse_exchange_emails_response(wrap_soap(response))


def test_model_is_immutable_and_hides_payload() -> None:
    result = ExchangeEmailsResult(
        csv=({"email": "sensitive-directory"},), download_url=URL
    )
    assert "sensitive-directory" not in repr(result)
    assert URL not in repr(result)
    assert not hasattr(result, "__dict__")
    with pytest.raises(FrozenInstanceError):
        result.success = True  # type: ignore[misc]


@pytest.mark.parametrize(
    "environment", [Environment.PRODUCTION, Environment.HABILITATION]
)
@pytest.mark.parametrize("success", ["true", "false"])
def test_signed_query_and_immediate_download(
    encrypted_pfx_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    exchange_response: Callable[[dict[str, str | None]], bytes],
    environment: Environment,
    success: str,
) -> None:
    output = BytesIO()
    with ZipFile(output, "w", compression=ZIP_STORED) as archive:
        archive.writestr(
            "directory.csv", "number,email\r\n0001,synthetic@example.invalid\r\n"
        )
    archive_bytes = output.getvalue()
    clients: list[httpx.Client] = []
    requests: list[httpx.Request] = []
    response = exchange_response(
        {
            "Success": success,
            "CsvBase64Bytes": b64encode(URL.encode()).decode(),
            "StatusCode": "00",
        }
    )

    def handle(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if request.method == "POST":
            return httpx.Response(200, content=response)
        assert clients[0].is_closed
        assert str(request.url) == URL
        assert request.content == b""
        assert "content-type" not in request.headers
        assert "authorization" not in request.headers
        assert "cookie" not in request.headers
        return httpx.Response(200, content=archive_bytes)

    def create(timeout: float) -> httpx.Client:
        client = httpx.Client(transport=httpx.MockTransport(handle), timeout=timeout)
        clients.append(client)
        return client

    monkeypatch.setattr(transport, "create_http_client", create)
    client = DianClient(
        encrypted_pfx_path,
        password="test-password",
        environment=environment,
        timeout=7.5,
    )
    certificate = client.certificate
    encrypted_pfx_path.unlink()
    for _ in range(2):
        result = client.get_exchange_emails()
        assert result is not None
        assert result.csv == ({"number": "0001", "email": "synthetic@example.invalid"},)
        assert result.download_url == URL
        assert result.status_code == "00"
        assert result.success is (success == "true")
        assert client.certificate is certificate
    assert len(requests) == len(clients) == 4
    assert all(c.is_closed for c in clients)
    request = requests[0]
    assert str(request.url) == environment.endpoint
    assert "GetExchangeEmails" in request.headers["Content-Type"]
    root = etree.fromstring(request.content)
    assert root.findtext(f"{{{SOAP}}}Header/{{{WSA}}}To") == environment.addressing_to
    operation = root.find(f"{{{SOAP}}}Body/{{{WCF}}}GetExchangeEmails")
    assert operation is not None and len(operation) == 0
    xmlsec.tree.add_ids(root, ["Id"])
    signature = root.find(f".//{{{DS}}}Signature")
    assert signature is not None
    context = xmlsec.SignatureContext()
    context.key = xmlsec.Key.from_memory(
        certificate.certificate.public_bytes(Encoding.PEM),
        xmlsec.constants.KeyDataFormatCertPem,
    )
    context.verify(signature)
    assert all(r.extensions["timeout"]["read"] == 7.5 for r in requests)


@pytest.mark.parametrize(
    "failure", ["no-url", "nil-result", "invalid-base64", "soap-fault"]
)
def test_no_download_without_usable_result(
    encrypted_pfx_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    exchange_response: Callable[[dict[str, str | None]], bytes],
    soap_fault: bytes,
    failure: str,
) -> None:
    response = exchange_response({})
    if failure == "nil-result":
        root = etree.fromstring(response)
        node = root.find(
            f"{{{SOAP}}}Body/{{{WCF}}}GetExchangeEmailsResponse/{{{WCF}}}GetExchangeEmailsResult"
        )
        assert node is not None
        node.set(f"{{{XSI}}}nil", "true")
        response = etree.tostring(root)
    elif failure == "invalid-base64":
        response = exchange_response({"CsvBase64Bytes": "!"})
    elif failure == "soap-fault":
        response = soap_fault
    clients: list[httpx.Client] = []

    def handle(request: httpx.Request) -> httpx.Response:
        assert request.method == "POST"
        return httpx.Response(200, content=response)

    def create(timeout: float) -> httpx.Client:
        client = httpx.Client(transport=httpx.MockTransport(handle), timeout=timeout)
        clients.append(client)
        return client

    monkeypatch.setattr(transport, "create_http_client", create)
    client = DianClient(encrypted_pfx_path, password="test-password")
    if failure in {"invalid-base64", "soap-fault"}:
        with pytest.raises(
            DianResponseError if failure == "invalid-base64" else DianSoapFaultError
        ):
            client.get_exchange_emails()
    else:
        result = client.get_exchange_emails()
        assert result == (None if failure == "nil-result" else ExchangeEmailsResult())
    assert len(clients) == 1 and clients[0].is_closed


@pytest.mark.parametrize("failure", [302, 403, 404, 500, "timeout", "read-error"])
def test_download_failure_is_not_retried(
    encrypted_pfx_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    exchange_response: Callable[[dict[str, str | None]], bytes],
    failure: int | str,
) -> None:
    clients: list[httpx.Client] = []
    requests: list[httpx.Request] = []
    response = exchange_response({"CsvBase64Bytes": b64encode(URL.encode()).decode()})

    class BrokenStream(httpx.SyncByteStream):
        def __iter__(self) -> Iterator[bytes]:
            yield b"partial"
            raise httpx.ReadError("Synthetic stream failure")

    def handle(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if request.method == "POST":
            return httpx.Response(200, content=response)
        if failure == "timeout":
            raise httpx.ConnectTimeout("Synthetic timeout", request=request)
        if failure == "read-error":
            return httpx.Response(200, stream=BrokenStream())
        assert isinstance(failure, int)
        return httpx.Response(
            failure, headers={"Location": "https://other.example.invalid/"}
        )

    def create(timeout: float) -> httpx.Client:
        client = httpx.Client(transport=httpx.MockTransport(handle), timeout=timeout)
        clients.append(client)
        return client

    monkeypatch.setattr(transport, "create_http_client", create)
    client = DianClient(encrypted_pfx_path, password="test-password")
    with pytest.raises(DianTransportError) as error:
        client.get_exchange_emails()
    assert error.value.status_code == (failure if isinstance(failure, int) else None)
    assert error.value.__cause__ is not None
    assert URL not in str(error.value)
    assert len(requests) == len(clients) == 2
    assert all(c.is_closed for c in clients)


def _csv_zip(content: bytes, *, name: str = "directory.csv") -> bytes:
    output = BytesIO()
    with ZipFile(output, "w") as archive:
        archive.writestr(name, content)
        archive.writestr("readme.txt", "Synthetic directory")
    return output.getvalue()


@pytest.mark.parametrize("separator", [",", ";", "\t", "|"])
def test_native_csv_records_preserve_text(separator: str) -> None:
    content = (
        f"number{separator}name{separator}email\r\n"
        f'0001{separator}"Empresa, de prueba"{separator}synthetic@example.invalid\r\n'
        f'0001{separator}"Línea uno\nLínea dos"{separator}\r\n'
        f'0001{separator}"Empresa, de prueba"{separator}synthetic@example.invalid\r\n'
    ).encode("utf-8-sig")
    result = parse_exchange_emails_csv(_csv_zip(content, name="nested/DIRECTORY.CSV"))
    assert result == (
        {
            "number": "0001",
            "name": "Empresa, de prueba",
            "email": "synthetic@example.invalid",
        },
        {"number": "0001", "name": "Línea uno\nLínea dos", "email": ""},
        {
            "number": "0001",
            "name": "Empresa, de prueba",
            "email": "synthetic@example.invalid",
        },
    )


@pytest.mark.parametrize("content", [b"", b"email\n", b"number,email\r\n"])
def test_empty_csv_records(content: bytes) -> None:
    assert parse_exchange_emails_csv(_csv_zip(content)) == ()


def test_single_column_csv() -> None:
    assert parse_exchange_emails_csv(_csv_zip(b"email\na@example.invalid\n")) == (
        {"email": "a@example.invalid"},
    )


@pytest.mark.parametrize(
    "content",
    [
        b"\xff",
        b"email,email\na,b\n",
        b",email\na,b\n",
        b" \na\n",
        b"\n",
        b"number,email\n1\n",
        b"number,email\n1,a,extra\n",
        b'number,email\n1,"unterminated\n',
    ],
)
def test_invalid_csv_content(content: bytes) -> None:
    with pytest.raises(DianResponseError) as error:
        parse_exchange_emails_csv(_csv_zip(content))
    assert error.value.__cause__ is not None


@pytest.mark.parametrize(
    "names", [[], ["readme.txt"], ["first.csv", "second.csv"], ["folder.csv/"]]
)
def test_archive_requires_one_csv(names: list[str]) -> None:
    output = BytesIO()
    with ZipFile(output, "w") as archive:
        for name in names:
            archive.writestr(name, b"email\n")
    with pytest.raises(DianResponseError) as error:
        extract_exchange_emails_csv(output.getvalue())
    assert isinstance(error.value.__cause__, ValueError)


@pytest.mark.parametrize("kind", ["not-zip", "crc", "encrypted", "unsupported"])
def test_unreadable_archive(kind: str) -> None:
    payload = b"email\na@example.invalid\n"
    data = bytearray(_csv_zip(payload))
    if kind == "not-zip":
        data = bytearray(b"not a ZIP archive")
    elif kind == "crc":
        data[data.index(payload)] ^= 1
    else:
        local = data.index(b"PK\x03\x04")
        central = data.index(b"PK\x01\x02")
        if kind == "encrypted":
            data[local + 6] |= 1
            data[central + 8] |= 1
        else:
            data[local + 8 : local + 10] = (99).to_bytes(2, "little")
            data[central + 10 : central + 12] = (99).to_bytes(2, "little")
    with pytest.raises(DianResponseError) as error:
        parse_exchange_emails_csv(bytes(data))
    assert error.value.__cause__ is not None


def test_deflated_csv_archive() -> None:
    output = BytesIO()
    with ZipFile(output, "w", compression=ZIP_DEFLATED) as archive:
        archive.writestr("directory.csv", b"email\na@example.invalid\n")
    assert parse_exchange_emails_csv(output.getvalue()) == (
        {"email": "a@example.invalid"},
    )


def test_invalid_csv_download_closes_connections(
    encrypted_pfx_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    exchange_response: Callable[[dict[str, str | None]], bytes],
) -> None:
    clients: list[httpx.Client] = []
    response = exchange_response({"CsvBase64Bytes": b64encode(URL.encode()).decode()})

    def handle(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200, content=response if request.method == "POST" else b"not a ZIP"
        )

    def create(timeout: float) -> httpx.Client:
        http = httpx.Client(transport=httpx.MockTransport(handle), timeout=timeout)
        clients.append(http)
        return http

    monkeypatch.setattr(transport, "create_http_client", create)
    client = DianClient(encrypted_pfx_path, password="test-password")
    with pytest.raises(DianResponseError):
        client.get_exchange_emails()
    assert len(clients) == 2 and all(http.is_closed for http in clients)

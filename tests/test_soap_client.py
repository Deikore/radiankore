"""End-to-end offline client tests with a real signer and HTTPX MockTransport."""

from base64 import b64encode
from collections.abc import Iterator
from pathlib import Path

import httpx
import pytest
import xmlsec
from lxml import etree

from radiankore import (
    DianClient,
    DianResponseError,
    DianSignatureError,
    DianSoapFaultError,
    DianTransportError,
    Environment,
)
from radiankore._soap import transport
from radiankore._soap.namespaces import (
    CAC,
    CBC,
    DS,
    RESPONSE,
    SOAP,
    WCF,
    WSA,
    WSU,
)
from radiankore.catalogs import EventType, IdentificationType


@pytest.mark.parametrize(
    "environment",
    [
        None,
        Environment.PRODUCTION,
        "production",
        Environment.HABILITATION,
        "habilitation",
    ],
)
def test_query_events_uses_selected_environment(
    encrypted_pfx_path: Path,
    mock_http: tuple[list[httpx.Client], list[httpx.Request]],
    environment: Environment | str | None,
) -> None:
    http, requests = mock_http
    client = (
        DianClient(encrypted_pfx_path, password="test-password")
        if environment is None
        else DianClient(
            encrypted_pfx_path, password="test-password", environment=environment
        )
    )
    selected = (
        Environment.PRODUCTION if environment is None else Environment(environment)
    )
    assert not requests and not http
    result = client.get_invoice_events("  SYNTHETIC-CUFE  ")
    assert client.environment is selected
    assert len(result.events) == 9
    assert len(requests) == 1
    request = requests[0]
    assert str(request.url) == selected.endpoint
    assert (
        "http://wcf.dian.colombia/IWcfDianCustomerServices/GetStatusEvent"
        in request.headers["Content-Type"]
    )
    assert request.extensions["timeout"] == {
        "connect": 30.0,
        "read": 30.0,
        "write": 30.0,
        "pool": 30.0,
    }
    root = etree.fromstring(request.content)
    assert root.findtext(f"{{{SOAP}}}Header/{{{WSA}}}To") == selected.addressing_to
    assert (
        root.findtext(f"{{{SOAP}}}Body/{{{WCF}}}GetStatusEvent/{{{WCF}}}trackId")
        == "SYNTHETIC-CUFE"
    )
    assert len(http) == 1 and http[0].is_closed


def test_repeated_queries_close_connections_and_reuse_loaded_certificate(
    encrypted_pfx_path: Path,
    mock_http: tuple[list[httpx.Client], list[httpx.Request]],
) -> None:
    clients, requests = mock_http
    client = DianClient(encrypted_pfx_path, password="test-password", timeout=7.5)
    certificate = client.certificate
    encrypted_pfx_path.unlink()
    assert not clients

    for cufe in ("FIRST-CUFE", "SECOND-CUFE"):
        result = client.get_invoice_events(cufe)
        assert len(result.events) == 9
        assert all(http.is_closed for http in clients)
        assert client.certificate is certificate

    assert len(clients) == 2 and clients[0] is not clients[1]
    assert len(requests) == 2
    assert requests[0].content != requests[1].content
    assert all(
        request.extensions["timeout"]
        == {"connect": 7.5, "read": 7.5, "write": 7.5, "pool": 7.5}
        for request in requests
    )


def test_queries_share_certificate_and_use_independent_operation_actions(
    encrypted_pfx_path: Path,
    soap_response: bytes,
    acquirer_response: bytes,
    document_info_response: bytes,
    reference_notes_response: bytes,
    xml_document_response: bytes,
    downloaded_document: bytes,
    document_status_response: bytes,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    clients: list[httpx.Client] = []
    requests: list[httpx.Request] = []

    def handle(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        root = etree.fromstring(request.content)
        body = root.find(f"{{{SOAP}}}Body")
        assert body is not None
        operation = etree.QName(body[0]).localname
        content = {
            "GetStatusEvent": soap_response,
            "GetStatus": document_status_response,
            "GetAcquirer": acquirer_response,
            "GetDocumentInfo": document_info_response,
            "GetReferenceNotes": reference_notes_response,
            "GetXmlByDocumentKey": xml_document_response,
        }[operation]
        return httpx.Response(200, content=content)

    def create(timeout: float) -> httpx.Client:
        http = httpx.Client(transport=httpx.MockTransport(handle), timeout=timeout)
        clients.append(http)
        return http

    monkeypatch.setattr(transport, "create_http_client", create)
    client = DianClient(encrypted_pfx_path, password="test-password")
    certificate = client.certificate
    encrypted_pfx_path.unlink()
    assert len(client.get_invoice_events("CUFE").events) == 9
    assert clients[0].is_closed
    result = client.get_acquirer(
        identification_type=IdentificationType.NIT, identification_number="001"
    )
    assert result is not None and result.email == "buyer@example.invalid"
    assert client.certificate is certificate
    document_result = client.get_document_info("UUID")
    assert document_result is not None and len(document_result.documents) == 1
    notes_result = client.get_reference_notes("identifier")
    assert notes_result is not None and notes_result.xml_bytes == b"\x00\xffNOTES"
    assert client.certificate is certificate
    xml_result = client.get_xml_by_document_key("DOCUMENT-KEY")
    assert xml_result is not None and xml_result.document_xml == downloaded_document
    assert client.certificate is certificate
    status_result = client.get_status("TRACK-ID")
    assert (
        status_result is not None and status_result.xml_base64_bytes == b"<validation/>"
    )
    assert client.certificate is certificate
    assert len(clients) == 6 and all(http.is_closed for http in clients)
    ids: list[set[str]] = []
    for request, operation in zip(
        requests,
        [
            "GetStatusEvent",
            "GetAcquirer",
            "GetDocumentInfo",
            "GetReferenceNotes",
            "GetXmlByDocumentKey",
            "GetStatus",
        ],
        strict=True,
    ):
        root = etree.fromstring(request.content)
        action = f"http://wcf.dian.colombia/IWcfDianCustomerServices/{operation}"
        assert root.findtext(f"{{{SOAP}}}Header/{{{WSA}}}Action") == action
        assert f'action="{action}"' in request.headers["Content-Type"]
        ids.append(
            {
                value
                for node in root.iter()
                if (value := node.get(f"{{{WSU}}}Id")) is not None
            }
        )
    assert all(ids)
    assert all(
        left.isdisjoint(right) for i, left in enumerate(ids) for right in ids[i + 1 :]
    )


@pytest.mark.parametrize("cufe", [None, 123, b"CUFE", []])
def test_invalid_cufe_type_never_sends(
    encrypted_pfx_path: Path,
    mock_http: tuple[list[httpx.Client], list[httpx.Request]],
    cufe: object,
) -> None:
    client = DianClient(encrypted_pfx_path, password="test-password")
    with pytest.raises(TypeError, match="cufe must be a string"):
        client.get_invoice_events(cufe)  # type: ignore[arg-type]
    assert mock_http == ([], [])


@pytest.mark.parametrize("cufe", ["", " \n\t"])
def test_empty_cufe_never_sends(
    encrypted_pfx_path: Path,
    mock_http: tuple[list[httpx.Client], list[httpx.Request]],
    cufe: str,
) -> None:
    client = DianClient(encrypted_pfx_path, password="test-password")
    with pytest.raises(ValueError, match="cufe"):
        client.get_invoice_events(cufe)
    assert not mock_http[0] and not mock_http[1]


def test_client_remains_usable_after_failed_query(
    encrypted_pfx_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    soap_response: bytes,
) -> None:
    clients: list[httpx.Client] = []
    calls: list[httpx.Request] = []

    def handle(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        if len(calls) == 1:
            raise httpx.ReadTimeout("synthetic timeout", request=request)
        return httpx.Response(200, content=soap_response)

    def create(timeout: float) -> httpx.Client:
        http = httpx.Client(transport=httpx.MockTransport(handle), timeout=timeout)
        clients.append(http)
        return http

    monkeypatch.setattr(transport, "create_http_client", create)
    client = DianClient(encrypted_pfx_path, password="test-password")

    with pytest.raises(DianTransportError):
        client.get_invoice_events("FIRST-CUFE")
    assert len(calls) == 1 and clients[0].is_closed

    result = client.get_invoice_events("SECOND-CUFE")
    assert len(result.events) == 9
    assert len(calls) == 2
    assert len(clients) == 2 and all(http.is_closed for http in clients)


@pytest.mark.parametrize("environment", ["SANDBOX", "produccion", "", None])
def test_invalid_environment_fails_before_reading_pfx(
    tmp_path: Path, environment: str | None
) -> None:
    with pytest.raises(ValueError):
        # None is deliberately invalid at the public boundary.
        DianClient(tmp_path / "missing.pfx", environment=environment)  # type: ignore[arg-type]


@pytest.mark.parametrize("timeout", [0.0, -1.0, float("nan"), float("inf"), True])
def test_invalid_timeout_fails_before_reading_pfx(
    tmp_path: Path, timeout: float
) -> None:
    with pytest.raises(ValueError, match="timeout"):
        DianClient(tmp_path / "missing.pfx", timeout=timeout)


@pytest.mark.parametrize(
    "operation", ["events", "acquirer", "documents", "notes", "xml", "status"]
)
@pytest.mark.parametrize(
    "status,kind,error",
    [
        (200, "fault", DianSoapFaultError),
        (500, "fault", DianSoapFaultError),
        (503, "html", DianTransportError),
        (302, "html", DianTransportError),
        (200, "html", DianResponseError),
        (500, "result", DianTransportError),
    ],
)
def test_http_and_soap_errors_are_distinct(
    encrypted_pfx_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    soap_response: bytes,
    soap_fault: bytes,
    status: int,
    kind: str,
    error: type[Exception],
    operation: str,
) -> None:
    calls: list[httpx.Request] = []
    responses: list[httpx.Response] = []
    data = {
        "fault": soap_fault,
        "html": b"<html>upstream failure</html>",
        "result": soap_response,
    }[kind]

    def handle(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        response = httpx.Response(
            status,
            content=data,
            headers={"Location": "https://example.invalid/redirect"},
        )
        responses.append(response)
        return response

    http = httpx.Client(transport=httpx.MockTransport(handle))
    monkeypatch.setattr(transport, "create_http_client", lambda timeout: http)
    client = DianClient(encrypted_pfx_path, password="test-password")
    with pytest.raises(error) as raised:
        if operation == "events":
            client.get_invoice_events("CUFE")
        elif operation == "acquirer":
            client.get_acquirer(
                identification_type=IdentificationType.NIT, identification_number="001"
            )
        elif operation == "documents":
            client.get_document_info("UUID")
        elif operation == "notes":
            client.get_reference_notes("identifier")
        elif operation == "xml":
            client.get_xml_by_document_key("DOCUMENT-KEY")
        else:
            client.get_status("TRACK-ID")
    assert len(calls) == 1 and http.is_closed
    assert all(response.is_closed for response in responses)
    if isinstance(raised.value, DianTransportError):
        assert raised.value.status_code == status
        assert isinstance(raised.value.__cause__, httpx.HTTPStatusError)
    if isinstance(raised.value, DianSoapFaultError):
        assert raised.value.code == "s:Sender"


@pytest.mark.parametrize(
    "error_type", [httpx.ConnectError, httpx.ReadTimeout, httpx.ConnectTimeout]
)
def test_network_errors_preserve_cause_and_do_not_retry(
    encrypted_pfx_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    error_type: type[httpx.RequestError],
) -> None:
    calls: list[httpx.Request] = []

    def handle(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        raise error_type("synthetic error", request=request)

    http = httpx.Client(transport=httpx.MockTransport(handle))
    monkeypatch.setattr(transport, "create_http_client", lambda timeout: http)
    client = DianClient(encrypted_pfx_path, password="test-password")
    with pytest.raises(DianTransportError) as error:
        client.get_invoice_events("CUFE")
    assert isinstance(error.value.__cause__, error_type)
    assert len(calls) == 1 and http.is_closed


@pytest.mark.parametrize(
    "descriptions,expected",
    [
        ([], ""),
        (["XML-only description"], "XML-only description"),
        ([" First ", "  ", "Second"], "First\nSecond"),
    ],
)
def test_client_preserves_xml_descriptions_with_enum_codes(
    encrypted_pfx_path: Path,
    soap_response: bytes,
    application_response: bytes,
    monkeypatch: pytest.MonkeyPatch,
    descriptions: list[str],
    expected: str,
) -> None:
    application = etree.fromstring(application_response)
    response = application.find(f"{{{CAC}}}DocumentResponse/{{{CAC}}}Response")
    assert response is not None
    for description in response.findall(f"{{{CBC}}}Description"):
        response.remove(description)
    for value in descriptions:
        etree.SubElement(response, f"{{{CBC}}}Description").text = value
    payload = etree.tostring(application)
    soap = etree.fromstring(soap_response)
    encoded = soap.find(f".//{{{RESPONSE}}}XmlBase64Bytes")
    assert encoded is not None
    encoded.text = b64encode(payload).decode("ascii")
    clients: list[httpx.Client] = []
    responses: list[httpx.Response] = []

    # Keep HTTPX construction and resource management real; replace only sending.
    def send(
        http: httpx.Client, request: httpx.Request, **kwargs: object
    ) -> httpx.Response:
        clients.append(http)
        result = httpx.Response(200, content=etree.tostring(soap), request=request)
        responses.append(result)
        return result

    monkeypatch.setattr(httpx.Client, "send", send)
    client = DianClient(encrypted_pfx_path, password="test-password", timeout=7.5)
    assert not clients
    result = client.get_invoice_events("CUFE")

    event = result.events[0]
    assert event.code is EventType.INVOICE_ACKNOWLEDGEMENT
    assert event.description == expected
    assert event.description != event.code.label
    assert event.issuer is not None
    assert event.issuer.identification_type is IdentificationType.NIT
    assert result.application_response_xml == payload
    assert len(clients) == 1 and clients[0].is_closed
    assert clients[0].timeout.as_dict() == {
        "connect": 7.5,
        "read": 7.5,
        "write": 7.5,
        "pool": 7.5,
    }
    assert not clients[0].follow_redirects
    assert len(responses) == 1 and responses[0].is_closed


def test_invalid_signature_template_never_opens_http_client(
    encrypted_pfx_path: Path,
    mock_http: tuple[list[httpx.Client], list[httpx.Request]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def invalid_template(*args: object, **kwargs: object) -> etree._Element:
        return etree.Element(f"{{{DS}}}Signature")

    monkeypatch.setattr(xmlsec.template, "create", invalid_template)
    client = DianClient(encrypted_pfx_path, password="test-password")
    with pytest.raises(DianSignatureError, match="signature template"):
        client.get_invoice_events("CUFE")
    clients, requests = mock_http
    assert not clients and not requests


@pytest.mark.parametrize("error_type", [httpx.ReadError, httpx.ReadTimeout])
def test_interrupted_response_closes_resources_and_client_remains_usable(
    encrypted_pfx_path: Path,
    soap_response: bytes,
    monkeypatch: pytest.MonkeyPatch,
    error_type: type[httpx.RequestError],
) -> None:
    class InterruptedStream(httpx.SyncByteStream):
        closed = False

        def __iter__(self) -> Iterator[bytes]:
            yield b"<partial-response>"
            raise error_type("synthetic interrupted response")

        def close(self) -> None:
            self.closed = True

    interrupted = InterruptedStream()
    clients: list[httpx.Client] = []
    responses: list[httpx.Response] = []
    requests: list[httpx.Request] = []

    def handle(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        response = (
            httpx.Response(200, stream=interrupted)
            if len(requests) == 1
            else httpx.Response(200, content=soap_response)
        )
        responses.append(response)
        return response

    def create(timeout: float) -> httpx.Client:
        http = httpx.Client(transport=httpx.MockTransport(handle), timeout=timeout)
        clients.append(http)
        return http

    monkeypatch.setattr(transport, "create_http_client", create)
    client = DianClient(encrypted_pfx_path, password="test-password")
    with pytest.raises(DianTransportError) as error:
        client.get_invoice_events("FIRST-CUFE")
    assert isinstance(error.value.__cause__, error_type)
    assert len(requests) == 1
    assert interrupted.closed and responses[0].is_closed and clients[0].is_closed

    result = client.get_invoice_events("SECOND-CUFE")
    assert len(result.events) == 9
    assert len(requests) == 2
    assert all(http.is_closed for http in clients)
    assert all(response.is_closed for response in responses)

"""Execute the real emission guides against synthetic certificates and MockTransport."""

import re
from collections.abc import Callable, Iterator, Mapping
from pathlib import Path
from typing import Any, cast, get_args
from unittest.mock import patch

import httpx
import pytest
from lxml import etree

from radiankore import DianClient, DigitalCertificate, Environment
from radiankore._soap import transport
from radiankore._soap.namespaces import WCF, XSI
from radiankore.models.events import (
    PreparedRadianEvent,
    RadianEvent,
    RadianSoftware,
)


def python_blocks(path: Path) -> list[str]:
    """Read the Python code actually published, without duplicating its examples."""
    return re.findall(r"```python\n(.*?)```", path.read_text(), re.DOTALL)


def example_events(value: object) -> Iterator[RadianEvent]:
    """Find named event alternatives, including the invoice guide's event mapping."""
    if isinstance(value, get_args(RadianEvent.__value__)):
        yield cast(RadianEvent, value)
    elif isinstance(value, Mapping):
        for child in value.values():
            yield from example_events(child)


@pytest.mark.parametrize(
    "guide,expected_codes",
    [
        ("radian-termination", {"044"}),
        ("radian-registration", {"036"}),
        ("radian-payments", {"045", "046"}),
        ("radian-endorsements", {"037", "038", "039", "040", "047"}),
        ("radian-guarantees", {"035"}),
        ("radian-economic-rights", {"049", "050", "051"}),
        ("radian-restrictions", {"041", "042"}),
        ("radian-protests", {"048"}),
        ("invoice-emission", {"030", "031", "032", "033", "034"}),
        ("mandate", {"043"}),
    ],
)
def test_emission_guides_execute_with_verified_signatures(
    guide: str,
    expected_codes: set[str],
    encrypted_pfx_path: Path,
    digital_certificate: DigitalCertificate,
    verify_event_signature: Callable[[bytes, DigitalCertificate], None],
    radian_schema: etree.XMLSchema | None,
    wrap_soap: Callable[[etree._Element], bytes],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    docs = Path(__file__).resolve().parents[1] / "docs/operations"
    if not (docs / f"{guide}.md").is_file():
        pytest.skip("Documentation examples are excluded from distributions.")
    response = etree.Element(f"{{{WCF}}}SendEventUpdateStatusResponse")
    etree.SubElement(response, f"{{{WCF}}}SendEventUpdateStatusResult").set(
        f"{{{XSI}}}nil", "true"
    )
    payload = wrap_soap(response)
    connections: list[httpx.Client] = []
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, content=payload)

    def http_client(timeout: float) -> httpx.Client:
        connection = httpx.Client(
            transport=httpx.MockTransport(handler), timeout=timeout
        )
        connections.append(connection)
        return connection

    monkeypatch.setattr(transport, "create_http_client", http_client)
    client = DianClient(
        encrypted_pfx_path,
        password="test-password",
        environment=Environment.HABILITATION,
    )
    # The mandate guide explicitly loads its example PDF before local preparation.
    (tmp_path / "contrato.pdf").write_bytes(b"%PDF-1.7\nSynthetic contract.\n%%EOF")
    monkeypatch.chdir(tmp_path)
    namespace: dict[str, Any] = {}
    seen: set[int] = set()
    held: list[RadianEvent] = []
    codes: set[str] = set()
    prepared: PreparedRadianEvent
    blocks = python_blocks(docs / f"{guide}.md")
    if guide.startswith("radian-"):
        blocks.insert(0, python_blocks(docs / "radian-emission.md")[0])
    with patch("radiankore.DianClient", return_value=client):
        for number, block in enumerate(blocks):
            exec(compile(block, f"{guide}.md:block-{number}", "exec"), namespace)
            software = namespace["software"]
            assert isinstance(software, RadianSoftware)
            for name, value in list(namespace.items()):
                if name.startswith("__"):
                    continue
                for event in example_events(value):
                    if id(event) in seen:
                        continue
                    seen.add(id(event))
                    held.append(event)
                    prepared = client.prepare_radian_event(
                        event=event, software=software
                    )
                    codes.add(prepared.code.value)
                    verify_event_signature(prepared.xml_bytes, digital_certificate)
                    if radian_schema is not None:
                        radian_schema.assertValid(etree.fromstring(prepared.xml_bytes))
    assert codes == expected_codes
    assert held
    assert all(connection.is_closed for connection in connections)
    if guide in {"mandate", "invoice-emission"}:
        assert len(requests) == 1
    else:
        assert not requests


@pytest.fixture
def documented_query_client(
    encrypted_pfx_path: Path,
    soap_response: bytes,
    document_status_response: bytes,
    document_info_response: bytes,
    reference_notes_response: bytes,
    xml_document_response: bytes,
    acquirer_response: bytes,
    wrap_soap: Callable[[etree._Element], bytes],
    monkeypatch: pytest.MonkeyPatch,
) -> tuple[DianClient, list[str], list[httpx.Client]]:
    """Serve every documented query offline, including the second directory GET."""
    from base64 import b64encode
    from io import BytesIO
    from zipfile import ZipFile

    from radiankore._soap.namespaces import (
        EXCHANGE_EMAIL_RESPONSE,
        NUMBER_RANGE_LIST,
        SOAP,
    )

    response = etree.Element(f"{{{WCF}}}GetExchangeEmailsResponse")
    result = etree.SubElement(response, f"{{{WCF}}}GetExchangeEmailsResult")
    etree.SubElement(result, f"{{{EXCHANGE_EMAIL_RESPONSE}}}Success").text = "true"
    etree.SubElement(
        result, f"{{{EXCHANGE_EMAIL_RESPONSE}}}CsvBase64Bytes"
    ).text = b64encode(b"https://directory.example.invalid/emails.zip").decode()
    numbering = etree.Element(f"{{{WCF}}}GetNumberingRangeResponse")
    ranges = etree.SubElement(numbering, f"{{{WCF}}}GetNumberingRangeResult")
    etree.SubElement(ranges, f"{{{NUMBER_RANGE_LIST}}}OperationCode").text = "100"
    responses = {
        "GetStatusEvent": soap_response,
        "GetStatus": document_status_response,
        "GetDocumentInfo": document_info_response,
        "GetReferenceNotes": reference_notes_response,
        "GetXmlByDocumentKey": xml_document_response,
        "GetAcquirer": acquirer_response,
        "GetExchangeEmails": wrap_soap(response),
        "GetNumberingRange": wrap_soap(numbering),
    }
    archive = BytesIO()
    with ZipFile(archive, "w") as zipped:
        zipped.writestr("emails.csv", "NIT,Email\n900000001,example@example.invalid\n")
    operations: list[str] = []
    connections: list[httpx.Client] = []

    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "GET":
            assert str(request.url) == "https://directory.example.invalid/emails.zip"
            assert not request.content
            operations.append("GET CSV")
            return httpx.Response(200, content=archive.getvalue())
        body = etree.fromstring(request.content).find(f"{{{SOAP}}}Body")
        assert body is not None and len(body) == 1
        operation = etree.QName(body[0]).localname
        operations.append(operation)
        return httpx.Response(200, content=responses[operation])

    def factory(timeout: float) -> httpx.Client:
        connection = httpx.Client(
            transport=httpx.MockTransport(handler), timeout=timeout
        )
        connections.append(connection)
        return connection

    monkeypatch.setattr(transport, "create_http_client", factory)
    return (
        DianClient(
            encrypted_pfx_path,
            password="test-password",
            environment=Environment.HABILITATION,
        ),
        operations,
        connections,
    )


def test_published_integration_functions_execute_all_queries(
    documented_query_client: tuple[DianClient, list[str], list[httpx.Client]],
    downloaded_document: bytes,
    tmp_path: Path,
) -> None:
    """Exercise the public recipes and assert data and byte-preserving download."""
    docs = Path(__file__).resolve().parents[1] / "docs/guides"
    if not (docs / "queries.md").exists():
        pytest.skip("Documentation examples are excluded from distributions.")
    client, operations, connections = documented_query_client
    namespace: dict[str, Any] = {}
    for block in python_blocks(docs / "queries.md"):
        exec(compile(block, "guides/queries.md", "exec"), namespace)
    assert not operations  # Importing recipes must not transmit anything.
    status, events, information, notes = namespace["inspect_invoice"](
        client, "SYNTHETIC-CUFE"
    )
    assert status.is_valid and status.messages
    assert len(events.events) == 9
    assert information.documents[0].holder.name == "Document holder"
    assert notes.notes
    destination = tmp_path / "download.xml"
    assert namespace["save_document"](client, "SYNTHETIC-KEY", destination)
    assert destination.read_bytes() == downloaded_document
    numbering, acquirer, emails = namespace["inspect_directory"](
        client, "900000001", "900000002", "SYNTHETIC-SOFTWARE", "900000003"
    )
    assert numbering.operation_code == "100"
    assert acquirer.email == "buyer@example.invalid"
    assert emails.csv == ({"NIT": "900000001", "Email": "example@example.invalid"},)
    assert len(operations) == 9 and len(set(operations)) == 9
    assert all(connection.is_closed for connection in connections)


@pytest.mark.parametrize(
    "guide,operation",
    [
        ("status", "GetStatus"),
        ("events", "GetStatusEvent"),
        ("document-info", "GetDocumentInfo"),
        ("reference-notes", "GetReferenceNotes"),
        ("xml-document", "GetXmlByDocumentKey"),
        ("numbering-range", "GetNumberingRange"),
        ("acquirer", "GetAcquirer"),
        ("exchange-emails", "GetExchangeEmails"),
    ],
)
def test_existing_query_examples_execute(
    guide: str,
    operation: str,
    documented_query_client: tuple[DianClient, list[str], list[httpx.Client]],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Validate the actual eight operation pages as well as the new recipes."""
    page = Path(__file__).resolve().parents[1] / f"docs/operations/{guide}.md"
    if not page.exists():
        pytest.skip("Documentation examples are excluded from distributions.")
    client, operations, connections = documented_query_client
    namespace: dict[str, Any] = {}
    monkeypatch.chdir(tmp_path)
    with patch("radiankore.DianClient", return_value=client):
        for number, block in enumerate(python_blocks(page)):
            exec(compile(block, f"{guide}.md:block-{number}", "exec"), namespace)
    assert operation in operations
    assert all(connection.is_closed for connection in connections)


def test_local_preparation_recipe_keeps_original_signed_bytes(
    encrypted_pfx_path: Path,
    radian_event_factory: Callable[[str], RadianEvent],
    radian_software: RadianSoftware,
    digital_certificate: DigitalCertificate,
    verify_event_signature: Callable[[bytes, DigitalCertificate], None],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The documented preparation helper does not send or reserialize the result."""
    from io import BytesIO
    from zipfile import ZipFile

    docs = Path(__file__).resolve().parents[1] / "docs/guides"
    if not (docs / "journeys.md").exists():
        pytest.skip("Documentation examples are excluded from distributions.")

    def forbid_network(timeout: float) -> httpx.Client:
        pytest.fail("Local preparation must not create an HTTP client.")

    monkeypatch.setattr(transport, "create_http_client", forbid_network)
    namespace: dict[str, Any] = {}
    for block in python_blocks(docs / "journeys.md"):
        exec(compile(block, "guides/journeys.md", "exec"), namespace)
    client = DianClient(encrypted_pfx_path, password="test-password")
    prepared = namespace["prepare_for_review"](
        client, radian_event_factory("441"), radian_software
    )
    verify_event_signature(prepared.xml_bytes, digital_certificate)
    with ZipFile(BytesIO(prepared.zip_bytes)) as archive:
        assert archive.namelist() == [f"ar_{prepared.cude}.xml"]
        assert archive.read(archive.namelist()[0]) == prepared.xml_bytes


@pytest.mark.parametrize(
    "kind", ["accepted", "rejected", "nil", "malformed", "fault", "network"]
)
def test_first_query_recipe_preserves_result_and_failures(
    kind: str,
    encrypted_pfx_path: Path,
    document_status_response: bytes,
    soap_fault: bytes,
    wrap_soap: Callable[[etree._Element], bytes],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The introductory recipe neither hides rejection nor retries failures."""
    from radiankore import DianResponseError, DianSoapFaultError, DianTransportError
    from radiankore._soap.namespaces import RESPONSE

    page = Path(__file__).resolve().parents[1] / "docs/guides/preparation.md"
    if not page.exists():
        pytest.skip("Documentation examples are excluded from distributions.")
    namespace: dict[str, Any] = {}
    for block in python_blocks(page):
        exec(compile(block, str(page), "exec"), namespace)
    payload = document_status_response
    if kind == "rejected":
        root = etree.fromstring(payload)
        valid = root.find(f".//{{{RESPONSE}}}IsValid")
        assert valid is not None
        valid.text = "false"
        payload = etree.tostring(root)
    elif kind == "nil":
        response = etree.Element(f"{{{WCF}}}GetStatusResponse")
        etree.SubElement(response, f"{{{WCF}}}GetStatusResult").set(
            f"{{{XSI}}}nil", "true"
        )
        payload = wrap_soap(response)
    elif kind == "malformed":
        payload = b"invalid SOAP"
    elif kind == "fault":
        payload = soap_fault
    attempts: list[httpx.Request] = []
    connections: list[httpx.Client] = []

    def handler(request: httpx.Request) -> httpx.Response:
        attempts.append(request)
        if kind == "network":
            raise httpx.ReadTimeout("Synthetic timeout", request=request)
        return httpx.Response(500 if kind == "fault" else 200, content=payload)

    def factory(timeout: float) -> httpx.Client:
        connection = httpx.Client(
            transport=httpx.MockTransport(handler), timeout=timeout
        )
        connections.append(connection)
        return connection

    monkeypatch.setattr(transport, "create_http_client", factory)
    arguments = (encrypted_pfx_path, "test-password", "SYNTHETIC-KEY")
    errors = {
        "malformed": DianResponseError,
        "fault": DianSoapFaultError,
        "network": DianTransportError,
    }
    if kind in errors:
        with pytest.raises(errors[kind]):
            namespace["check_document"](*arguments)
    else:
        result = namespace["check_document"](*arguments)
        if kind == "nil":
            assert result is None
        else:
            assert result.is_valid is (kind == "accepted")
            assert result.messages
    assert len(attempts) == 1 and all(c.is_closed for c in connections)


def test_performance_guide_examples_execute(
    document_info_response: bytes,
    monkeypatch: pytest.MonkeyPatch,
    encrypted_pfx_path: Path,
    digital_certificate: DigitalCertificate,
    mock_http: tuple[list[httpx.Client], list[httpx.Request]],
) -> None:
    path = Path(__file__).resolve().parents[1] / "docs/guides/performance.md"
    if not path.is_file():
        pytest.skip("Documentation examples are excluded from distributions.")
    namespace: dict[str, Any] = {}
    for block in python_blocks(path):
        exec(compile(block, str(path), "exec"), namespace)
    result = namespace["consultar"](
        encrypted_pfx_path.read_bytes(), "test-password", "SYNTHETIC"
    )
    assert len(result.events) == 9
    connections = mock_http[0]

    def create(timeout: float) -> httpx.Client:
        client = httpx.Client(
            transport=httpx.MockTransport(
                lambda request: httpx.Response(200, content=document_info_response)
            ),
            timeout=timeout,
        )
        connections.append(client)
        return client

    monkeypatch.setattr(transport, "create_http_client", create)
    result = namespace["consultar_con_material"](digital_certificate, "SYNTHETIC")
    assert result is not None and result.documents
    assert all(client.is_closed for client in mock_http[0])

"""Synthetic certificate fixtures; no real credentials or DIAN data are used."""

from base64 import b64encode
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from pathlib import Path

import httpx
import pytest
from cryptography import x509
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.serialization import BestAvailableEncryption, pkcs12
from cryptography.x509.oid import NameOID
from lxml import etree

from radiankore import DigitalCertificate
from radiankore._soap import transport
from radiankore._soap.namespaces import ACQUIRER, ARRAY, RESPONSE, SOAP, WCF


@pytest.fixture(scope="session")
def digital_certificate() -> DigitalCertificate:
    """Generate a self-signed certificate and key entirely in memory."""
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "radiankore.test")])
    now = datetime.now(UTC)
    certificate = (
        x509.CertificateBuilder()
        .subject_name(name)
        .issuer_name(name)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - timedelta(days=1))
        .not_valid_after(now + timedelta(days=1))
        .sign(key, hashes.SHA256())
    )
    return DigitalCertificate(key, certificate)


@pytest.fixture
def encrypted_pfx_path(tmp_path: Path, digital_certificate: DigitalCertificate) -> Path:
    """Write a synthetic encrypted certificate for client tests."""
    path = tmp_path / "certificate.pfx"
    path.write_bytes(
        pkcs12.serialize_key_and_certificates(
            b"test",
            digital_certificate.private_key,
            digital_certificate.certificate,
            None,
            BestAvailableEncryption(b"test-password"),
        )
    )
    return path


@pytest.fixture
def application_response() -> bytes:
    """Load a synthetic nine-event document with no real taxpayer information."""
    return (Path(__file__).parent / "fixtures" / "invoice_events.xml").read_bytes()


@pytest.fixture
def wrap_soap() -> Callable[[etree._Element], bytes]:
    """Wrap an operation response in a SOAP 1.2 envelope."""

    def wrap(response: etree._Element) -> bytes:
        envelope = etree.Element(f"{{{SOAP}}}Envelope", nsmap={"s": SOAP})
        etree.SubElement(envelope, f"{{{SOAP}}}Body").append(response)
        return etree.tostring(envelope)

    return wrap


@pytest.fixture
def acquirer_response(wrap_soap: Callable[[etree._Element], bytes]) -> bytes:
    """Return synthetic acquirer data with no real personal information."""
    response = etree.Element(f"{{{WCF}}}GetAcquirerResponse")
    result = etree.SubElement(response, f"{{{WCF}}}GetAcquirerResult")
    for name, value in {
        "Message": "Synthetic result",
        "ReceiverEmail": "buyer@example.invalid",
        "ReceiverName": "Synthetic Buyer",
        "StatusCode": "TEST-STATUS",
    }.items():
        etree.SubElement(result, f"{{{ACQUIRER}}}{name}").text = value
    return wrap_soap(response)


@pytest.fixture
def document_info_response(wrap_soap: Callable[[etree._Element], bytes]) -> bytes:
    """Wrap a complete synthetic GetDocumentInfo data-contract response."""
    payload = (Path(__file__).parent / "fixtures" / "document_info.xml").read_bytes()
    return wrap_soap(etree.fromstring(payload))


@pytest.fixture
def soap_response(
    application_response: bytes, wrap_soap: Callable[[etree._Element], bytes]
) -> bytes:
    """Wrap the fixture in a successful response containing a DIAN notification."""
    response = etree.Element(f"{{{WCF}}}GetStatusEventResponse")
    result = etree.SubElement(response, f"{{{WCF}}}GetStatusEventResult")
    messages = etree.SubElement(result, f"{{{RESPONSE}}}ErrorMessage")
    etree.SubElement(messages, f"{{{ARRAY}}}string").text = "Synthetic notification"
    for name, value in {
        "IsValid": "true",
        "StatusCode": "00",
        "StatusDescription": "Processed",
        "StatusMessage": "Synthetic invoice",
        "XmlDocumentKey": "SYNTHETIC-CUFE",
        "XmlFileName": "synthetic.xml",
        "XmlBase64Bytes": b64encode(application_response).decode("ascii"),
    }.items():
        etree.SubElement(result, f"{{{RESPONSE}}}{name}").text = value
    return wrap_soap(response)


@pytest.fixture
def soap_fault() -> bytes:
    """Return a synthetic authentication fault."""
    return f'''<s:Envelope xmlns:s="{SOAP}"><s:Body><s:Fault>
      <s:Code><s:Value>s:Sender</s:Value></s:Code>
      <s:Reason><s:Text xml:lang="en">Synthetic authentication error</s:Text></s:Reason>
    </s:Fault></s:Body></s:Envelope>'''.encode()


@pytest.fixture
def mock_http(
    monkeypatch: pytest.MonkeyPatch,
    soap_response: bytes,
) -> tuple[list[httpx.Client], list[httpx.Request]]:
    clients: list[httpx.Client] = []
    requests: list[httpx.Request] = []

    def handle(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, content=soap_response)

    def create(timeout: float) -> httpx.Client:
        http = httpx.Client(transport=httpx.MockTransport(handle), timeout=timeout)
        clients.append(http)
        return http

    monkeypatch.setattr(transport, "create_http_client", create)
    return clients, requests


@pytest.fixture
def reference_notes_response(
    wrap_soap: Callable[[etree._Element], bytes],
    reference_notes_application: bytes,
) -> bytes:
    """Return synthetic reference-note metadata with distinct binary fields."""
    payload = (Path(__file__).parent / "fixtures" / "reference_notes.xml").read_bytes()
    root = etree.fromstring(payload)
    node = root.find(f"{{{WCF}}}GetReferenceNotesResult/{{{RESPONSE}}}XmlBase64Bytes")
    assert node is not None
    node.text = b64encode(reference_notes_application).decode("ascii")
    return wrap_soap(root)


@pytest.fixture
def reference_notes_application() -> bytes:
    """Return multiple synthetic notes, references and line-level reasons."""
    return (
        Path(__file__).parent / "fixtures" / "reference_notes_application.xml"
    ).read_bytes()


@pytest.fixture
def downloaded_document() -> bytes:
    """Return a synthetic UTF-8 document whose exact serialization matters."""
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\r\n'
        '<Document xmlns="urn:synthetic"><Name>Nota electrónica</Name>\n'
        "  <ID>0001</ID>\n</Document>\r\n"
    ).encode()


@pytest.fixture
def xml_document_response(
    wrap_soap: Callable[[etree._Element], bytes],
    downloaded_document: bytes,
) -> bytes:
    """Return a synthetic GetXmlByDocumentKey response with a downloaded document."""
    payload = (Path(__file__).parent / "fixtures" / "xml_document.xml").read_bytes()
    root = etree.fromstring(payload)
    namespace = "http://schemas.datacontract.org/2004/07/EventResponse"
    node = root.find(
        f"{{{WCF}}}GetXmlByDocumentKeyResult/{{{namespace}}}XmlBytesBase64"
    )
    assert node is not None
    node.text = b64encode(downloaded_document).decode("ascii")
    return wrap_soap(root)


@pytest.fixture
def document_status_response(wrap_soap: Callable[[etree._Element], bytes]) -> bytes:
    """Return document status with independent, synthetic binary payloads."""
    payload = (Path(__file__).parent / "fixtures" / "document_status.xml").read_bytes()
    return wrap_soap(etree.fromstring(payload))

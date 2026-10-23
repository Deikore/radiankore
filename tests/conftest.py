"""Synthetic certificate fixtures; no real credentials or DIAN data are used."""

from base64 import b64encode
from collections.abc import Callable
from datetime import UTC, date, datetime, time, timedelta
from pathlib import Path

import httpx
import lxml.etree as etree  # Initialize libxml2 before xmlsec's native callbacks.
import pytest
import xmlsec
from _pytest.terminal import TerminalReporter
from cryptography import x509
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.serialization import (
    BestAvailableEncryption,
    Encoding,
    pkcs12,
)
from cryptography.x509.oid import NameOID

from radiankore import DigitalCertificate
from radiankore._soap import transport
from radiankore._soap.namespaces import ACQUIRER, ARRAY, DS, RESPONSE, SOAP, WCF
from radiankore.catalogs import (
    EventType,
    IdentificationType,
    MandateChannel,
    MandateeType,
    MandateNature,
    MandateOperationType,
    MandatePower,
    MandateReferenceType,
    MandatorType,
    OrganizationType,
)
from radiankore.models.events import (
    InvoiceEventDocumentReference,
    InvoiceEventParty,
    InvoiceEventPerson,
    InvoiceResponseEvent,
    MandateAttachedDocument,
    MandateDocumentReference,
    MandateEvent,
    MandateParty,
    MandatePerson,
    MandateScope,
    MandateValidityPeriod,
    RadianEvent,
    RadianSoftware,
)
from tests.event_factories import radian_event_factory as make_radian_event_factory

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
_RADIAN_XSD = _PROJECT_ROOT / (
    "docs/references/dian/radian/toolbox/XSD/maindoc/UBL-ApplicationResponse-2.1.xsd"
)


def pytest_addoption(parser: pytest.Parser) -> None:
    """Distinguish checkout validation from intentionally source-free distributions."""
    group = parser.getgroup("reference validation")
    group.addoption(
        "--require-references",
        action="store_true",
        help="Require preserved DIAN sources and the RADIAN XSD.",
    )
    group.addoption(
        "--allow-missing-references",
        action="store_true",
        help="Allow omitted DIAN references when testing a distribution.",
    )


def pytest_sessionstart(session: pytest.Session) -> None:
    """Never silently remove reference validation from a source checkout."""
    required = session.config.getoption("--require-references")
    allowed = session.config.getoption("--allow-missing-references")
    if required and allowed:
        raise pytest.UsageError("Reference validation options are mutually exclusive.")
    paths = (
        _RADIAN_XSD,
        _PROJECT_ROOT / "docs/references/dian/radian/1.1/anexo-tecnico.pdf",
        _PROJECT_ROOT / "docs/references/dian/invoicing/1.9/anexo-tecnico.pdf",
    )
    missing = [
        str(path.relative_to(_PROJECT_ROOT)) for path in paths if not path.is_file()
    ]
    if missing and (required or not allowed):
        raise pytest.UsageError(
            "Missing required DIAN references: "
            + ", ".join(missing)
            + ". Use --allow-missing-references only for distribution tests."
        )


def pytest_terminal_summary(terminalreporter: TerminalReporter) -> None:
    """Report exactly when schema checks are absent while signature tests still run."""
    if not _RADIAN_XSD.exists():
        terminalreporter.section("Reference validation")
        terminalreporter.write_line(
            "RADIAN XSD unavailable: schema checks were omitted explicitly; "
            "signature and byte-preservation checks remain enabled."
        )


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
        # Older libxml2 schema validators reject very large xs:integer values.
        .serial_number(1234567890123456789)
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


@pytest.fixture
def mandate_event() -> "MandateEvent":
    """Return a fully synthetic special mandate with a common general scope."""
    person = MandatePerson(
        identification_number="100000001",
        identification_type=IdentificationType.CITIZENSHIP_CARD,
        first_name="Synthetic",
        family_name="Representative",
        job_title="Representante Legal",
    )
    return MandateEvent(
        operation_type=MandateOperationType.GENERAL_LIMITED_TIME,
        nature=MandateNature.SPECIAL,
        reference_type=MandateReferenceType.ONE,
        event_number="TEST-1",
        issue_date=date(2026, 10, 22),
        issue_time=time(10, 30),
        notes=(
            "Declaración sintética: el representante confiere las facultades indicadas "
            "en el contrato de prueba; no constituye un mandato real.",
        ),
        sender_party=MandateParty(
            name="Synthetic Mandator",
            tax_number="900000001",
            identification_type=IdentificationType.NIT,
            verification_digit="1",
            role=MandatorType.INVOICE_ISSUER,
            representative=person,
        ),
        mandatee_party=MandateParty(
            name="Synthetic Mandatee",
            tax_number="900000002",
            identification_type=IdentificationType.NIT,
            verification_digit="2",
            role=MandateeType.ELECTRONIC_NEGOTIATION_SYSTEM,
            representative=person,
        ),
        effective_date=date(2026, 10, 22),
        document_references=(
            MandateDocumentReference(document_number="FE1", uuid="a" * 96),
        ),
        validity_period=MandateValidityPeriod(
            start_date=date(2026, 10, 22), end_date=date(2026, 12, 31)
        ),
        scope=MandateScope(
            powers=(
                (
                    MandatePower.GENERAL_DOCUMENT,
                    MandateChannel.ELECTRONIC_NEGOTIATION_SYSTEM,
                ),
            )
        ),
        attached_contract=MandateAttachedDocument(
            document_id="CONTRACT-1",
            embedded_bytes=b"%PDF-1.7\nSynthetic contract.\n%%EOF",
        ),
        acceptance=True,
    )


@pytest.fixture
def radian_software() -> "RadianSoftware":
    """Software data is fictitious and has never been registered with DIAN."""
    return RadianSoftware(
        software_id="00000000-0000-4000-8000-000000000001",
        pin="synthetic-pin",
        provider_tax_number="900000002",
        provider_verification_digit="2",
        signer_role="thirdparty",
    )


@pytest.fixture
def invoice_event_factory() -> Callable[[EventType], InvoiceResponseEvent]:
    """Build synthetic invoice events with event-specific required inputs."""

    def make(code: EventType) -> InvoiceResponseEvent:
        sender = InvoiceEventParty(
            name="Synthetic Sender",
            tax_number="900000001",
            identification_type=IdentificationType.NIT,
            verification_digit="1",
            organization_type=OrganizationType.LEGAL_PERSON,
        )
        receiver = InvoiceEventParty(
            name="Synthetic Receiver",
            tax_number="100000002",
            identification_type=IdentificationType.CITIZENSHIP_CARD,
            organization_type=OrganizationType.NATURAL_PERSON,
        )
        person = InvoiceEventPerson(
            identification_number="100000003",
            identification_type=IdentificationType.CITIZENSHIP_CARD,
            first_name="Synthetic",
            family_name="Recipient",
        )
        from radiankore.catalogs import InvoiceClaimReason

        return InvoiceResponseEvent(
            code=code,
            event_number="TEST-INVOICE-1",
            issue_date=date(2026, 10, 22),
            issue_time=time(10, 30),
            sender_party=sender,
            receiver_party=None if code is EventType.TACIT_ACCEPTANCE else receiver,
            document_reference=InvoiceEventDocumentReference(
                document_number="FE-TEST-1",
                uuid="a" * 96,
            ),
            issuer_person=person
            if code
            in (
                EventType.INVOICE_ACKNOWLEDGEMENT,
                EventType.GOODS_OR_SERVICES_RECEIPT,
            )
            else None,
            claim_reason=InvoiceClaimReason.DOCUMENT_INCONSISTENCIES
            if code is EventType.INVOICE_CLAIM
            else None,
            notes=(
                "Declaración sintética; no constituye aceptación de una factura real.",
            )
            if code is EventType.TACIT_ACCEPTANCE
            else (),
        )

    return make


@pytest.fixture
def verify_event_signature() -> Callable[[bytes, DigitalCertificate], None]:
    """Provide independent verification for serialized UBL and SOAP signatures."""

    def verify_signature(xml: bytes, certificate: DigitalCertificate) -> None:
        """Verify signed, serialized bytes using only the public certificate."""
        root = etree.fromstring(xml)
        xmlsec.tree.add_ids(root, ["Id"])
        signature = root.find(f".//{{{DS}}}Signature")
        assert signature is not None
        ctx = xmlsec.SignatureContext()
        ctx.key = xmlsec.Key.from_memory(
            certificate.certificate.public_bytes(Encoding.PEM),
            xmlsec.constants.KeyDataFormatCertPem,
            None,
        )
        ctx.verify(signature)

    return verify_signature


@pytest.fixture
def radian_event_factory() -> Callable[[str], RadianEvent]:
    """Provide the shared operation-matrix factory without duplicating profile data."""
    return make_radian_event_factory()


@pytest.fixture(scope="session")
def radian_schema() -> etree.XMLSchema | None:
    return (
        etree.XMLSchema(etree.parse(str(_RADIAN_XSD))) if _RADIAN_XSD.exists() else None
    )

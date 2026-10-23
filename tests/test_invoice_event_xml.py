"""FE 1.9 serialized contracts, CUDE vectors and independent signature verification."""

from collections.abc import Callable
from dataclasses import replace
from datetime import UTC, date, time
from hashlib import sha384
from pathlib import Path
from zipfile import ZipFile

import pytest
import xmlsec
from lxml import etree

from radiankore import DigitalCertificate, Environment
from radiankore._soap.events import (
    build_invoice_application_response,
    compute_application_response_cude,
    sign_application_response,
)
from radiankore._soap.namespaces import CAC, CBC, STS
from radiankore.catalogs import (
    DocumentType,
    EventType,
    InvoiceClaimReason,
    OrganizationType,
    PartyTaxScheme,
)
from radiankore.models.events import InvoiceResponseEvent, RadianSoftware


@pytest.fixture(scope="module")
def invoice_schema() -> etree.XMLSchema | None:
    path = Path(__file__).resolve().parents[1] / (
        "docs/references/dian/radian/toolbox/XSD/maindoc/"
        "UBL-ApplicationResponse-2.1.xsd"
    )
    if not path.exists():
        return None
    return etree.XMLSchema(etree.parse(str(path)))


@pytest.mark.parametrize("code", ["030", "031", "032", "033", "034"])
@pytest.mark.parametrize("environment", list(Environment))
def test_all_invoice_event_xml_contracts(
    invoice_event_factory: Callable[[EventType], InvoiceResponseEvent],
    radian_software: RadianSoftware,
    digital_certificate: DigitalCertificate,
    invoice_schema: etree.XMLSchema | None,
    verify_event_signature: Callable[[bytes, DigitalCertificate], None],
    code: str,
    environment: Environment,
) -> None:
    event = invoice_event_factory(EventType(code))
    root = build_invoice_application_response(
        event,
        software=radian_software,
        environment=environment,
    )
    sign_application_response(
        root,
        certificate=digital_certificate,
        signer_role=radian_software.signer_role,
    )
    raw = etree.tostring(root, encoding="UTF-8", xml_declaration=True)
    parsed = etree.fromstring(raw)
    if invoice_schema is not None:
        invoice_schema.assertValid(parsed)
    verify_event_signature(raw, digital_certificate)
    assert parsed.findtext(f"{{{CBC}}}CustomizationID") == "1"
    assert parsed.findtext(f"{{{CBC}}}ProfileID") == (
        "DIAN 2.1: ApplicationResponse de Factura Electrónica de Venta"
    )
    assert (
        parsed.findtext(f"{{{CBC}}}ProfileExecutionID")
        == environment.profile_execution_id
    )
    uuid = parsed.find(f"{{{CBC}}}UUID")
    assert uuid is not None
    assert {str(k): str(v) for k, v in uuid.attrib.items()} == {
        "schemeID": environment.profile_execution_id,
        "schemeName": "CUDE-SHA384",
    }
    responses = parsed.findall(f"{{{CAC}}}DocumentResponse")
    assert len(responses) == 1
    response = responses[0]
    response_code = response.find(f"{{{CAC}}}Response/{{{CBC}}}ResponseCode")
    assert response_code is not None and response_code.text == code
    assert {str(k): str(v) for k, v in response_code.attrib.items()} == (
        {"listID": "01", "name": "Documento con inconsistencias"}
        if code == "031"
        else {}
    )
    assert (response.find(f"{{{CAC}}}IssuerParty/{{{CAC}}}Person") is not None) == (
        code in ("030", "032")
    )
    assert response.find(f"{{{CAC}}}LineResponse") is None
    ref = response.find(f"{{{CAC}}}DocumentReference")
    assert ref is not None
    assert ref.findtext(f"{{{CBC}}}ID") == "FE-TEST-1"
    assert ref.findtext(f"{{{CBC}}}UUID") == "a" * 96
    assert ref.findtext(f"{{{CBC}}}DocumentTypeCode") == "01"
    recipient = "800197268" if code == "034" else "100000002"
    assert (
        parsed.findtext(
            f"{{{CAC}}}ReceiverParty/{{{CAC}}}PartyTaxScheme/{{{CBC}}}CompanyID"
        )
        == recipient
    )
    expected = sha384(
        (
            f"TEST-INVOICE-12026-10-2210:30:00-05:00900000001{recipient}{code}"
            "FE-TEST-101synthetic-pin"
        ).encode()
    ).hexdigest()
    assert uuid.text == expected
    host = (
        "catalogo-vpfe.dian.gov.co"
        if environment is Environment.PRODUCTION
        else ("catalogo-vpfe-hab.dian.gov.co")
    )
    assert parsed.findtext(f".//{{{STS}}}QRCode") == (
        f"https://{host}/document/searchqr?documentkey=" + "a" * 96
    )
    assert (
        parsed.findtext(f".//{{{STS}}}SoftwareSecurityCode")
        == sha384(
            (
                radian_software.software_id + radian_software.pin + event.event_number
            ).encode()
        ).hexdigest()
    )
    # Mutation of a serialized business field must invalidate the signature.
    event_id = parsed.find(f"{{{CBC}}}ID")
    assert event_id is not None
    event_id.text = "tampered"
    with pytest.raises(xmlsec.VerificationError):
        verify_event_signature(etree.tostring(parsed), digital_certificate)


def test_official_cude_vector() -> None:
    assert compute_application_response_cude(
        "1",
        date(2019, 4, 30),
        time(19, 48, 50),
        "99998888",
        "11111",
        document_number="FE123",
        receiver_nit="800197268",
        response_code="030",
    ) == (
        "0d91ba25b01f5e7dbda870a11b274501d3a62a73e91932c473c86c93f12a142a2"
        "ac45876efcde3e679024a01c0be41f9"
    )


@pytest.mark.parametrize("reason", list(InvoiceClaimReason))
def test_all_claim_reasons(
    invoice_event_factory: Callable[[EventType], InvoiceResponseEvent],
    radian_software: RadianSoftware,
    reason: InvoiceClaimReason,
) -> None:
    event = replace(invoice_event_factory(EventType.INVOICE_CLAIM), claim_reason=reason)
    root = build_invoice_application_response(
        event,
        software=radian_software,
        environment=Environment.PRODUCTION,
    )
    code = root.find(
        f"{{{CAC}}}DocumentResponse/{{{CAC}}}Response/{{{CBC}}}ResponseCode"
    )
    assert code is not None and code.get("listID") == reason.value
    assert code.get("name") == reason.label


@pytest.mark.parametrize("organization", list(OrganizationType))
@pytest.mark.parametrize("tax", list(PartyTaxScheme))
def test_parties_use_shared_catalogs(
    invoice_event_factory: Callable[[EventType], InvoiceResponseEvent],
    radian_software: RadianSoftware,
    organization: OrganizationType,
    tax: PartyTaxScheme,
) -> None:
    event = invoice_event_factory(EventType.EXPRESS_ACCEPTANCE)
    event = replace(
        event,
        sender_party=replace(
            event.sender_party,
            organization_type=organization,
            tax_scheme=tax,
        ),
    )
    root = build_invoice_application_response(
        event,
        software=radian_software,
        environment=Environment.PRODUCTION,
    )
    party = root.find(f"{{{CAC}}}SenderParty/{{{CAC}}}PartyTaxScheme")
    assert party is not None
    company = party.find(f"{{{CBC}}}CompanyID")
    assert company is not None
    assert company.get("schemeVersionID") == organization.value
    assert party.findtext(f"{{{CAC}}}TaxScheme/{{{CBC}}}ID") == tax.value
    assert party.findtext(f"{{{CAC}}}TaxScheme/{{{CBC}}}Name") == tax.label


@pytest.mark.parametrize(
    "document_type",
    [
        DocumentType.SALES_INVOICE,
        DocumentType.EXPORT_INVOICE,
        DocumentType.PAPER_INVOICE_TRANSMISSION,
        DocumentType.DIAN_CONTINGENCY_INVOICE,
    ],
)
def test_invoice_reference_types_and_notes(
    invoice_event_factory: Callable[[EventType], InvoiceResponseEvent],
    radian_software: RadianSoftware,
    document_type: DocumentType,
) -> None:
    event = invoice_event_factory(EventType.EXPRESS_ACCEPTANCE)
    event = replace(
        event,
        document_reference=replace(
            event.document_reference,
            document_type=document_type,
        ),
        notes=("First & <synthetic>", "Repeated", "Repeated"),
    )
    root = build_invoice_application_response(
        event,
        software=radian_software,
        environment=Environment.PRODUCTION,
    )
    assert [n.text for n in root.findall(f"{{{CBC}}}Note")] == list(event.notes)
    assert (
        root.findtext(
            f"{{{CAC}}}DocumentResponse/{{{CAC}}}DocumentReference/{{{CBC}}}DocumentTypeCode"
        )
        == document_type.value
    )


def test_utc_date_conversion_and_cude_agree(
    invoice_event_factory: Callable[[EventType], InvoiceResponseEvent],
    radian_software: RadianSoftware,
) -> None:
    event = replace(
        invoice_event_factory(EventType.EXPRESS_ACCEPTANCE),
        issue_date=date(2026, 10, 23),
        issue_time=time(2, 30, 0, 123, tzinfo=UTC),
    )
    root = build_invoice_application_response(
        event,
        software=radian_software,
        environment=Environment.PRODUCTION,
    )
    assert root.findtext(f"{{{CBC}}}IssueDate") == "2026-10-22"
    assert root.findtext(f"{{{CBC}}}IssueTime") == "21:30:00-05:00"
    expected = sha384(
        b"TEST-INVOICE-12026-10-2221:30:00-05:00900000001100000002033"
        b"FE-TEST-101synthetic-pin"
    ).hexdigest()
    assert root.findtext(f"{{{CBC}}}UUID") == expected


def test_claim_catalog_matches_official_table() -> None:
    """Check preserved XLSX cells without adding spreadsheet runtime dependencies."""
    path = Path(__file__).resolve().parents[1] / (
        "docs/references/dian/invoicing/1.9/13.3.12-Concepto-de-Reclamo.xlsx"
    )
    if not path.exists():
        pytest.skip("Original tables are excluded from distributions.")
    ns = {"s": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
    with ZipFile(path) as archive:
        shared = etree.fromstring(archive.read("xl/sharedStrings.xml"))
        strings = [
            "".join(str(t) for t in e.itertext()) for e in shared.findall("s:si", ns)
        ]
        sheet = etree.fromstring(archive.read("xl/worksheets/sheet1.xml"))
    labels = {}
    for row in sheet.findall(".//s:row", ns):
        values = []
        for cell in row.findall("s:c", ns):
            value = cell.findtext("s:v", namespaces=ns)
            if value is not None:
                values.append(strings[int(value)] if cell.get("t") == "s" else value)
        if len(values) == 2 and values[0] in {"01", "02", "03", "04"}:
            labels[values[0]] = values[1].strip()
    assert {m.value: m.label for m in InvoiceClaimReason} == labels

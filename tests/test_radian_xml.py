"""RADIAN operation matrix, serialized signatures and independent CUDE assertions."""

from collections.abc import Callable
from dataclasses import replace
from datetime import date, time
from hashlib import sha384
from io import BytesIO
from pathlib import Path
from zipfile import ZipFile

import pytest
from lxml import etree

from radiankore import DianClient, DigitalCertificate, Environment
from radiankore._soap.events.cude import compute_blank_endorsement_cude
from radiankore._soap.namespaces import AR, CAC, CBC, DS, EXT, STS
from radiankore.catalogs import PaymentRestriction, RadianOperationType
from radiankore.models.events import (
    EconomicRightsPaymentEvent,
    EndorsementEvent,
    InvoicePaymentEvent,
    InvoiceResponseEvent,
    MandateEvent,
    MandateTerminationEvent,
    RadianEvent,
    RadianRegistrationEvent,
    RadianSoftware,
)

VARIANTS = [op.value for op in RadianOperationType] + [
    "371-blank",
    "372-blank",
    "038-blank",
    "039-blank",
]
NS = {"ar": AR, "cac": CAC, "cbc": CBC, "sts": STS}


def xpath(root: etree._Element, expression: str) -> list[object]:
    """Narrow node-set XPath results without weakening the library's strict types."""
    result = root.xpath(expression, namespaces=NS)
    assert isinstance(result, list)
    return list[object](result)


@pytest.mark.parametrize("variant", VARIANTS)
@pytest.mark.parametrize("environment", list(Environment))
def test_all_operations_and_blank_variants(
    radian_event_factory: Callable[[str], RadianEvent],
    encrypted_pfx_path: Path,
    radian_software: RadianSoftware,
    digital_certificate: DigitalCertificate,
    verify_event_signature: Callable[[bytes, DigitalCertificate], None],
    radian_schema: etree.XMLSchema | None,
    variant: str,
    environment: Environment,
) -> None:
    event = radian_event_factory(variant)
    assert not isinstance(event, (InvoiceResponseEvent, MandateEvent))
    client = DianClient(
        encrypted_pfx_path, password="test-password", environment=environment
    )
    prepared = client.prepare_radian_event(event=event, software=radian_software)
    root = etree.fromstring(prepared.xml_bytes)
    if radian_schema is not None:
        radian_schema.assertValid(root)
    verify_event_signature(prepared.xml_bytes, digital_certificate)
    # Applicable common Schematron checks AA03/AA04, DA16/DA22-27 and DC01a.
    extensions = root.find(f"{{{EXT}}}UBLExtensions")
    assert extensions is not None
    assert len(extensions.findall(f".//{{{STS}}}DianExtensions")) == 1
    assert len(extensions.findall(f".//{{{DS}}}Signature")) == 1
    for tag in (
        "SoftwareProvider",
        "SoftwareSecurityCode",
        "AuthorizationProvider",
        "QRCode",
    ):
        assert extensions.find(f".//{{{STS}}}{tag}") is not None
    assert (
        root.findtext(f".//{{{STS}}}SoftwareSecurityCode")
        == sha384(
            (
                radian_software.software_id
                + radian_software.pin
                + event.header.event_number
            ).encode()
        ).hexdigest()
    )
    assert prepared.code is event.code
    assert root.findtext(f"{{{CBC}}}CustomizationID") == event.operation_type.value
    assert root.findtext(f"{{{CBC}}}ProfileID") == (
        "DIAN 2.1: ApplicationResponse de la Factura Electrónica de Venta"
    )
    assert (
        root.findtext(f"{{{CBC}}}ProfileExecutionID")
        == environment.profile_execution_id
    )
    assert root.findtext(f"{{{CBC}}}IssueDate") == "2026-10-22"
    assert root.findtext(f"{{{CBC}}}IssueTime") == "10:30:00-05:00"
    assert [e.text for e in root.findall(f"{{{CBC}}}Note")] == list(event.header.notes)
    uuid = root.find(f"{{{CBC}}}UUID")
    assert uuid is not None and uuid.get("schemeID") == environment.profile_execution_id
    assert uuid.get("schemeName") == "CUDE-SHA384" and uuid.text == prepared.cude
    code = root.find(
        f"{{{CAC}}}DocumentResponse/{{{CAC}}}Response/{{{CBC}}}ResponseCode"
    )
    assert code is not None and code.text == event.code.value
    if isinstance(event, EndorsementEvent):
        assert code.get("listID") == ("2" if variant.endswith("-blank") else "1")
    elif isinstance(event, (InvoicePaymentEvent, EconomicRightsPaymentEvent)):
        assert code.get("listID") == "1"  # Restriction, not partial/full payment.
    else:
        assert code.get("listID") is None
    reference = root.find(f"{{{CAC}}}DocumentResponse/{{{CAC}}}DocumentReference")
    assert reference is not None
    reference_uuid = reference.find(f"{{{CBC}}}UUID")
    assert reference_uuid is not None and reference_uuid.text == event.reference.uuid
    previous_event = event.code.value in ("040", "044", "042")
    assert reference.findtext(f"{{{CBC}}}DocumentTypeCode") == (
        "96" if previous_event else "01"
    )
    assert reference_uuid.get("schemeName") == (
        "CUDE-SHA384" if previous_event else "CUFE-SHA384"
    )
    sender_numbers = xpath(
        root, "cac:SenderParty/cac:PartyTaxScheme/cbc:CompanyID/text()"
    )
    receiver_numbers = xpath(
        root, "cac:ReceiverParty/cac:PartyTaxScheme/cbc:CompanyID/text()"
    )
    assert receiver_numbers
    blank = variant.endswith("-blank")
    if blank:
        assert sender_numbers == []
        assert not xpath(root, "cac:SenderParty/cac:PartyLegalEntity/cbc:CompanyID")
    else:
        assert sender_numbers
    # XPath selects the first identity; extra parties are not concatenated.
    composition = (
        "RADIAN-TEST-12026-10-2210:30:00-05:00"
        + ("" if blank else str(sender_numbers[0]))
        + str(receiver_numbers[0])
        + event.code.value
        + ("2" if blank else "")
        + event.reference.document_number
        + ("96" if previous_event else "01")
        + "synthetic-pin"
    )
    assert prepared.cude == sha384(composition.encode()).hexdigest()
    host = (
        "catalogo-vpfe.dian.gov.co"
        if environment is Environment.PRODUCTION
        else "catalogo-vpfe-hab.dian.gov.co"
    )
    assert root.findtext(f".//{{{STS}}}QRCode") == (
        f"https://{host}/document/searchqr?documentkey={event.reference.uuid}"
    )
    with ZipFile(BytesIO(prepared.zip_bytes)) as archive:
        assert archive.namelist() == [f"ar_{prepared.cude}.xml"]
        assert archive.read(archive.namelist()[0]) == prepared.xml_bytes
    if isinstance(event, RadianRegistrationEvent):
        buyer = root.find(f"{{{CAC}}}DocumentResponse/{{{CAC}}}IssuerParty")
        assert (buyer is not None) == (variant in ("362", "364"))
        values = xpath(root, ".//ar:ConstanciadePagos/ar:Value/text()")
        assert values == ["100000.00", "25000.00", "75000.00"]
    if isinstance(event, MandateTerminationEvent):
        assert len(xpath(root, "cac:SenderParty/cac:Person")) == 1
    if isinstance(event, EndorsementEvent):
        assert len(xpath(root, "cac:SenderParty/cac:PartyLegalEntity")) == 2
        assert len(xpath(root, "cac:ReceiverParty/cac:PartyLegalEntity")) == 2
        assert xpath(
            root, "cac:ReceiverParty/cac:PartyTaxScheme/cbc:CompanyID/text()"
        ) == ["900000002", "900000005"]
        if event.code.value in ("038", "039"):
            assert xpath(root, ".//ar:InformacionNegociacion/ar:Name/text()") == [
                "ValorTotalEndoso"
            ]


def test_official_blank_cude_vector() -> None:
    assert compute_blank_endorsement_cude(
        "1",
        date(2019, 4, 30),
        time(19, 48, 50),
        "800197268",
        "030",
        "FE123",
        "11111",
    ) == (
        "314ca930d7b4be11c610bb7a398b94e8ef1e03d39e2394248275816814864d282fb9caa2"
        "ed9e2dfe5b711085c9fb1e03"
    )


@pytest.mark.parametrize("operation", ["451", "452"])
@pytest.mark.parametrize("restriction", list(PaymentRestriction))
def test_payment_operation_and_restriction_are_independent(
    radian_event_factory: Callable[[str], RadianEvent],
    encrypted_pfx_path: Path,
    radian_software: RadianSoftware,
    operation: str,
    restriction: PaymentRestriction,
) -> None:
    event = radian_event_factory(operation)
    assert isinstance(event, InvoicePaymentEvent)
    event = replace(event, restriction=restriction)
    client = DianClient(encrypted_pfx_path, password="test-password")
    prepared = client.prepare_radian_event(event=event, software=radian_software)
    root = etree.fromstring(prepared.xml_bytes)
    assert root.findtext(f"{{{CBC}}}CustomizationID") == operation
    code = root.find(
        f"{{{CAC}}}DocumentResponse/{{{CAC}}}Response/{{{CBC}}}ResponseCode"
    )
    assert code is not None and code.get("listID") == restriction.value


def test_optional_blank_identity_and_optional_guarantee_fields(
    radian_event_factory: Callable[[str], RadianEvent],
    encrypted_pfx_path: Path,
    radian_software: RadianSoftware,
    radian_schema: etree.XMLSchema | None,
) -> None:
    event = radian_event_factory("038-blank")
    assert isinstance(event, EndorsementEvent)
    assert event.endorsees[0].party is not None
    event = replace(
        event,
        debtors=(),
        reference=replace(event.reference, due_date=None),
        endorsees=(
            replace(
                event.endorsees[0], party=replace(event.endorsees[0].party, name=None)
            ),
        ),
    )
    client = DianClient(encrypted_pfx_path, password="test-password")
    root = etree.fromstring(
        client.prepare_radian_event(event=event, software=radian_software).xml_bytes
    )
    if radian_schema is not None:
        radian_schema.assertValid(root)
    assert not xpath(root, ".//cac:ValidityPeriod")
    assert not xpath(root, "cac:ReceiverParty//cbc:RegistrationName")
    assert xpath(root, "cac:ReceiverParty//cbc:CompanyID/text()") == [
        "900000002",
        "900000002",
    ]

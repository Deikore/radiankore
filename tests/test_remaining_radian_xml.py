"""Profile-specific XML, signed evidence and source-backed shapes for final events."""

from base64 import b64decode
from collections.abc import Callable
from dataclasses import replace
from decimal import Decimal
from pathlib import Path

import pytest
from lxml import etree

from radiankore import DianClient, DigitalCertificate
from radiankore._soap.events.radian_builder import build_radian_application_response
from radiankore._soap.namespaces import AR, CAC, CBC
from radiankore.catalogs import AcceptanceFailureType, PaymentRestriction
from radiankore.environment import Environment
from radiankore.models.events import (
    CirculationRestrictionEvent,
    CirculationRestrictionTerminationEvent,
    EconomicRightsPaymentEvent,
    GuaranteeBeneficiary,
    GuaranteeEvent,
    ProtestEvent,
    RadianEvent,
    RadianSoftware,
)

NS = {"ar": AR, "cac": CAC, "cbc": CBC}


@pytest.mark.parametrize("variant", ["411", "412", "421", "422", "481", "482"])
def test_pdf_bytes_metadata_and_issuer_are_preserved(
    radian_event_factory: Callable[[str], RadianEvent],
    encrypted_pfx_path: Path,
    radian_software: RadianSoftware,
    digital_certificate: DigitalCertificate,
    verify_event_signature: Callable[[bytes, DigitalCertificate], None],
    radian_schema: etree.XMLSchema | None,
    variant: str,
) -> None:
    event = radian_event_factory(variant)
    assert isinstance(
        event,
        (
            CirculationRestrictionEvent,
            CirculationRestrictionTerminationEvent,
            ProtestEvent,
        ),
    )
    protest = isinstance(event, ProtestEvent)
    attachment = (
        event.act.attachment if isinstance(event, ProtestEvent) else event.attachment
    )
    client = DianClient(encrypted_pfx_path, password="test-password")
    prepared = client.prepare_radian_event(event=event, software=radian_software)
    root = etree.fromstring(prepared.xml_bytes)
    if radian_schema is not None:
        radian_schema.assertValid(root)
    verify_event_signature(prepared.xml_bytes, digital_certificate)
    base = (
        "cac:DocumentResponse/cac:LineResponse/cac:LineReference/cac:DocumentReference"
        if protest
        else "cac:DocumentResponse/cac:DocumentReference"
    )
    node = root.find(base + "/cac:Attachment/cbc:EmbeddedDocumentBinaryObject", NS)
    assert node is not None and node.text is not None
    assert b64decode(node.text, validate=True) == attachment.content_bytes
    expected_metadata = {
        "format": "Archivo. PDF",
        "mimeCode": "PDF",
        "encodingCode": "base 64, UTF-8" if protest else "base64, UTF-8",
        "characterSetCode": "UTF-8",
        "filename": attachment.filename,
    }
    assert len(node.attrib) == len(expected_metadata)
    assert all(node.get(name) == value for name, value in expected_metadata.items())
    if protest:
        assert isinstance(event, ProtestEvent)
        assert root.findtext(base + "/cbc:ID", namespaces=NS) == event.act.notary_number
        assert (
            root.findtext(
                "cac:DocumentResponse/cac:LineResponse/cac:Response/cbc:EffectiveDate",
                namespaces=NS,
            )
            == event.act.effective_date.isoformat()
        )
        assert (
            root.findtext(
                base + "/cac:IssuerParty/cac:Person/cbc:JobTitle", namespaces=NS
            )
            == "Notario"
        )
        customization = root.find("cbc:CustomizationID", NS)
        assert customization is not None
        assert customization.get("schemeID") == ("1" if variant == "481" else None)
        assert len(root.findall(".//ar:InformacionProtesto/ar:Value", NS)) == (
            3 if variant == "481" else 1
        )
    else:
        # The 041 profile does not carry maturity even if the common reference has it.
        assert root.find(base + "/cac:ValidityPeriod", NS) is None
        assert len(root.findall(base + "/cac:IssuerParty/cac:PartyTaxScheme", NS)) == 2
        assert [
            n.text
            for n in root.findall(
                base + "/cac:IssuerParty/cac:PartyTaxScheme/cbc:CompanyID", NS
            )
        ] == ["900000003", "900000003"]


@pytest.mark.parametrize(
    "amount,beneficiaries",
    [("0.00", 0), ("30000.00", 0), ("100000.00", 2), ("1" * 18, 1)],
)
def test_guarantee_variants_have_no_empty_party_placeholders(
    radian_event_factory: Callable[[str], RadianEvent],
    radian_software: RadianSoftware,
    radian_schema: etree.XMLSchema | None,
    amount: str,
    beneficiaries: int,
) -> None:
    event = radian_event_factory("035")
    assert isinstance(event, GuaranteeEvent)
    first = event.guarantors[0]
    beneficiary = GuaranteeBeneficiary(
        party=first.party, amount=Decimal("50000.00") if beneficiaries > 1 else None
    )
    event = replace(
        event,
        guarantors=(replace(first, amount=Decimal(amount)),),
        beneficiaries=(beneficiary,) * beneficiaries,
    )
    root = build_radian_application_response(
        event, software=radian_software, environment=Environment.PRODUCTION
    )
    if radian_schema is not None:
        radian_schema.assertValid(root)
    assert (
        root.findtext(
            "cac:SenderParty/cac:PartyLegalEntity/cbc:CorporateStockAmount",
            namespaces=NS,
        )
        == amount
    )
    assert (
        len(
            root.findall(
                "cac:DocumentResponse/cac:IssuerParty/cac:PartyLegalEntity", NS
            )
        )
        == beneficiaries
    )
    assert (
        root.find("cac:DocumentResponse/cac:DocumentReference/cac:ValidityPeriod", NS)
        is None
    )


def test_guarantee_amount_preserves_25_digit_precision(
    radian_event_factory: Callable[[str], RadianEvent],
    radian_software: RadianSoftware,
) -> None:
    """Check serialization beyond older libxml2's XSD decimal precision limit."""
    event = radian_event_factory("035")
    assert isinstance(event, GuaranteeEvent)
    amount = "1" * 25
    event = replace(
        event,
        guarantors=(replace(event.guarantors[0], amount=Decimal(amount)),),
    )
    root = build_radian_application_response(
        event, software=radian_software, environment=Environment.PRODUCTION
    )
    assert (
        root.findtext(
            "cac:SenderParty/cac:PartyLegalEntity/cbc:CorporateStockAmount",
            namespaces=NS,
        )
        == amount
    )


@pytest.mark.parametrize("variant", ["511", "512"])
@pytest.mark.parametrize("restriction", list(PaymentRestriction))
def test_rights_payment_does_not_derive_restriction_from_payment_kind(
    radian_event_factory: Callable[[str], RadianEvent],
    radian_software: RadianSoftware,
    variant: str,
    restriction: PaymentRestriction,
) -> None:
    event = radian_event_factory(variant)
    assert isinstance(event, EconomicRightsPaymentEvent)
    root = build_radian_application_response(
        replace(event, restriction=restriction),
        software=radian_software,
        environment=Environment.PRODUCTION,
    )
    code = root.find("cac:DocumentResponse/cac:Response/cbc:ResponseCode", NS)
    assert code is not None and code.get("listID") == restriction.value
    assert root.findtext("cbc:CustomizationID", namespaces=NS) == variant
    assert len(root.findall("cac:SenderParty/cac:PartyLegalEntity", NS)) == 1


def test_total_acceptance_failure_has_numeric_values(
    radian_event_factory: Callable[[str], RadianEvent],
    radian_software: RadianSoftware,
) -> None:
    event = radian_event_factory("481")
    assert isinstance(event, ProtestEvent)
    event = replace(
        event,
        acceptance_failure=AcceptanceFailureType.TOTAL,
        accepted_value=Decimal("0.00"),
        pending_value=event.title_value,
    )
    root = build_radian_application_response(
        event, software=radian_software, environment=Environment.PRODUCTION
    )
    node = root.find("cbc:CustomizationID", NS)
    assert node is not None and node.get("schemeID") == "2"
    assert [n.text for n in root.findall(".//ar:InformacionProtesto/ar:Value", NS)] == [
        "100000.00",
        "0.00",
        "100000.00",
    ]


def test_embedded_pdf_is_subject_to_signed_size_limit(
    radian_event_factory: Callable[[str], RadianEvent],
    encrypted_pfx_path: Path,
    radian_software: RadianSoftware,
) -> None:
    event = radian_event_factory("411")
    assert isinstance(event, CirculationRestrictionEvent)
    client = DianClient(encrypted_pfx_path, password="test-password")
    event = replace(
        event,
        attachment=replace(
            event.attachment, content_bytes=b"%PDF-1.7\n" + b"x" * 375000
        ),
    )
    with pytest.raises(ValueError, match="500,000"):
        client.prepare_radian_event(event=event, software=radian_software)


def test_preserved_samples_confirm_extension_and_reference_shapes(
    radian_event_factory: Callable[[str], RadianEvent],
    radian_software: RadianSoftware,
) -> None:
    folder = (
        Path(__file__).resolve().parents[1]
        / "docs/references/dian/radian/toolbox/Ejemplificaciones/XMLs de ejemplo"
    )
    if not folder.exists():
        pytest.skip("Reference documents are excluded from distributions.")
    count = 0
    for path in folder.rglob("*"):
        if path.suffix.lower() != ".xml" or path.parent.name[:3] not in {
            "035",
            "041",
            "042",
            "048",
            "049",
            "050",
            "051",
        }:
            continue
        original = etree.parse(str(path)).getroot()
        operation = original.findtext("cbc:CustomizationID", namespaces=NS)
        assert operation is not None
        event = radian_event_factory(operation)
        built = build_radian_application_response(
            event, software=radian_software, environment=Environment.HABILITATION
        )
        assert [
            n.text
            for n in original.findall(".//ar:CustomTagGeneral/*/ar:Name", NS)
            if not (
                operation == "482" and n.text in {"ValorAceptado", "ValorPendiente"}
            )
        ] == [n.text for n in built.findall(".//ar:CustomTagGeneral/*/ar:Name", NS)]
        original_ref = original.find("cac:DocumentResponse/cac:DocumentReference", NS)
        built_ref = built.find("cac:DocumentResponse/cac:DocumentReference", NS)
        assert original_ref is not None and built_ref is not None
        for name in ("UUID", "DocumentTypeCode"):
            a, b = (
                original_ref.find(f"cbc:{name}", NS),
                built_ref.find(f"cbc:{name}", NS),
            )
            assert a is not None and b is not None
            assert a.get("schemeName") == b.get("schemeName")
            if name == "DocumentTypeCode":
                assert a.text == b.text
        count += 1
    assert count == 16

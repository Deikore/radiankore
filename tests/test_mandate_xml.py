"""Serialized mandate contracts, XSD structure and independent signature checks."""

from dataclasses import replace
from datetime import date, time, timedelta, timezone
from hashlib import sha384
from pathlib import Path

import pytest
import xmlsec
from cryptography.hazmat.primitives.serialization import Encoding
from lxml import etree

from radiankore import DigitalCertificate, Environment
from radiankore._soap.events import (
    build_mandate_application_response,
    compute_mandate_cude,
    sign_application_response,
)
from radiankore._soap.namespaces import CAC, CBC, DS, STS, XADES
from radiankore.catalogs import (
    MandateChannel,
    MandateNature,
    MandateOperationType,
    MandatePower,
    MandateReferenceType,
)
from radiankore.models.events import (
    MandateAttachedDocument,
    MandateDocumentReference,
    MandateEvent,
    MandateScope,
    MandateValidityPeriod,
    RadianSoftware,
)


@pytest.fixture(scope="module")
def ubl_schema() -> etree.XMLSchema:
    root = Path(__file__).resolve().parents[1]
    paths = list(
        (root / "docs/references/dian/radian/toolbox/XSD").rglob(
            "UBL-ApplicationResponse-2.1.xsd"
        )
    )
    if not paths:
        pytest.skip("Original DIAN XSDs are only available in a repository checkout.")
    return etree.XMLSchema(etree.parse(str(paths[0])))


def verify(xml: bytes, certificate: DigitalCertificate) -> None:
    """Verify the serialized signature with a fresh, public-key-only context."""
    root = etree.fromstring(xml)
    xmlsec.tree.add_ids(root, ["Id"])
    signature = root.find(f".//{{{DS}}}Signature")
    assert signature is not None
    context = xmlsec.SignatureContext()
    context.key = xmlsec.Key.from_memory(
        certificate.certificate.public_bytes(Encoding.PEM),
        xmlsec.constants.KeyDataFormatCertPem,
        None,
    )
    context.verify(signature)


@pytest.mark.parametrize("operation", list(MandateOperationType))
@pytest.mark.parametrize("nature", list(MandateNature))
@pytest.mark.parametrize("mode", list(MandateReferenceType))
def test_all_mandate_variants(
    mandate_event: MandateEvent,
    radian_software: RadianSoftware,
    digital_certificate: DigitalCertificate,
    ubl_schema: etree.XMLSchema,
    operation: MandateOperationType,
    nature: MandateNature,
    mode: MandateReferenceType,
) -> None:
    limited = operation.value in ("431", "433")
    general_documents = operation.value in ("431", "432")
    scope = (
        mandate_event.scope
        if general_documents
        else MandateScope(
            powers=(
                (
                    MandatePower.WITH_REPRESENTATION,
                    MandateChannel.ELECTRONIC_NEGOTIATION_SYSTEM,
                ),
                (
                    MandatePower.ACKNOWLEDGEMENT,
                    MandateChannel.ELECTRONIC_NEGOTIATION_SYSTEM,
                ),
            )
        )
    )
    ref = mandate_event.document_references[0]
    refs: tuple[MandateDocumentReference, ...] = (
        () if mode is MandateReferenceType.ALL else (ref,)
    )
    if mode is MandateReferenceType.MULTIPLE:
        refs += (replace(ref, document_number="FE2", uuid="b" * 96),)
    contract = mandate_event.attached_contract
    note = None
    if nature is MandateNature.GENERAL:
        notary = replace(
            mandate_event.sender_party.representative,
            job_title="Notario",
            organization_department="1",
        )
        contract = replace(contract, issuer=notary, effective_date=date(2026, 10, 21))
        note = MandateAttachedDocument(
            document_id="VALIDITY-1",
            issuer=notary,
            embedded_bytes=b"%PDF-1.7\nSynthetic validity note",
        )
    event = replace(
        mandate_event,
        operation_type=operation,
        nature=nature,
        reference_type=mode,
        document_references=refs,
        scope=scope,
        attached_contract=contract,
        attached_validity_note=note,
        validity_period=mandate_event.validity_period
        if limited
        else MandateValidityPeriod(),
    )
    root = build_mandate_application_response(
        event, software=radian_software, environment=Environment.HABILITATION
    )
    sign_application_response(
        root, certificate=digital_certificate, signer_role=radian_software.signer_role
    )
    raw = etree.tostring(root, encoding="UTF-8", xml_declaration=True)
    parsed = etree.fromstring(raw)
    assert ubl_schema.validate(parsed), str(ubl_schema.error_log)
    verify(raw, digital_certificate)
    assert parsed.findtext(f"{{{CBC}}}ProfileExecutionID") == "2"
    customization = parsed.find(f"{{{CBC}}}CustomizationID")
    assert customization is not None and customization.get("schemeID") == nature.value
    primary, scope_block = parsed.findall(f"{{{CAC}}}DocumentResponse")
    assert len(primary.findall(f"{{{CAC}}}Response")) == 1
    assert len(primary.findall(f"{{{CAC}}}LineResponse")) == (2 if note else 1)
    xml_refs = primary.findall(f"{{{CAC}}}DocumentReference")
    assert len(xml_refs) == max(1, len(refs))
    response_code = primary.find(f"{{{CAC}}}Response/{{{CBC}}}ResponseCode")
    assert response_code is not None and response_code.get("listID") == mode.value
    if mode is MandateReferenceType.ALL:
        assert xml_refs[0].findtext(f"{{{CBC}}}ID") == "1"
        assert xml_refs[0].find(f"{{{CBC}}}UUID") is None
        assert xml_refs[0].find(f"{{{CBC}}}DocumentTypeCode") is None
    assert len(
        xml_refs[0].findall(f"{{{CAC}}}ValidityPeriod/{{{CBC}}}StartDate")
    ) == int(limited)
    assert (
        scope_block.findtext(
            f"{{{CAC}}}LineResponse/{{{CAC}}}Response/{{{CBC}}}ResponseCode"
        )
        == "ACEPTA"
    )
    assert (
        primary.find(
            f"{{{CAC}}}IssuerParty/{{{CAC}}}PowerOfAttorney/{{{CAC}}}AgentParty/{{{CAC}}}Person"
        )
        is not None
    )
    assert primary.find(f"{{{CAC}}}IssuerParty/{{{CAC}}}Person") is None
    assert parsed.findtext(f".//{{{XADES}}}ClaimedRole") == "thirdparty"
    cude = parsed.findtext(f"{{{CBC}}}UUID")
    ref_id = "1" if not refs else "FE1"
    expected = sha384(
        (
            f"TEST-12026-10-2210:30:00-05:00900000001800197268043{ref_id}01"
            "synthetic-pin"
        ).encode()
    ).hexdigest()
    assert cude == expected
    assert parsed.findtext(f".//{{{STS}}}QRCode") == (
        f"https://catalogo-vpfe-hab.dian.gov.co/document/searchqr?documentkey={cude}"
    )
    assert (
        parsed.findtext(f".//{{{STS}}}SoftwareSecurityCode")
        == sha384(
            (
                radian_software.software_id + radian_software.pin + event.event_number
            ).encode()
        ).hexdigest()
    )


def test_per_invoice_scopes_preserve_references(
    mandate_event: MandateEvent,
    radian_software: RadianSoftware,
    ubl_schema: etree.XMLSchema,
) -> None:
    scope = MandateScope(
        powers=(
            (MandatePower.WITH_REPRESENTATION, MandateChannel.FACTOR),
            (MandatePower.GUARANTEE, MandateChannel.FACTOR),
        )
    )
    other = MandateScope(
        powers=(
            (MandatePower.WITH_REPRESENTATION, MandateChannel.FACTOR),
            (MandatePower.MANDATE, MandateChannel.FACTOR),
        )
    )
    ref = mandate_event.document_references[0]
    refs = (ref, replace(ref, document_number="FE2", scope=other), ref)
    event = replace(
        mandate_event,
        operation_type=MandateOperationType.LIMITED_LIMITED_TIME,
        reference_type=MandateReferenceType.MULTIPLE,
        document_references=refs,
        scope=scope,
    )
    root = build_mandate_application_response(
        event, software=radian_software, environment=Environment.PRODUCTION
    )
    assert ubl_schema.validate(root), str(ubl_schema.error_log)
    blocks = root.findall(f"{{{CAC}}}DocumentResponse")
    assert len(blocks) == 3
    assert [
        n.text for n in blocks[0].findall(f"{{{CAC}}}DocumentReference/{{{CBC}}}ID")
    ] == ["FE1", "FE2", "FE1"]
    assert len(blocks[1].findall(f"{{{CAC}}}DocumentReference")) == 2
    assert blocks[2].findtext(f"{{{CAC}}}DocumentReference/{{{CBC}}}ID") == "FE2"


@pytest.mark.parametrize(
    "offset,expected_day,expected_time",
    [
        (0, "2026-10-21", "22:30:00-05:00"),
        (9, "2026-10-21", "13:30:00-05:00"),
        (-12, "2026-10-22", "10:30:00-05:00"),
    ],
)
def test_xml_and_cude_share_normalized_date(
    mandate_event: MandateEvent,
    radian_software: RadianSoftware,
    offset: int,
    expected_day: str,
    expected_time: str,
) -> None:
    event = replace(
        mandate_event,
        issue_time=time(3, 30, 0, 999, tzinfo=timezone(timedelta(hours=offset))),
    )
    root = build_mandate_application_response(
        event, software=radian_software, environment=Environment.PRODUCTION
    )
    assert root.findtext(f"{{{CBC}}}IssueDate") == expected_day
    assert root.findtext(f"{{{CBC}}}IssueTime") == expected_time
    expected = sha384(
        (
            f"TEST-1{expected_day}{expected_time}900000001800197268043FE101"
            "synthetic-pin"
        ).encode()
    ).hexdigest()
    assert root.findtext(f"{{{CBC}}}UUID") == expected


@pytest.mark.parametrize(
    "path", [f"{{{CBC}}}ID", f".//{{{DS}}}KeyInfo", f".//{{{XADES}}}SignedProperties"]
)
def test_tampering_invalidates_signature(
    mandate_event: MandateEvent,
    radian_software: RadianSoftware,
    digital_certificate: DigitalCertificate,
    path: str,
) -> None:
    root = build_mandate_application_response(
        mandate_event, software=radian_software, environment=Environment.PRODUCTION
    )
    sign_application_response(
        root, certificate=digital_certificate, signer_role="supplier"
    )
    raw = etree.tostring(root)
    verify(raw, digital_certificate)
    received = etree.fromstring(raw)
    node = received.find(path)
    assert node is not None
    node.set("tampered", "true")
    with pytest.raises(xmlsec.Error):
        verify(etree.tostring(received), digital_certificate)


def test_certificate_chain_and_policy(
    mandate_event: MandateEvent,
    radian_software: RadianSoftware,
    digital_certificate: DigitalCertificate,
) -> None:
    chained = replace(
        digital_certificate, additional_certificates=(digital_certificate.certificate,)
    )
    root = build_mandate_application_response(
        mandate_event, software=radian_software, environment=Environment.PRODUCTION
    )
    sign_application_response(root, certificate=chained, signer_role="supplier")
    assert len(root.findall(f".//{{{DS}}}X509Certificate")) == 2
    assert root.findtext(f".//{{{XADES}}}SigPolicyId/{{{XADES}}}Description")
    assert root.findtext(f".//{{{XADES}}}SigPolicyHash/{{{DS}}}DigestValue") == (
        "dMoMvtcG5aIzgYo0tIsSQeVJBDnUnfSOfBpxXrmor0Y="
    )
    verify(etree.tostring(root), digital_certificate)


def test_annex_hash_algorithm_example() -> None:
    # The published vector uses response code 030; actual mandate tests use 043.
    assert compute_mandate_cude(
        "1",
        date(2019, 4, 30),
        time(19, 48, 50),
        "99998888",
        "11111",
        document_number="1",
        response_code="030",
    ) == (
        "3a386d6eb39ad711932af8ab1b3e318fadf1f39dea97d0ab8ababc8cb6fff5f3"
        "b91ee11b0a3a898b3ac3a0a908bcfdf9"
    )


def test_signing_errors_are_typed(
    mandate_event: MandateEvent,
    radian_software: RadianSoftware,
    digital_certificate: DigitalCertificate,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from cryptography import x509
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.asymmetric import ec

    from radiankore.exceptions import DianSignatureError

    root = build_mandate_application_response(
        mandate_event, software=radian_software, environment=Environment.PRODUCTION
    )
    with pytest.raises(ValueError):
        sign_application_response(
            root, certificate=digital_certificate, signer_role="bad"
        )
    key = ec.generate_private_key(ec.SECP256R1())
    base = digital_certificate.certificate
    cert = (
        x509.CertificateBuilder()
        .subject_name(base.subject)
        .issuer_name(base.issuer)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(base.not_valid_before_utc)
        .not_valid_after(base.not_valid_after_utc)
        .sign(key, hashes.SHA256())
    )
    with pytest.raises(DianSignatureError, match="RSA private"):
        sign_application_response(
            root, certificate=DigitalCertificate(key, cert), signer_role="supplier"
        )
    with pytest.raises(DianSignatureError, match="unsigned UBL"):
        sign_application_response(
            etree.Element("root"),
            certificate=digital_certificate,
            signer_role="supplier",
        )

    def failing_context() -> None:
        raise xmlsec.Error("synthetic failure")

    monkeypatch.setattr(xmlsec, "SignatureContext", failing_context)
    with pytest.raises(DianSignatureError) as failure:
        sign_application_response(
            root, certificate=digital_certificate, signer_role="supplier"
        )
    assert isinstance(failure.value.__cause__, xmlsec.Error)


@pytest.mark.parametrize(
    "name",
    [
        "../escape.xml",
        "/absolute.xml",
        "folder/file.xml",
        "folder\\file.xml",
        "file.zip",
    ],
)
def test_zip_rejects_paths(name: str) -> None:
    from radiankore._soap.events import pack_event

    with pytest.raises(ValueError):
        pack_event(b"<xml/>", xml_name=name)

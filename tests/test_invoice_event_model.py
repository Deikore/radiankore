"""Public invoice emission contracts and incompatible event-specific inputs."""

from collections.abc import Callable
from dataclasses import FrozenInstanceError, replace
from datetime import datetime

import pytest

from radiankore.catalogs import (
    DocumentType,
    EventType,
    IdentificationType,
    InvoiceClaimReason,
    OrganizationType,
    PartyTaxScheme,
)
from radiankore.models.events import InvoiceResponseEvent, PreparedRadianEvent


@pytest.mark.parametrize("code", ["030", "031", "032", "033", "034"])
def test_public_immutable_models(
    invoice_event_factory: Callable[[EventType], InvoiceResponseEvent],
    code: str,
) -> None:
    event = invoice_event_factory(EventType(code))
    assert not hasattr(event, "__dict__")
    assert event.document_reference.document_type is DocumentType.SALES_INVOICE
    with pytest.raises(FrozenInstanceError):
        event.event_number = "other"  # type: ignore[misc]


@pytest.mark.parametrize(
    "change,exception",
    [
        ({"code": "030"}, TypeError),
        ({"code": EventType.MANDATE}, ValueError),
        ({"event_number": " "}, ValueError),
        ({"event_number": 1}, TypeError),
        ({"event_number": "x" * 51}, ValueError),
        ({"issue_date": datetime(2026, 10, 22)}, TypeError),
        ({"issue_time": "10:30"}, TypeError),
        ({"sender_party": None}, TypeError),
        ({"receiver_party": None}, TypeError),
        ({"document_reference": None}, TypeError),
        ({"issuer_person": None}, TypeError),
        ({"claim_reason": InvoiceClaimReason.GOODS_NOT_DELIVERED}, ValueError),
        ({"notes": ["note"]}, TypeError),
        ({"notes": ("",)}, ValueError),
        ({"notes": ("x" * 10_001,)}, ValueError),
    ],
)
def test_invalid_event_inputs(
    invoice_event_factory: Callable[[EventType], InvoiceResponseEvent],
    change: dict[str, object],
    exception: type[Exception],
) -> None:
    event = invoice_event_factory(EventType.INVOICE_ACKNOWLEDGEMENT)
    with pytest.raises(exception):
        replace(event, **change)  # type: ignore[arg-type]


def test_event_specific_inputs(
    invoice_event_factory: Callable[[EventType], InvoiceResponseEvent],
) -> None:
    claim = invoice_event_factory(EventType.INVOICE_CLAIM)
    with pytest.raises(TypeError, match="InvoiceClaimReason"):
        replace(claim, claim_reason=None)
    with pytest.raises(ValueError, match="issuer_person"):
        replace(
            claim,
            issuer_person=invoice_event_factory(
                EventType.INVOICE_ACKNOWLEDGEMENT
            ).issuer_person,
        )
    tacit = invoice_event_factory(EventType.TACIT_ACCEPTANCE)
    with pytest.raises(ValueError, match="sworn"):
        replace(tacit, notes=())
    with pytest.raises(ValueError, match="DIAN receiver"):
        replace(tacit, receiver_party=claim.receiver_party)
    with pytest.raises(ValueError, match="NIT"):
        replace(
            claim,
            sender_party=replace(
                claim.sender_party,
                identification_type=IdentificationType.CITIZENSHIP_CARD,
                verification_digit=None,
            ),
        )


def test_party_person_and_reference_validation(
    invoice_event_factory: Callable[[EventType], InvoiceResponseEvent],
) -> None:
    event = invoice_event_factory(EventType.INVOICE_ACKNOWLEDGEMENT)
    with pytest.raises(ValueError, match="verification digit"):
        replace(event.sender_party, verification_digit=None)
    with pytest.raises(ValueError, match="only applicable"):
        assert event.receiver_party is not None
        replace(event.receiver_party, verification_digit="1")
    with pytest.raises(TypeError, match="OrganizationType"):
        replace(event.sender_party, organization_type="1")  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="PartyTaxScheme"):
        replace(event.sender_party, tax_scheme="01")  # type: ignore[arg-type]
    assert event.issuer_person is not None
    with pytest.raises(ValueError, match="family_name"):
        replace(event.issuer_person, family_name=" ")
    with pytest.raises(ValueError, match="100 characters"):
        replace(event.issuer_person, job_title="x" * 101)
    for invalid in ("a" * 95, "x" * 96):
        with pytest.raises(ValueError, match="uuid"):
            replace(event.document_reference, uuid=invalid)
    for kind in (DocumentType.CREDIT_NOTE, DocumentType.APPLICATION_RESPONSE):
        with pytest.raises(ValueError, match="01-04"):
            replace(event.document_reference, document_type=kind)
    with pytest.raises(TypeError, match="DocumentType"):
        replace(event.document_reference, document_type="01")  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "catalog,codes",
    [
        (InvoiceClaimReason, ["01", "02", "03", "04"]),
        (OrganizationType, ["1", "2"]),
        (PartyTaxScheme, ["01", "04", "ZA", "ZZ"]),
    ],
)
def test_catalog_contracts(
    catalog: type[InvoiceClaimReason] | type[OrganizationType] | type[PartyTaxScheme],
    codes: list[str],
) -> None:
    assert [member.value for member in catalog] == codes
    for member in catalog:
        assert catalog.from_code(member.value) is member
        assert member.label
    for unknown in (None, "", " 01 ", "future"):
        assert catalog.from_code(unknown) is None


def test_prepared_inputs_are_validated() -> None:
    from radiankore import Environment

    prepared = PreparedRadianEvent(
        code=EventType.EXPRESS_ACCEPTANCE,
        event_number="SYNTHETIC",
        cude="a" * 96,
        environment=Environment.HABILITATION,
        xml_bytes=b"<synthetic/>",
        zip_bytes=b"synthetic archive",
    )
    assert "xml_bytes=" not in repr(prepared) and "zip_bytes=" not in repr(prepared)
    with pytest.raises(ValueError, match="Unsupported"):
        replace(prepared, code=EventType.DIAN_REJECTED)
    with pytest.raises(ValueError, match="digest"):
        replace(prepared, cude="A" * 96)
    with pytest.raises(ValueError, match="empty"):
        replace(prepared, zip_bytes=b"")

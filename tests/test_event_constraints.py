"""Regressions for statutory bounds, conditional data and one-payment profiles."""

from collections.abc import Callable
from dataclasses import replace
from decimal import Decimal, localcontext

import pytest
from lxml import etree

from radiankore import DianClient, DigitalCertificate, Environment
from radiankore._soap.namespaces import CAC, CBC
from radiankore.catalogs import EventNoteKind, OrganizationType, PartyTaxScheme
from radiankore.models.events import (
    EconomicRightsPaymentEvent,
    EconomicRightsTransferEvent,
    EndorsementEvent,
    EventNote,
    InvoicePaymentEvent,
    MandateEvent,
    RadianEvent,
    RadianSoftware,
)


@pytest.mark.parametrize("variant", ["451", "452", "511", "512"])
@pytest.mark.parametrize("violation", ["zero", "exceeds", "balance", "full"])
def test_payment_rejection_rules_are_shared(
    radian_event_factory: Callable[[str], RadianEvent],
    variant: str,
    violation: str,
) -> None:
    event = radian_event_factory(variant)
    assert isinstance(event, (InvoicePaymentEvent, EconomicRightsPaymentEvent))
    if violation == "zero":
        amount, rule = Decimal("0"), "positive"
    elif violation == "exceeds":
        amount, rule = event.current_value + 1, "AAF19b"
    elif violation == "full" and variant in {"452", "512"}:
        amount, rule = event.current_value - 1, "AAF19c"
    elif variant in {"451", "511"}:
        amount, rule = event.payer.amount - 1, "AAK07"
    else:
        amount, rule = Decimal("0.01"), "AAF19c"
    with pytest.raises(ValueError, match=rule):
        replace(event, payer=replace(event.payer, amount=amount))


def test_invoice_payment_has_no_legacy_multiple_payers_alias(
    radian_event_factory: Callable[[str], RadianEvent],
) -> None:
    event = radian_event_factory("451")
    assert isinstance(event, InvoicePaymentEvent)
    with pytest.raises(TypeError, match="payers"):
        replace(event, payers=(event.payer,))  # type: ignore[call-arg]
    with pytest.raises(TypeError, match="RadianParticipation"):
        replace(event, payer=(event.payer, event.payer))  # type: ignore[arg-type]


@pytest.mark.parametrize("variant", ["451", "511"])
def test_payment_arithmetic_preserves_precision_in_a_consumers_decimal_context(
    radian_event_factory: Callable[[str], RadianEvent], variant: str
) -> None:
    event = radian_event_factory(variant)
    assert isinstance(event, (InvoicePaymentEvent, EconomicRightsPaymentEvent))
    with localcontext() as context:
        context.prec = 2
        payment = replace(
            event,
            current_value=Decimal("1234567890123456.78"),
            remaining_value=Decimal("1234567890122222.22"),
            payer=replace(event.payer, amount=Decimal("1234.56")),
        )
    assert payment.payer.amount == Decimal("1234.56")


@pytest.mark.parametrize(
    "variant",
    ["371", "372", "038", "039", "047", "371-blank", "038-blank", "039-blank"],
)
@pytest.mark.parametrize("side", ["endorsers", "endorsees"])
def test_zero_endorsement_participations_are_not_sum_notifications(
    radian_event_factory: Callable[[str], RadianEvent], variant: str, side: str
) -> None:
    event = radian_event_factory(variant)
    assert isinstance(event, EndorsementEvent)
    participants = event.endorsers if side == "endorsers" else event.endorsees
    changed = (replace(participants[0], amount=Decimal("0.00")), *participants[1:])
    with pytest.raises(ValueError, match="positive"):
        if side == "endorsers":
            replace(event, endorsers=changed)
        else:
            replace(event, endorsees=changed)


@pytest.mark.parametrize("variant", ["491", "492", "493", "494"])
def test_zero_transferee_is_distinct_from_a_sum_mismatch_notification(
    radian_event_factory: Callable[[str], RadianEvent], variant: str
) -> None:
    event = radian_event_factory(variant)
    assert isinstance(event, EconomicRightsTransferEvent)
    with pytest.raises(ValueError, match="positive"):
        replace(event, transferees=(replace(event.transferees[0], amount=Decimal(0)),))
    assert replace(event, transferees=event.transferees[:1]).transferees


@pytest.mark.parametrize("size", [1, 50])
def test_mandate_event_number_boundaries(
    mandate_event: MandateEvent, size: int
) -> None:
    assert replace(mandate_event, event_number="X" * size).event_number == "X" * size
    with pytest.raises(ValueError, match="50"):
        replace(mandate_event, event_number="X" * 51)


@pytest.mark.parametrize("size", [5, 450])
def test_mandate_party_name_boundaries(mandate_event: MandateEvent, size: int) -> None:
    party = mandate_event.sender_party
    assert replace(party, name="X" * size).name == "X" * size
    for invalid in (4, 451):
        with pytest.raises(ValueError):
            replace(party, name="X" * invalid)


def test_mandate_note_reference_and_person_bounds(mandate_event: MandateEvent) -> None:
    assert (
        len(
            replace(
                mandate_event,
                additional_notes=(
                    EventNote(kind=EventNoteKind.ADDITIONAL, text="X" * 5000),
                ),
            )
            .additional_notes[0]
            .text
        )
        == 5000
    )
    with pytest.raises(ValueError, match="5000"):
        replace(
            mandate_event,
            additional_notes=(
                EventNote(kind=EventNoteKind.ADDITIONAL, text="X" * 5001),
            ),
        )
    ref = mandate_event.document_references[0]
    assert len(replace(ref, document_number="X" * 50).document_number) == 50
    with pytest.raises(ValueError, match="50"):
        replace(ref, document_number="X" * 51)
    person = mandate_event.sender_party.representatives[0]
    for name, maximum in (
        ("first_name", 100),
        ("family_name", 100),
        ("job_title", 100),
        ("nationality_id", 100),
        ("organization_department", 200),
    ):
        changed = replace(person, **{name: "X" * maximum})  # type: ignore[arg-type]
        assert getattr(changed, name) == "X" * maximum
        with pytest.raises(ValueError):
            replace(person, **{name: "X" * (maximum + 1)})  # type: ignore[arg-type]
    # AAF23 uses 14 characters; agent and notary AAH70/ABH20 permit 15.
    long_person = replace(person, identification_number="1" * 15)
    with pytest.raises(ValueError, match="14"):
        replace(
            mandate_event,
            sender_party=replace(
                mandate_event.sender_party, representatives=(long_person,)
            ),
        )
    replace(
        mandate_event,
        mandatee_party=replace(
            mandate_event.mandatee_party, representatives=(long_person,)
        ),
        declaration=replace(mandate_event.declaration, declarant=long_person),
    )


@pytest.mark.parametrize("organization", list(OrganizationType))
@pytest.mark.parametrize("tax_scheme", list(PartyTaxScheme))
@pytest.mark.parametrize("environment", list(Environment))
def test_mandate_organization_and_tax_are_explicit_serialized_inputs(
    mandate_event: MandateEvent,
    digital_certificate: DigitalCertificate,
    radian_software: RadianSoftware,
    verify_event_signature: Callable[[bytes, DigitalCertificate], None],
    organization: OrganizationType,
    tax_scheme: PartyTaxScheme,
    environment: Environment,
) -> None:
    event = replace(
        mandate_event,
        sender_party=replace(
            mandate_event.sender_party,
            organization_type=organization,
            tax_scheme=tax_scheme,
        ),
    )
    with DianClient.from_certificate(
        digital_certificate, environment=environment
    ) as client:
        prepared = client.prepare_radian_event(event=event, software=radian_software)
    verify_event_signature(prepared.xml_bytes, digital_certificate)
    root = etree.fromstring(prepared.xml_bytes)
    tax = root.find(f"{{{CAC}}}SenderParty/{{{CAC}}}PartyTaxScheme")
    assert tax is not None
    company = tax.find(f"{{{CBC}}}CompanyID")
    assert company is not None and company.get("schemeVersionID") == organization.value
    assert tax.findtext(f"{{{CAC}}}TaxScheme/{{{CBC}}}ID") == tax_scheme.value
    assert tax.findtext(f"{{{CAC}}}TaxScheme/{{{CBC}}}Name") == tax_scheme.label
    assert mandate_event.sender_party.organization_type is OrganizationType.LEGAL_PERSON
    assert mandate_event.sender_party.tax_scheme is PartyTaxScheme.VAT


@pytest.mark.parametrize("field", ["organization_type", "tax_scheme"])
def test_mandate_tax_catalogs_remain_typed(
    mandate_event: MandateEvent, field: str
) -> None:
    with pytest.raises(TypeError):
        replace(mandate_event.sender_party, **{field: "1"})  # type: ignore[arg-type]

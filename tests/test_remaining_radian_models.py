"""Public contracts and financial/profile boundaries of the final RADIAN families."""

from collections.abc import Callable
from dataclasses import replace
from datetime import UTC, date, datetime, time
from decimal import Decimal, localcontext

import pytest

from radiankore.catalogs import AcceptanceFailureType, RadianOperationType
from radiankore.models.events import (
    CirculationRestrictionEvent,
    CirculationRestrictionTerminationEvent,
    EconomicRightsNotificationEvent,
    EconomicRightsPaymentEvent,
    EconomicRightsTransferEvent,
    GuaranteeBeneficiary,
    GuaranteeCommitment,
    GuaranteeEvent,
    InvoiceResponseEvent,
    MandateEvent,
    ProtestAct,
    ProtestEvent,
    ProtestNotary,
    RadianEvent,
    RadianEventReference,
    RadianPdfAttachment,
)


@pytest.mark.parametrize(
    "variant,change,error",
    [
        ("035", {"guarantors": ()}, ValueError),
        ("035", {"guarantors": (None,)}, TypeError),
        ("035", {"beneficiaries": []}, TypeError),
        ("035", {"beneficiaries": (None,)}, TypeError),
        ("035", {"title_value": Decimal("0")}, ValueError),
        ("491", {"transferors": ()}, ValueError),
        ("491", {"transferees": ()}, ValueError),
        ("491", {"debtors": ()}, ValueError),
        ("491", {"debtors": (None,)}, TypeError),
        ("491", {"terms": None}, TypeError),
        ("050", {"current_value": 1.5}, TypeError),
        ("050", {"receiver_party": None}, TypeError),
        ("511", {"payer": None}, TypeError),
        ("511", {"restriction": "1"}, TypeError),
        ("511", {"remaining_value": Decimal("0")}, ValueError),
        ("511", {"remaining_value": Decimal("100000")}, ValueError),
        ("511", {"remaining_value": Decimal("10000")}, ValueError),
        ("511", {"effective_date": date(2026, 10, 23)}, ValueError),
        ("511", {"effective_date": datetime(2026, 10, 21)}, TypeError),
        ("512", {"remaining_value": Decimal("1")}, ValueError),
        ("411", {"authorities": ()}, ValueError),
        ("411", {"officials": ()}, ValueError),
        ("411", {"officials": (None,)}, TypeError),
        ("411", {"attachment": None}, TypeError),
        ("411", {"measure_value": Decimal("-1")}, ValueError),
        ("421", {"debt_value": Decimal("NaN")}, ValueError),
        ("421", {"restriction_value": 1.5}, TypeError),
        ("481", {"act": None}, TypeError),
        ("481", {"acceptance_failure": "1"}, TypeError),
        ("481", {"acceptance_failure": None}, TypeError),
        ("481", {"accepted_value": None}, TypeError),
        ("481", {"pending_value": None}, TypeError),
        ("481", {"pending_value": Decimal("0")}, ValueError),
        ("481", {"accepted_value": Decimal("1")}, ValueError),
        ("481", {"acceptance_failure": AcceptanceFailureType.TOTAL}, ValueError),
        ("482", {"accepted_value": Decimal("0")}, ValueError),
        ("482", {"acceptance_failure": AcceptanceFailureType.TOTAL}, ValueError),
    ],
)
def test_invalid_compositions_fail_before_xml(
    radian_event_factory: Callable[[str], RadianEvent],
    variant: str,
    change: dict[str, object],
    error: type[Exception],
) -> None:
    with pytest.raises(error):
        replace(radian_event_factory(variant), **change)  # type: ignore[arg-type]


@pytest.mark.parametrize("variant", ["411", "421", "481", "491", "511"])
def test_operation_cannot_cross_family(
    radian_event_factory: Callable[[str], RadianEvent], variant: str
) -> None:
    event = radian_event_factory(variant)
    with pytest.raises(ValueError, match="family"):
        replace(event, operation_type=RadianOperationType.GUARANTEE)  # type: ignore[arg-type]
    with pytest.raises(TypeError):
        replace(event, operation_type=variant)  # type: ignore[arg-type]


def test_guarantee_full_coverage_and_amount_width_are_profile_specific(
    radian_event_factory: Callable[[str], RadianEvent],
) -> None:
    event = radian_event_factory("035")
    assert isinstance(event, GuaranteeEvent)
    guarantor = event.guarantors[0]
    assert guarantor.amount == 0
    # AAF19 permits 25 characters, without widening all other money fields.
    wide = replace(guarantor, amount=Decimal("1" * 25))
    assert replace(event, guarantors=(wide,)).guarantors == (wide,)
    for amount in (Decimal("1" * 26), Decimal("-1"), Decimal("Infinity")):
        with pytest.raises(ValueError):
            replace(guarantor, amount=amount)
    beneficiary = GuaranteeBeneficiary(party=guarantor.party)
    assert replace(event, beneficiaries=(beneficiary,)).beneficiaries[0].amount is None
    with pytest.raises(ValueError, match="individual amounts"):
        replace(event, beneficiaries=(beneficiary, beneficiary))
    quantified = replace(beneficiary, amount=Decimal("30000.00"))
    assert replace(event, beneficiaries=(quantified, quantified)).beneficiaries == (
        quantified,
        quantified,
    )
    with pytest.raises(ValueError, match="declaration"):
        replace(event, header=replace(event.header, notes=()))
    with pytest.raises(ValueError):
        GuaranteeCommitment(
            party=replace(guarantor.party, name=None), amount=Decimal("0")
        )


def test_transfer_extension_rejection_takes_precedence_over_notification(
    radian_event_factory: Callable[[str], RadianEvent],
) -> None:
    event = radian_event_factory("491")
    assert isinstance(event, EconomicRightsTransferEvent)
    with pytest.raises(ValueError, match="AAI05a"):
        replace(event, transferors=event.transferors[:1])
    with pytest.raises(ValueError, match="positive"):
        replace(
            event, transferors=(replace(event.transferors[0], amount=Decimal("0")),)
        )
    # AAG20 remains a notification, and ambiguous price/factor math is not imposed.
    assert replace(event, transferees=event.transferees[:1]).transferees
    assert (
        replace(event, terms=replace(event.terms, price=Decimal("1"))).terms.price == 1
    )
    for value in (Decimal("101"), Decimal("0.000001")):
        with pytest.raises(ValueError):
            replace(event.terms, discount_factor=value)
    with pytest.raises(TypeError):
        replace(event.terms, payment_means="10")  # type: ignore[arg-type]


@pytest.mark.parametrize("variant", ["481", "491", "050", "511"])
def test_due_date_required_by_new_profiles(
    radian_event_factory: Callable[[str], RadianEvent], variant: str
) -> None:
    event = radian_event_factory(variant)
    assert not isinstance(event, (InvoiceResponseEvent, MandateEvent))
    with pytest.raises(ValueError, match="due_date"):
        replace(event, reference=replace(event.reference, due_date=None))  # type: ignore[arg-type]


def test_invoice_and_event_references_are_not_interchangeable(
    radian_event_factory: Callable[[str], RadianEvent],
) -> None:
    restriction = radian_event_factory("411")
    termination = radian_event_factory("421")
    assert isinstance(restriction, CirculationRestrictionEvent)
    assert isinstance(termination, CirculationRestrictionTerminationEvent)
    with pytest.raises(TypeError):
        replace(restriction, reference=termination.reference)  # type: ignore[arg-type]
    with pytest.raises(TypeError):
        replace(termination, reference=restriction.reference)  # type: ignore[arg-type]
    notification = radian_event_factory("050")
    assert isinstance(notification, EconomicRightsNotificationEvent)
    with pytest.raises(TypeError):
        replace(
            notification,
            reference=RadianEventReference(document_number="X", uuid="a" * 96),  # type: ignore[arg-type]
        )


def test_payment_amount_rules_and_colombian_day_are_explicit(
    radian_event_factory: Callable[[str], RadianEvent],
) -> None:
    event = radian_event_factory("511")
    full = radian_event_factory("512")
    assert isinstance(event, EconomicRightsPaymentEvent)
    assert isinstance(full, EconomicRightsPaymentEvent)
    for amount in (Decimal("0"), Decimal("100001"), Decimal("1")):
        with pytest.raises(ValueError):
            replace(event, payer=replace(event.payer, amount=amount))
    with pytest.raises(ValueError, match="AAF19c"):
        replace(full, payer=event.payer)
    with localcontext() as context:
        context.prec = 2
        assert replace(event, remaining_value=Decimal("50000.00")).payer.amount == 50000
    midnight = replace(event.header, issue_time=time(1, tzinfo=UTC))
    assert replace(event, header=midnight).effective_date == date(2026, 10, 21)
    with pytest.raises(ValueError, match="Colombian"):
        replace(event, header=midnight, effective_date=date(2026, 10, 22))


def test_pdf_metadata_and_protest_contracts(
    radian_event_factory: Callable[[str], RadianEvent],
) -> None:
    evidence = RadianPdfAttachment(
        filename="test.pdf", content_bytes=b"%PDF-1.7\n%%EOF"
    )
    assert "content_bytes=" not in repr(evidence)
    with pytest.raises(TypeError):
        replace(evidence, content_bytes=bytearray(b"%PDF-1.7"))  # type: ignore[arg-type]
    with pytest.raises(ValueError):
        replace(evidence, content_bytes=b"")
    restriction = radian_event_factory("411")
    assert isinstance(restriction, CirculationRestrictionEvent)
    with pytest.raises(ValueError, match="filename"):
        replace(restriction, attachment=evidence)
    event = radian_event_factory("481")
    assert isinstance(event, ProtestEvent)
    changes_to_try: tuple[dict[str, object], ...] = (
        {"notaries": ()},
        {"notaries": (None,)},
        {"notary_number": "abc"},
        {"attachment": evidence},
        {"effective_date": datetime(2026, 10, 21)},
    )
    for changes in changes_to_try:
        with pytest.raises((TypeError, ValueError)):
            replace(event.act, **changes)  # type: ignore[arg-type]
    with pytest.raises(ValueError):
        ProtestNotary(first_name="", family_name="Synthetic", job_title="Notario")
    assert isinstance(event.act, ProtestAct)
    assert not hasattr(event.act.notaries[0], "identification_number")
    total = replace(
        event,
        acceptance_failure=AcceptanceFailureType.TOTAL,
        accepted_value=Decimal("0"),
        pending_value=event.title_value,
    )
    with localcontext() as context:
        context.prec = 2
        assert replace(total).accepted_value == 0

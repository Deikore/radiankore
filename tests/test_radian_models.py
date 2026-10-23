"""Public RADIAN invariants, financial precision and catalog compatibility."""

from collections.abc import Callable
from dataclasses import FrozenInstanceError, replace
from datetime import UTC, date, datetime, time
from decimal import Decimal, localcontext

import pytest

from radiankore.catalogs import (
    AcceptanceFailureType,
    CurrencyCode,
    EndorsementForm,
    EventType,
    FactorType,
    PaymentMeans,
    PaymentRestriction,
    RadianOperationType,
)
from radiankore.models.events import (
    EndorsementEvent,
    InvoicePaymentEvent,
    InvoiceResponseEvent,
    MandateEvent,
    NegotiationTerms,
    PreparedRadianEvent,
    RadianEvent,
    RadianEventHeader,
    RadianInvoiceReference,
    RadianParticipation,
    RadianRegistrationEvent,
    RegistrationPaymentState,
)


@pytest.mark.parametrize("operation", list(RadianOperationType))
def test_event_code_is_derived_and_inputs_are_frozen(
    radian_event_factory: Callable[[str], RadianEvent],
    operation: RadianOperationType,
) -> None:
    event = radian_event_factory(operation.value)
    assert not isinstance(event, (InvoiceResponseEvent, MandateEvent))
    assert event.code is operation.event_type
    assert not hasattr(event, "__dict__")
    with pytest.raises(FrozenInstanceError):
        event.header = event.header  # type: ignore[misc]


@pytest.mark.parametrize(
    "variant,change,error",
    [
        ("441", {"representatives": ()}, ValueError),
        ("441", {"representatives": (None,)}, TypeError),
        ("441", {"reference": None}, TypeError),
        ("441", {"sender_party": None}, TypeError),
        ("361", {"payment_state": None}, TypeError),
        ("362", {"direct_buyer": None}, TypeError),
        ("451", {"payers": ()}, ValueError),
        ("451", {"payers": (None,)}, TypeError),
        ("451", {"restriction": "1"}, TypeError),
        ("451", {"remaining_value": Decimal("0")}, ValueError),
        ("451", {"remaining_value": Decimal("1000000")}, ValueError),
        ("451", {"effective_date": date(2026, 10, 23)}, ValueError),
        ("452", {"remaining_value": Decimal("1")}, ValueError),
        ("046", {"receiver_party": None}, TypeError),
        ("371", {"negotiation": None}, TypeError),
        ("371", {"debtors": ()}, ValueError),
        ("371", {"debtors": []}, TypeError),
        ("371", {"form": "1"}, TypeError),
        ("371", {"endorsers": (RadianParticipation(amount=Decimal("1")),)}, ValueError),
        ("038", {"endorsees": (RadianParticipation(amount=Decimal("1")),)}, ValueError),
        ("401", {"receiver_party": None}, TypeError),
    ],
)
def test_invalid_public_compositions(
    radian_event_factory: Callable[[str], RadianEvent],
    variant: str,
    change: dict[str, object],
    error: type[Exception],
) -> None:
    event = radian_event_factory(variant)
    with pytest.raises(error):
        replace(event, **change)  # type: ignore[arg-type]


@pytest.mark.parametrize("variant", ["441", "361", "451", "371", "401"])
def test_wrong_operation_family_is_rejected(
    radian_event_factory: Callable[[str], RadianEvent],
    variant: str,
) -> None:
    event = radian_event_factory(variant)
    with pytest.raises(TypeError, match="RadianOperationType"):
        replace(event, operation_type=variant)  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="family"):
        replace(event, operation_type=RadianOperationType.PAYMENT_REPORT)  # type: ignore[arg-type]


def test_required_declarations_and_maturity(
    radian_event_factory: Callable[[str], RadianEvent],
) -> None:
    for variant in ("441", "442", "443", "401", "402", "403", "372"):
        event = radian_event_factory(variant)
        assert not isinstance(event, (InvoiceResponseEvent, MandateEvent))
        with pytest.raises(ValueError, match="declaration"):
            replace(event, header=replace(event.header, notes=()))
    for variant in ("361", "451", "046", "371", "047"):
        event = radian_event_factory(variant)
        assert not isinstance(event, (InvoiceResponseEvent, MandateEvent))
        assert isinstance(event.reference, RadianInvoiceReference)
        with pytest.raises(ValueError, match="due_date"):
            replace(event, reference=replace(event.reference, due_date=None))


def test_endorsement_specific_financial_and_date_rules(
    radian_event_factory: Callable[[str], RadianEvent],
) -> None:
    event = radian_event_factory("371")
    assert isinstance(event, EndorsementEvent)
    with pytest.raises(ValueError, match="AAI05a"):
        replace(event, endorsers=(replace(event.endorsers[0], amount=Decimal("1")),))
    with pytest.raises(ValueError, match="complete negotiation"):
        replace(event, negotiation=replace(event.negotiation, price=None))
    with pytest.raises(ValueError, match="omit their identity"):
        replace(event, form=EndorsementForm.BLANK)
    with pytest.raises(ValueError, match="047"):
        replace(event, reference=replace(event.reference, due_date=date(2026, 10, 21)))
    ordinary = radian_event_factory("047")
    assert isinstance(ordinary, EndorsementEvent)
    with pytest.raises(ValueError, match="after maturity"):
        replace(
            ordinary, reference=replace(ordinary.reference, due_date=date(2026, 10, 22))
        )
    with pytest.raises(ValueError, match="complete endorsement"):
        replace(
            ordinary,
            form=EndorsementForm.BLANK,
            endorsers=tuple(replace(p, party=None) for p in ordinary.endorsers),
        )
    guarantee = radian_event_factory("038")
    assert isinstance(guarantee, EndorsementEvent)
    with pytest.raises(ValueError, match="without sale terms"):
        replace(guarantee, negotiation=event.negotiation)
    # Receiver sum mismatch is a notification in the annex, not a local rejection.
    replace(event, endorsees=(replace(event.endorsees[0], amount=Decimal("1")),))
    # Preserve explicit price/rate despite contradictory AAI07b/sample arithmetic.
    replace(event, negotiation=replace(event.negotiation, price=Decimal("12345.67")))


def test_registration_buyer_and_payment_state(
    radian_event_factory: Callable[[str], RadianEvent],
) -> None:
    general = radian_event_factory("361")
    direct = radian_event_factory("362")
    assert isinstance(general, RadianRegistrationEvent)
    assert isinstance(direct, RadianRegistrationEvent)
    with pytest.raises(ValueError, match="only applicable"):
        replace(general, direct_buyer=direct.direct_buyer)
    with pytest.raises(ValueError, match="must equal"):
        RegistrationPaymentState(
            invoice_value=Decimal("100"),
            paid_value=Decimal("20"),
            remaining_value=Decimal("90"),
        )
    # All financial checks work under a consumer's low-precision Decimal context.
    with localcontext() as context:
        context.prec = 2
        balance = RegistrationPaymentState(
            invoice_value=Decimal("1234567890123456.78"),
            paid_value=Decimal("1234.56"),
            remaining_value=Decimal("1234567890122222.22"),
        )
        assert balance.invoice_value == Decimal("1234567890123456.78")


@pytest.mark.parametrize(
    "value,error",
    [
        (1.5, TypeError),
        ("10", TypeError),
        (Decimal("NaN"), ValueError),
        (Decimal("Infinity"), ValueError),
        (Decimal("-1"), ValueError),
        (Decimal("1E10000"), ValueError),
        (Decimal("1E-10000"), ValueError),
    ],
)
def test_financial_values_are_explicit_finite_decimal(
    value: object, error: type[Exception]
) -> None:
    with pytest.raises(error):
        NegotiationTerms(total_value=value)  # type: ignore[arg-type]


def test_header_native_types_and_colombian_date_boundaries(
    radian_event_factory: Callable[[str], RadianEvent],
) -> None:
    base = RadianEventHeader(
        event_number="TEST", issue_date=date(2026, 10, 22), issue_time=time(10, 30)
    )
    changes: tuple[dict[str, object], ...] = (
        {"notes": []},
        {"issue_date": datetime(2026, 10, 22)},
        {"issue_time": "10:30"},
    )
    for change in changes:
        with pytest.raises(TypeError):
            replace(base, **change)  # type: ignore[arg-type]
    event = radian_event_factory("451")
    assert isinstance(event, InvoicePaymentEvent)
    # UTC 02:00 is still the preceding day in Colombia.
    header = replace(
        event.header, issue_date=date(2026, 10, 23), issue_time=time(2, 0, tzinfo=UTC)
    )
    with pytest.raises(ValueError, match="Colombian"):
        replace(event, header=header, effective_date=date(2026, 10, 23))
    ownership = radian_event_factory("371")
    assert isinstance(ownership, EndorsementEvent)
    replace(
        ownership,
        header=header,
        reference=replace(ownership.reference, due_date=date(2026, 10, 22)),
    )


@pytest.mark.parametrize(
    "catalog",
    [
        AcceptanceFailureType,
        CurrencyCode,
        EndorsementForm,
        EventType,
        FactorType,
        PaymentMeans,
        PaymentRestriction,
        RadianOperationType,
    ],
)
def test_catalogs_follow_existing_public_contracts(
    catalog: type[AcceptanceFailureType]
    | type[CurrencyCode]
    | type[EndorsementForm]
    | type[FactorType]
    | type[PaymentMeans]
    | type[PaymentRestriction]
    | type[RadianOperationType],
) -> None:
    for member in catalog:
        assert catalog.from_code(member.value) is member and member.label
    for missing in (None, "", "unknown", " 1 "):
        assert catalog.from_code(missing) is None


@pytest.mark.parametrize("code", list(EventType))
def test_prepared_event_accepts_only_emittable_codes(code: EventType) -> None:
    from radiankore import Environment

    def prepare() -> PreparedRadianEvent:
        return PreparedRadianEvent(
            code=code,
            event_number="SYNTHETIC",
            cude="a" * 96,
            environment=Environment.HABILITATION,
            xml_bytes=b"<synthetic/>",
            zip_bytes=b"synthetic archive",
        )

    if code in (EventType.DIAN_VALIDATED, EventType.DIAN_REJECTED):
        with pytest.raises(ValueError, match="Unsupported"):
            prepare()
    else:
        assert prepare().code is code

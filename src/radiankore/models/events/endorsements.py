"""RADIAN endorsement, negotiation and cancellation domain contracts."""

from dataclasses import dataclass
from decimal import Decimal

from radiankore._datetime import colombian_issue_datetime
from radiankore.catalogs import (
    CurrencyCode,
    EndorsementForm,
    EventType,
    PaymentMeans,
    RadianOperationType,
)
from radiankore.models.events.radian_common import (
    RadianEventHeader,
    RadianEventReference,
    RadianInvoiceReference,
    RadianParticipation,
    RadianParty,
    currency,
    decimal_value,
    event_inputs,
    maturity,
    named_party,
    operation,
    participation_sum,
    participations,
)


@dataclass(frozen=True, slots=True, kw_only=True)
class NegotiationTerms:
    """Explicit financial terms; ambiguous annex discount math is not inferred."""

    total_value: Decimal
    price: Decimal | None = None
    discount_rate: Decimal | None = None
    payment_means: PaymentMeans | None = None
    currency: CurrencyCode = CurrencyCode.COP

    def __post_init__(self) -> None:
        decimal_value(self.total_value, "total_value", positive=True)
        if self.price is not None:
            decimal_value(self.price, "price")
        if self.discount_rate is not None:
            decimal_value(self.discount_rate, "discount_rate", maximum=7)
            if self.discount_rate > 100:
                raise ValueError("discount_rate is a percentage between 0 and 100.")
        if self.payment_means is not None and not isinstance(
            self.payment_means, PaymentMeans
        ):
            raise TypeError("payment_means must be a PaymentMeans or None.")
        currency(self.currency)


@dataclass(frozen=True, slots=True, kw_only=True)
class EndorsementEvent:
    """One endorsement with ordered, possibly multiple financial participants.

    Blank 037/038/039 endorsers omit identities; endorsees still identify themselves.
    Ordinary assignment (047) is complete and explicitly selected by the caller.
    """

    header: RadianEventHeader
    operation_type: RadianOperationType
    reference: RadianInvoiceReference
    form: EndorsementForm
    endorsers: tuple[RadianParticipation, ...]
    endorsees: tuple[RadianParticipation, ...]
    negotiation: NegotiationTerms
    debtors: tuple[RadianParty, ...] = ()

    def __post_init__(self) -> None:
        operation(self.operation_type, ("371", "372", "038", "039", "047"))
        event_inputs(self.header, self.reference, RadianInvoiceReference)
        if not isinstance(self.form, EndorsementForm):
            raise TypeError("form must be an EndorsementForm.")
        blank = self.form is EndorsementForm.BLANK
        participations(self.endorsers, blank=blank, sender=True, anonymous=blank)
        participations(self.endorsees, blank=blank)
        if not isinstance(self.negotiation, NegotiationTerms):
            raise TypeError("negotiation must be a NegotiationTerms.")
        if not isinstance(self.debtors, tuple):
            raise TypeError("debtors must be a tuple.")
        for party in self.debtors:
            named_party(party)
        ownership = self.operation_type.value in ("371", "372", "047")
        terms = self.negotiation
        if ownership:
            maturity(self.reference)
            if not self.debtors:
                raise ValueError(
                    "Ownership/ordinary assignment requires invoice debtors."
                )
            if (
                terms.price is None
                or terms.discount_rate is None
                or terms.payment_means is None
            ):
                raise ValueError(
                    "Ownership/ordinary assignment requires complete negotiation terms."
                )
            if participation_sum(self.endorsers) != terms.total_value:
                raise ValueError(
                    "Endorser participations must sum to total_value (AAI05a)."
                )
        elif any(
            v is not None
            for v in (terms.price, terms.discount_rate, terms.payment_means)
        ):
            raise ValueError(
                "Guarantee/collection uses total_value without sale terms."
            )
        if (
            self.operation_type is RadianOperationType.OWNERSHIP_WITHOUT_RECOURSE
            and not self.header.notes
        ):
            raise ValueError(
                "Without-recourse endorsements require an explicit declaration."
            )
        issue_date = colombian_issue_datetime(
            self.header.issue_date, self.header.issue_time
        ).date()
        due = self.reference.due_date
        if (
            self.operation_type.value in ("371", "372")
            and due is not None
            and issue_date > due
        ):
            raise ValueError("Ownership after maturity requires explicit event 047.")
        if self.operation_type is RadianOperationType.ORDINARY_ASSIGNMENT_ENDORSEMENT:
            if blank:
                raise ValueError("Event 047 requires a complete endorsement.")
            if due is not None and issue_date <= due:
                raise ValueError("Event 047 requires an issue date after maturity.")

    @property
    def code(self) -> EventType:
        """Derive the endorsement event from its operation variant."""
        return self.operation_type.event_type


@dataclass(frozen=True, slots=True, kw_only=True)
class EndorsementCancellationEvent:
    """Cancel an existing endorsement by its event CUDE and explicit declaration."""

    header: RadianEventHeader
    operation_type: RadianOperationType
    sender_party: RadianParty
    receiver_party: RadianParty
    reference: RadianEventReference

    def __post_init__(self) -> None:
        operation(self.operation_type, ("401", "402", "403"))
        event_inputs(self.header, self.reference, RadianEventReference)
        named_party(self.sender_party, sender=True)
        named_party(self.receiver_party)
        if not self.header.notes:
            raise ValueError(
                "Endorsement cancellation requires an explicit declaration."
            )

    @property
    def code(self) -> EventType:
        """Return the fixed cancellation ResponseCode."""
        return EventType.ENDORSEMENT_CANCELLATION

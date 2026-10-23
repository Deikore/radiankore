"""RADIAN economic-rights transfers, debtor notification and payment."""

import datetime as dt
from dataclasses import dataclass
from decimal import Decimal, localcontext

from radiankore.catalogs import (
    CurrencyCode,
    EventType,
    PaymentMeans,
    PaymentRestriction,
    RadianOperationType,
)
from radiankore.models.events._payment import payment_values
from radiankore.models.events.radian_common import (
    RadianEventHeader,
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
class EconomicRightsTransferTerms:
    """Explicit sale terms; the annex's ambiguous price formula is not inferred."""

    transferred_value: Decimal
    price: Decimal
    discount_factor: Decimal
    payment_means: PaymentMeans
    currency: CurrencyCode = CurrencyCode.COP

    def __post_init__(self) -> None:
        decimal_value(self.transferred_value, "transferred_value", positive=True)
        decimal_value(self.price, "price")
        decimal_value(self.discount_factor, "discount_factor", maximum=7)
        if self.discount_factor > 100:
            raise ValueError("discount_factor must be a percentage between 0 and 100.")
        if not isinstance(self.payment_means, PaymentMeans):
            raise TypeError("payment_means must be a PaymentMeans.")
        currency(self.currency)


@dataclass(frozen=True, slots=True, kw_only=True)
class EconomicRightsTransferEvent:
    """Explicit partial/total assignment, with or without transferor recourse."""

    header: RadianEventHeader
    operation_type: RadianOperationType
    reference: RadianInvoiceReference
    transferors: tuple[RadianParticipation, ...]
    transferees: tuple[RadianParticipation, ...]
    debtors: tuple[RadianParty, ...]
    terms: EconomicRightsTransferTerms

    def __post_init__(self) -> None:
        operation(self.operation_type, ("491", "492", "493", "494"))
        event_inputs(self.header, self.reference, RadianInvoiceReference)
        maturity(self.reference)
        participations(self.transferors, sender=True)
        participations(self.transferees)
        for participant in self.transferors:
            decimal_value(participant.amount, "transferor amount", positive=True)
        if not isinstance(self.debtors, tuple) or not self.debtors:
            raise ValueError("debtors must be a nonempty tuple.")
        for debtor in self.debtors:
            named_party(debtor)
        if not isinstance(self.terms, EconomicRightsTransferTerms):
            raise TypeError("terms must be EconomicRightsTransferTerms.")
        if participation_sum(self.transferors) != self.terms.transferred_value:
            raise ValueError(
                "Transferor amounts must sum to transferred_value (AAI05a)."
            )

    @property
    def code(self) -> EventType:
        """Return the economic-rights transfer ResponseCode."""
        return EventType.ECONOMIC_RIGHTS_TRANSFER


@dataclass(frozen=True, slots=True, kw_only=True)
class EconomicRightsNotificationEvent:
    """Notify the debtor, referencing the invoice rather than the transfer event."""

    header: RadianEventHeader
    sender_party: RadianParty
    receiver_party: RadianParty
    reference: RadianInvoiceReference
    current_value: Decimal

    def __post_init__(self) -> None:
        event_inputs(self.header, self.reference, RadianInvoiceReference)
        maturity(self.reference)
        named_party(self.sender_party, sender=True)
        named_party(self.receiver_party)
        decimal_value(self.current_value, "current_value", positive=True)

    @property
    def code(self) -> EventType:
        """Return the debtor notification ResponseCode."""
        return EventType.ECONOMIC_RIGHTS_TRANSFER_NOTIFICATION

    @property
    def operation_type(self) -> RadianOperationType:
        """Return the fixed debtor notification CustomizationID."""
        return RadianOperationType.ECONOMIC_RIGHTS_NOTIFICATION


@dataclass(frozen=True, slots=True, kw_only=True)
class EconomicRightsPaymentEvent:
    """One debtor's payment participation, as required by AAF12 (1..1)."""

    header: RadianEventHeader
    operation_type: RadianOperationType
    reference: RadianInvoiceReference
    payer: RadianParticipation
    restriction: PaymentRestriction
    effective_date: dt.date
    current_value: Decimal
    remaining_value: Decimal
    currency: CurrencyCode = CurrencyCode.COP

    def __post_init__(self) -> None:
        operation(self.operation_type, ("511", "512"))
        event_inputs(self.header, self.reference, RadianInvoiceReference)
        maturity(self.reference)
        participations((self.payer,), sender=True)
        partial = (
            self.operation_type is RadianOperationType.ECONOMIC_RIGHTS_PARTIAL_PAYMENT
        )
        payment_values(
            header=self.header,
            restriction=self.restriction,
            effective_date=self.effective_date,
            current_value=self.current_value,
            remaining_value=self.remaining_value,
            partial=partial,
        )
        decimal_value(self.payer.amount, "paid amount", positive=True)
        if self.payer.amount > self.current_value:
            raise ValueError("Paid amount must not exceed current_value (AAF19b).")
        if not partial and self.payer.amount != self.current_value:
            raise ValueError("Full payment must equal current_value (AAF19c).")
        with localcontext() as context:
            context.prec = 50
            if self.payer.amount + self.remaining_value != self.current_value:
                raise ValueError(
                    "Paid amount plus remaining_value must equal current_value (AAK07)."
                )
        currency(self.currency)

    @property
    def code(self) -> EventType:
        """Return the economic-rights payment ResponseCode."""
        return EventType.ECONOMIC_RIGHTS_TRANSFER_PAYMENT

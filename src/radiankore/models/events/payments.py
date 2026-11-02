"""RADIAN 045 and 046, keeping payment kind and restriction independent."""

import datetime as dt
from dataclasses import dataclass
from decimal import Decimal

from radiankore.catalogs import (
    CurrencyCode,
    EventType,
    PaymentRestriction,
    RadianOperationType,
)
from radiankore.models.events._payment import payment_values as payment_values
from radiankore.models.events.notes import validate_event_notes
from radiankore.models.events.radian_common import (
    RadianEventHeader,
    RadianInvoiceReference,
    RadianParticipation,
    RadianParty,
    additional_senders,
    currency,
    decimal_value,
    event_inputs,
    maturity,
    named_party,
    operation,
    participations,
)


@dataclass(frozen=True, slots=True, kw_only=True)
class InvoicePaymentEvent:
    """One payment participation (AAF12), independently restricted or unrestricted."""

    header: RadianEventHeader
    operation_type: RadianOperationType
    reference: RadianInvoiceReference
    payer: RadianParticipation
    restriction: PaymentRestriction
    effective_date: dt.date
    current_value: Decimal
    remaining_value: Decimal
    currency: CurrencyCode = CurrencyCode.COP

    additional_sender_parties: tuple[RadianParty, ...] = ()

    def __post_init__(self) -> None:
        operation(self.operation_type, ("451", "452"))
        event_inputs(self.header, self.reference, RadianInvoiceReference)
        additional_senders(self.additional_sender_parties)
        validate_event_notes(
            self.header.notes, code=self.code.value, operation=self.operation_type.value
        )
        maturity(self.reference)
        participations((self.payer,), sender=True)
        payment_values(
            header=self.header,
            restriction=self.restriction,
            effective_date=self.effective_date,
            current_value=self.current_value,
            remaining_value=self.remaining_value,
            paid_amount=self.payer.amount,
            partial=self.operation_type is RadianOperationType.PARTIAL_PAYMENT,
        )
        currency(self.currency)

    @property
    def code(self) -> EventType:
        """Return the invoice payment ResponseCode."""
        return EventType.INVOICE_PAYMENT


@dataclass(frozen=True, slots=True, kw_only=True)
class PaymentReportEvent:
    """Inform the debtor of a title-value invoice's payment information."""

    header: RadianEventHeader
    sender_party: RadianParty
    receiver_party: RadianParty
    reference: RadianInvoiceReference
    title_value: Decimal

    additional_sender_parties: tuple[RadianParty, ...] = ()

    def __post_init__(self) -> None:
        event_inputs(self.header, self.reference, RadianInvoiceReference)
        additional_senders(self.additional_sender_parties)
        validate_event_notes(
            self.header.notes, code=self.code.value, operation=self.operation_type.value
        )
        maturity(self.reference)
        named_party(self.sender_party, sender=True)
        named_party(self.receiver_party)
        decimal_value(self.title_value, "title_value", positive=True)

    @property
    def operation_type(self) -> RadianOperationType:
        """Return the fixed CustomizationID without accepting another variant."""
        return RadianOperationType.PAYMENT_REPORT

    @property
    def code(self) -> EventType:
        """Return the payment report ResponseCode."""
        return EventType.PAYMENT_REPORT

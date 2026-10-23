"""RADIAN 036: initial/subsequent registration and direct/general negotiation."""

from dataclasses import dataclass
from decimal import Decimal, localcontext

from radiankore.catalogs import EventType, RadianOperationType
from radiankore.models.events.radian_common import (
    RadianEventHeader,
    RadianInvoiceReference,
    RadianParty,
    decimal_value,
    event_inputs,
    maturity,
    named_party,
    operation,
)


@dataclass(frozen=True, slots=True, kw_only=True)
class RegistrationPaymentState:
    """Explicit original value, paid value and outstanding title-value balance."""

    invoice_value: Decimal
    paid_value: Decimal
    remaining_value: Decimal

    def __post_init__(self) -> None:
        decimal_value(self.invoice_value, "invoice_value", positive=True)
        decimal_value(self.paid_value, "paid_value")
        decimal_value(self.remaining_value, "remaining_value")
        with localcontext() as context:
            context.prec = 50
            if self.paid_value + self.remaining_value != self.invoice_value:
                raise ValueError(
                    "paid_value + remaining_value must equal invoice_value."
                )


@dataclass(frozen=True, slots=True, kw_only=True)
class RadianRegistrationEvent:
    """Register one invoice, with a direct buyer only for operations 362/364."""

    header: RadianEventHeader
    operation_type: RadianOperationType
    sender_party: RadianParty
    reference: RadianInvoiceReference
    payment_state: RegistrationPaymentState
    direct_buyer: RadianParty | None = None

    def __post_init__(self) -> None:
        operation(self.operation_type, ("361", "362", "363", "364"))
        event_inputs(self.header, self.reference, RadianInvoiceReference)
        maturity(self.reference)
        named_party(self.sender_party, sender=True)
        if not isinstance(self.payment_state, RegistrationPaymentState):
            raise TypeError("payment_state must be a RegistrationPaymentState.")
        direct = self.operation_type.value in ("362", "364")
        if direct:
            named_party(self.direct_buyer)  # type: ignore[arg-type]
        elif self.direct_buyer is not None:
            raise ValueError("direct_buyer is only applicable to operations 362/364.")

    @property
    def code(self) -> EventType:
        """Return the registration ResponseCode."""
        return EventType.RADIAN_REGISTRATION

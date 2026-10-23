"""RADIAN 035 guarantees, including explicit zero-as-full-coverage commitments."""

from dataclasses import dataclass
from decimal import Decimal

from radiankore.catalogs import CurrencyCode, EventType, RadianOperationType
from radiankore.models.events.radian_common import (
    RadianEventHeader,
    RadianInvoiceReference,
    RadianParty,
    currency,
    decimal_value,
    event_inputs,
    named_party,
)


@dataclass(frozen=True, slots=True, kw_only=True)
class GuaranteeCommitment:
    """One guarantor; amount zero explicitly guarantees the entire title (AAF19)."""

    party: RadianParty
    amount: Decimal

    def __post_init__(self) -> None:
        named_party(self.party, sender=True)
        decimal_value(self.amount, "guarantee amount", maximum=25)


@dataclass(frozen=True, slots=True, kw_only=True)
class GuaranteeBeneficiary:
    """An expressly guaranteed party; multiple beneficiaries require amounts."""

    party: RadianParty
    amount: Decimal | None = None

    def __post_init__(self) -> None:
        named_party(self.party)
        if self.amount is not None:
            decimal_value(self.amount, "beneficiary amount")


@dataclass(frozen=True, slots=True, kw_only=True)
class GuaranteeEvent:
    """Guarantee an invoice; no beneficiaries means all parties are guaranteed."""

    header: RadianEventHeader
    reference: RadianInvoiceReference
    title_value: Decimal
    guarantors: tuple[GuaranteeCommitment, ...]
    beneficiaries: tuple[GuaranteeBeneficiary, ...] = ()
    currency: CurrencyCode = CurrencyCode.COP

    def __post_init__(self) -> None:
        event_inputs(self.header, self.reference, RadianInvoiceReference)
        decimal_value(self.title_value, "title_value", positive=True)
        currency(self.currency)
        if not isinstance(self.guarantors, tuple) or not self.guarantors:
            raise ValueError("guarantors must be a nonempty tuple.")
        if any(not isinstance(p, GuaranteeCommitment) for p in self.guarantors):
            raise TypeError("guarantors must contain GuaranteeCommitment members.")
        if not isinstance(self.beneficiaries, tuple):
            raise TypeError("beneficiaries must be a tuple.")
        for beneficiary in self.beneficiaries:
            if not isinstance(beneficiary, GuaranteeBeneficiary):
                raise TypeError("Expected GuaranteeBeneficiary members.")
            if len(self.beneficiaries) > 1 and beneficiary.amount is None:
                raise ValueError("Multiple beneficiaries require individual amounts.")
        if not self.header.notes:
            raise ValueError("Guarantees require an explicit declaration.")

    @property
    def code(self) -> EventType:
        """Return the fixed guarantee ResponseCode."""
        return EventType.GUARANTEE

    @property
    def operation_type(self) -> RadianOperationType:
        """Return the fixed guarantee CustomizationID."""
        return RadianOperationType.GUARANTEE

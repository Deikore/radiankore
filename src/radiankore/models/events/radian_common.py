"""Pure, composable domain inputs shared by RADIAN financial event families."""

import datetime as dt
from dataclasses import dataclass
from decimal import Decimal, localcontext

from radiankore.catalogs import (
    CurrencyCode,
    DocumentType,
    FactorType,
    IdentificationType,
    OrganizationType,
    PartyTaxScheme,
    RadianOperationType,
)
from radiankore.models.events._validation import digest, identity, text


def native_date(value: dt.date, name: str) -> None:
    """Reject datetime values where a calendar date is required."""
    if type(value) is not dt.date:
        raise TypeError(f"{name} must be a native date.")


def decimal_value(
    value: Decimal, name: str, *, positive: bool = False, maximum: int = 20
) -> None:
    """Require finite Decimal values that fit the XML field without rounding."""
    if not isinstance(value, Decimal):
        raise TypeError(f"{name} must be a Decimal.")
    if not value.is_finite() or value < 0 or (positive and value == 0):
        raise ValueError(
            f"{name} must be finite and {'positive' if positive else 'nonnegative'}."
        )
    parts = value.as_tuple()
    exponent = parts.exponent
    assert isinstance(exponent, int)
    digits = len(parts.digits)
    width = (
        digits + exponent
        if exponent >= 0
        else max(digits, -exponent) + 1 + int(digits + exponent <= 0)
    )
    width += int(parts.sign)
    if width > maximum:
        raise ValueError(f"{name} exceeds the {maximum}-character numeric field.")


def operation(value: RadianOperationType, allowed: tuple[str, ...]) -> None:
    """Require a typed operation belonging to the event family."""
    if not isinstance(value, RadianOperationType):
        raise TypeError("operation_type must be a RadianOperationType.")
    if value.value not in allowed:
        raise ValueError("operation_type does not belong to this event family.")


@dataclass(frozen=True, slots=True, kw_only=True)
class RadianEventHeader:
    """Event number, Colombian issue date/time inputs and caller declarations."""

    event_number: str
    issue_date: dt.date
    issue_time: dt.time
    notes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        text(self.event_number, "event_number", maximum=50)
        native_date(self.issue_date, "issue_date")
        if not isinstance(self.issue_time, dt.time):
            raise TypeError("issue_time must be a native time.")
        if not isinstance(self.notes, tuple):
            raise TypeError("notes must be a tuple.")
        for note in self.notes:
            text(note, "note", maximum=5000)


@dataclass(frozen=True, slots=True, kw_only=True)
class RadianParty:
    """Participant identity; name may be omitted only for a blank endorsee."""

    tax_number: str
    identification_type: IdentificationType
    organization_type: OrganizationType
    name: str | None = None
    verification_digit: str | None = None
    tax_scheme: PartyTaxScheme = PartyTaxScheme.VAT

    def __post_init__(self) -> None:
        identity(self.tax_number, self.identification_type, self.verification_digit)
        if self.name is not None:
            text(self.name, "name", maximum=450)
        if not isinstance(self.organization_type, OrganizationType):
            raise TypeError("organization_type must be an OrganizationType.")
        if not isinstance(self.tax_scheme, PartyTaxScheme):
            raise TypeError("tax_scheme must be a PartyTaxScheme.")


def named_party(value: RadianParty, *, sender: bool = False) -> None:
    """Require a full named party and, where applicable, its generator NIT."""
    if not isinstance(value, RadianParty):
        raise TypeError("party must be a RadianParty.")
    if value.name is None:
        raise ValueError("A named party is required for this event.")
    if sender and value.identification_type is not IdentificationType.NIT:
        raise ValueError("The event generator must be identified by NIT.")


@dataclass(frozen=True, slots=True, kw_only=True)
class RadianPerson:
    """Legal representative, with optional notification-only personal fields."""

    identification_number: str
    identification_type: IdentificationType
    first_name: str
    family_name: str
    verification_digit: str | None = None
    job_title: str | None = None
    nationality_id: str | None = None
    organization_department: str | None = None

    def __post_init__(self) -> None:
        identity(
            self.identification_number,
            self.identification_type,
            self.verification_digit,
        )
        text(self.first_name, "first_name", maximum=100)
        text(self.family_name, "family_name", maximum=100)
        for name, value in (
            ("job_title", self.job_title),
            ("nationality_id", self.nationality_id),
            ("organization_department", self.organization_department),
        ):
            if value is not None:
                text(
                    value,
                    name,
                    maximum=200 if name == "organization_department" else 100,
                )


@dataclass(frozen=True, slots=True, kw_only=True)
class RadianInvoiceReference:
    """A sales invoice CUFE and its original maturity date."""

    document_number: str
    uuid: str
    due_date: dt.date | None = None

    def __post_init__(self) -> None:
        text(self.document_number, "document_number", maximum=100)
        digest(self.uuid, "uuid")
        if self.due_date is not None:
            native_date(self.due_date, "due_date")

    @property
    def document_type(self) -> DocumentType:
        """Return the fixed RADIAN title-value invoice reference code."""
        return DocumentType.SALES_INVOICE


@dataclass(frozen=True, slots=True, kw_only=True)
class RadianEventReference:
    """Number and CUDE of a previously registered event, not an invoice."""

    document_number: str
    uuid: str

    def __post_init__(self) -> None:
        text(self.document_number, "document_number", maximum=50)
        digest(self.uuid, "uuid")

    @property
    def document_type(self) -> DocumentType:
        """Return ApplicationResponse (96), never invoice code 01."""
        return DocumentType.APPLICATION_RESPONSE


@dataclass(frozen=True, slots=True, kw_only=True)
class RadianParticipation:
    """One ordered financial participation; blank endorsers can omit identity."""

    amount: Decimal
    party: RadianParty | None = None
    factor_type: FactorType | None = None

    def __post_init__(self) -> None:
        decimal_value(self.amount, "participation amount")
        if self.party is not None and not isinstance(self.party, RadianParty):
            raise TypeError("party must be a RadianParty or None.")
        if self.factor_type is not None and not isinstance(
            self.factor_type, FactorType
        ):
            raise TypeError("factor_type must be a FactorType or None.")


def participations(
    values: tuple[RadianParticipation, ...],
    *,
    blank: bool = False,
    sender: bool = False,
    anonymous: bool = False,
) -> None:
    """Validate ordered participants without deduplicating or reordering them."""
    if not isinstance(values, tuple) or not values:
        raise ValueError("Participations must be a nonempty tuple.")
    for value in values:
        if not isinstance(value, RadianParticipation):
            raise TypeError("Expected RadianParticipation members.")
        if value.party is None:
            if not anonymous:
                raise ValueError("Participant identity is required.")
        elif not blank:
            named_party(value.party, sender=sender)
        if anonymous and value.party is not None:
            raise ValueError("Blank endorsers must omit their identity.")


def participation_sum(values: tuple[RadianParticipation, ...]) -> Decimal:
    """Sum without using the consumer's potentially low Decimal precision."""
    with localcontext() as context:
        context.prec = 50 + len(str(len(values)))
        return sum((value.amount for value in values), Decimal(0))


def event_inputs(
    header: RadianEventHeader, reference: object, reference_type: type
) -> None:
    """Validate composition boundaries before any serialization or signing."""
    if not isinstance(header, RadianEventHeader):
        raise TypeError("header must be a RadianEventHeader.")
    if not isinstance(reference, reference_type):
        raise TypeError(f"reference must be a {reference_type.__name__}.")


def currency(value: CurrencyCode) -> None:
    """Require a versioned currency member instead of accepting arbitrary strings."""
    if not isinstance(value, CurrencyCode):
        raise TypeError("currency must be a CurrencyCode.")


def maturity(reference: RadianInvoiceReference) -> None:
    """Require the original due date only where this event profile requires it."""
    if reference.due_date is None:
        raise ValueError("This event requires the invoice due_date.")

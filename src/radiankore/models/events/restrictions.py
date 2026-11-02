"""Authority restrictions with complete repeatable DocumentResponse groups."""

from dataclasses import dataclass
from decimal import Decimal

from radiankore.catalogs import EventType, RadianOperationType
from radiankore.models.events.attachments import RadianPdfAttachment, pdf_attachment
from radiankore.models.events.notes import validate_event_notes
from radiankore.models.events.radian_common import (
    RadianEventHeader,
    RadianEventReference,
    RadianInvoiceReference,
    RadianParty,
    decimal_value,
    event_inputs,
    named_party,
    operation,
)


def authority_parties(values: tuple[RadianParty, ...], *, sender: bool) -> None:
    """Keep all ordered authority identities, including intentional repetitions."""
    if not isinstance(values, tuple) or not values:
        raise ValueError("authorities/officials must be a nonempty tuple.")
    for party in values:
        named_party(party, sender=sender)


@dataclass(frozen=True, slots=True, kw_only=True)
class RestrictionDocumentReference:
    """One target with its own exact PDF evidence and ordered officials."""

    reference: RadianInvoiceReference | RadianEventReference
    officials: tuple[RadianParty, ...]
    attachment: RadianPdfAttachment

    def __post_init__(self) -> None:
        if not isinstance(
            self.reference, (RadianInvoiceReference, RadianEventReference)
        ):
            raise TypeError("reference must identify an invoice or prior event.")
        authority_parties(self.officials, sender=False)
        pdf_attachment(self.attachment, "Mandamiento de pago emitido por un Juez PDF")


@dataclass(frozen=True, slots=True, kw_only=True)
class CirculationRestrictionResponse:
    """One 041 DocumentResponse, containing one or more invoice references."""

    references: tuple[RestrictionDocumentReference, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.references, tuple) or not self.references:
            raise ValueError("references must be a nonempty tuple.")
        for item in self.references:
            if not isinstance(item, RestrictionDocumentReference):
                raise TypeError("references must contain RestrictionDocumentReference.")
            if not isinstance(item.reference, RadianInvoiceReference):
                raise TypeError("041 must reference invoices, not events.")


@dataclass(frozen=True, slots=True, kw_only=True)
class CirculationRestrictionTerminationResponse:
    """One 042 DocumentResponse with exactly one prior restriction reference."""

    reference: RestrictionDocumentReference

    def __post_init__(self) -> None:
        if not isinstance(self.reference, RestrictionDocumentReference):
            raise TypeError("reference must be a RestrictionDocumentReference.")
        if not isinstance(self.reference.reference, RadianEventReference):
            raise TypeError("042 must reference a prior event, not an invoice.")


def _responses(values: object, expected: type) -> None:
    if not isinstance(values, tuple) or not values:
        raise ValueError("responses must be a nonempty tuple.")
    if any(not isinstance(value, expected) for value in values):
        raise TypeError(f"responses must contain {expected.__name__} instances.")


@dataclass(frozen=True, slots=True, kw_only=True)
class CirculationRestrictionEvent:
    """Record an authority's measure across all declared response/reference groups."""

    header: RadianEventHeader
    operation_type: RadianOperationType
    authorities: tuple[RadianParty, ...]
    responses: tuple[CirculationRestrictionResponse, ...]
    measure_value: Decimal

    def __post_init__(self) -> None:
        operation(self.operation_type, ("411", "412"))
        _responses(self.responses, CirculationRestrictionResponse)
        event_inputs(self.header, self.reference, RadianInvoiceReference)
        authority_parties(self.authorities, sender=True)
        validate_event_notes(
            self.header.notes, code=self.code.value, operation=self.operation_type.value
        )
        decimal_value(self.measure_value, "measure_value")

    @property
    def reference(self) -> RadianInvoiceReference:
        """Return the first XML reference selected by the annex's CUDE/QR XPath."""
        reference = self.responses[0].references[0].reference
        assert isinstance(reference, RadianInvoiceReference)
        return reference

    @property
    def code(self) -> EventType:
        """Return the fixed restriction ResponseCode."""
        return EventType.CIRCULATION_RESTRICTION


@dataclass(frozen=True, slots=True, kw_only=True)
class CirculationRestrictionTerminationEvent:
    """Terminate restrictions, retaining each response's own evidence and officials."""

    header: RadianEventHeader
    operation_type: RadianOperationType
    authorities: tuple[RadianParty, ...]
    responses: tuple[CirculationRestrictionTerminationResponse, ...]
    debt_value: Decimal
    restriction_value: Decimal

    def __post_init__(self) -> None:
        operation(self.operation_type, ("421", "422"))
        _responses(self.responses, CirculationRestrictionTerminationResponse)
        event_inputs(self.header, self.reference, RadianEventReference)
        authority_parties(self.authorities, sender=True)
        validate_event_notes(
            self.header.notes, code=self.code.value, operation=self.operation_type.value
        )
        decimal_value(self.debt_value, "debt_value")
        decimal_value(self.restriction_value, "restriction_value")

    @property
    def reference(self) -> RadianEventReference:
        """Return the first referenced event used for the CUDE and QR."""
        reference = self.responses[0].reference.reference
        assert isinstance(reference, RadianEventReference)
        return reference

    @property
    def code(self) -> EventType:
        """Return the fixed restriction termination ResponseCode."""
        return EventType.CIRCULATION_RESTRICTION_TERMINATION

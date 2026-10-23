"""Authority-imposed circulation restrictions and their explicit termination."""

from dataclasses import dataclass
from decimal import Decimal

from radiankore.catalogs import EventType, RadianOperationType
from radiankore.models.events.attachments import RadianPdfAttachment, pdf_attachment
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


def authority_evidence(
    authorities: tuple[RadianParty, ...],
    officials: tuple[RadianParty, ...],
    attachment: RadianPdfAttachment,
) -> None:
    """Validate ordered authority/official groups and the statutory PDF literal."""
    for name, parties in (("authorities", authorities), ("officials", officials)):
        if not isinstance(parties, tuple) or not parties:
            raise ValueError(f"{name} must be a nonempty tuple.")
        for party in parties:
            named_party(party, sender=name == "authorities")
    pdf_attachment(attachment, "Mandamiento de pago emitido por un Juez PDF")


@dataclass(frozen=True, slots=True, kw_only=True)
class CirculationRestrictionEvent:
    """Record an authority's measure against an invoice CUFE."""

    header: RadianEventHeader
    operation_type: RadianOperationType
    reference: RadianInvoiceReference
    authorities: tuple[RadianParty, ...]
    officials: tuple[RadianParty, ...]
    attachment: RadianPdfAttachment
    measure_value: Decimal

    def __post_init__(self) -> None:
        operation(self.operation_type, ("411", "412"))
        event_inputs(self.header, self.reference, RadianInvoiceReference)
        authority_evidence(self.authorities, self.officials, self.attachment)
        decimal_value(self.measure_value, "measure_value")

    @property
    def code(self) -> EventType:
        """Return the fixed restriction ResponseCode."""
        return EventType.CIRCULATION_RESTRICTION


@dataclass(frozen=True, slots=True, kw_only=True)
class CirculationRestrictionTerminationEvent:
    """Terminate an existing restriction by its CUDE, never by invoice CUFE."""

    header: RadianEventHeader
    operation_type: RadianOperationType
    reference: RadianEventReference
    authorities: tuple[RadianParty, ...]
    officials: tuple[RadianParty, ...]
    attachment: RadianPdfAttachment
    debt_value: Decimal
    restriction_value: Decimal

    def __post_init__(self) -> None:
        operation(self.operation_type, ("421", "422"))
        event_inputs(self.header, self.reference, RadianEventReference)
        authority_evidence(self.authorities, self.officials, self.attachment)
        decimal_value(self.debt_value, "debt_value")
        decimal_value(self.restriction_value, "restriction_value")

    @property
    def code(self) -> EventType:
        """Return the fixed restriction termination ResponseCode."""
        return EventType.CIRCULATION_RESTRICTION_TERMINATION

"""RADIAN protests with an explicit notarial act and conditional acceptance data."""

import datetime as dt
from dataclasses import dataclass
from decimal import Decimal, localcontext

from radiankore.catalogs import AcceptanceFailureType, EventType, RadianOperationType
from radiankore.models.events._validation import text
from radiankore.models.events.attachments import RadianPdfAttachment, pdf_attachment
from radiankore.models.events.notes import validate_event_notes
from radiankore.models.events.radian_common import (
    RadianEventHeader,
    RadianInvoiceReference,
    RadianParty,
    additional_senders,
    decimal_value,
    event_inputs,
    maturity,
    named_party,
    native_date,
    operation,
)


@dataclass(frozen=True, slots=True, kw_only=True)
class ProtestNotary:
    """Notary fields specified by the act; no fictitious identity is invented."""

    first_name: str
    family_name: str
    job_title: str

    def __post_init__(self) -> None:
        for name in ("first_name", "family_name", "job_title"):
            text(getattr(self, name), name, maximum=100)


@dataclass(frozen=True, slots=True, kw_only=True)
class ProtestAct:
    """Evidence and issuer of the notarial act embedded in LineResponse."""

    notary_number: str
    effective_date: dt.date
    notaries: tuple[ProtestNotary, ...]
    attachment: RadianPdfAttachment

    def __post_init__(self) -> None:
        text(self.notary_number, "notary_number")
        if not self.notary_number.isascii() or not self.notary_number.isdecimal():
            raise ValueError("notary_number must contain digits.")
        native_date(self.effective_date, "effective_date")
        if not isinstance(self.notaries, tuple) or not self.notaries:
            raise ValueError("notaries must be a nonempty tuple.")
        if any(not isinstance(p, ProtestNotary) for p in self.notaries):
            raise TypeError("notaries must contain ProtestNotary members.")
        pdf_attachment(self.attachment, "Acta de protesto, PDF")


@dataclass(frozen=True, slots=True, kw_only=True)
class ProtestDocumentResponse:
    """One 048 response with all invoice references and its own notarial act."""

    references: tuple[RadianInvoiceReference, ...]
    act: ProtestAct

    def __post_init__(self) -> None:
        if not isinstance(self.references, tuple) or not self.references:
            raise ValueError("references must be a nonempty tuple.")
        for reference in self.references:
            if not isinstance(reference, RadianInvoiceReference):
                raise TypeError("references must contain RadianInvoiceReference.")
            maturity(reference)
        if not isinstance(self.act, ProtestAct):
            raise TypeError("act must be a ProtestAct.")


@dataclass(frozen=True, slots=True, kw_only=True)
class ProtestEvent:
    """Acceptance/payment protest; acceptance amounts are exclusive to 481."""

    header: RadianEventHeader
    operation_type: RadianOperationType
    sender_party: RadianParty
    receiver_party: RadianParty
    responses: tuple[ProtestDocumentResponse, ...]
    title_value: Decimal
    acceptance_failure: AcceptanceFailureType | None = None
    accepted_value: Decimal | None = None
    pending_value: Decimal | None = None

    additional_sender_parties: tuple[RadianParty, ...] = ()

    def __post_init__(self) -> None:
        operation(self.operation_type, ("481", "482"))
        if not isinstance(self.responses, tuple) or not self.responses:
            raise ValueError("responses must be a nonempty tuple.")
        if any(
            not isinstance(item, ProtestDocumentResponse) for item in self.responses
        ):
            raise TypeError("responses must contain ProtestDocumentResponse instances.")
        event_inputs(self.header, self.reference, RadianInvoiceReference)
        additional_senders(self.additional_sender_parties)
        validate_event_notes(
            self.header.notes, code=self.code.value, operation=self.operation_type.value
        )
        maturity(self.reference)
        named_party(self.sender_party, sender=True)
        named_party(self.receiver_party)
        decimal_value(self.title_value, "title_value", positive=True)
        if self.operation_type is RadianOperationType.PROTEST_NON_ACCEPTANCE:
            if not isinstance(self.acceptance_failure, AcceptanceFailureType):
                raise TypeError("481 requires an AcceptanceFailureType.")
            decimal_value(self.accepted_value, "accepted_value")  # type: ignore[arg-type]
            decimal_value(self.pending_value, "pending_value", positive=True)  # type: ignore[arg-type]
            assert self.accepted_value is not None and self.pending_value is not None
            with localcontext() as context:
                context.prec = 50
                if self.accepted_value + self.pending_value != self.title_value:
                    raise ValueError(
                        "accepted_value + pending_value must equal title_value."
                    )
            partial = self.acceptance_failure is AcceptanceFailureType.PARTIAL
            if partial != (self.accepted_value > 0):
                raise ValueError(
                    "Acceptance amounts must agree with partial/total failure."
                )
        elif any(
            v is not None
            for v in (self.acceptance_failure, self.accepted_value, self.pending_value)
        ):
            raise ValueError("Acceptance failure data is only applicable to 481.")

    @property
    def reference(self) -> RadianInvoiceReference:
        """Return the first reference used by the CUDE and QR XPath."""
        return self.responses[0].references[0]

    @property
    def code(self) -> EventType:
        """Return the fixed protest ResponseCode."""
        return EventType.PROTEST

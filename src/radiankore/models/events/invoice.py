"""Immutable emission inputs for invoice ApplicationResponse events 030-034."""

import datetime as dt
from dataclasses import dataclass

from radiankore.catalogs import (
    DocumentType,
    EventType,
    IdentificationType,
    InvoiceClaimReason,
    OrganizationType,
    PartyTaxScheme,
)
from radiankore.models.events._validation import digest, identity, text

INVOICE_EVENT_TYPES = frozenset(
    (
        EventType.INVOICE_ACKNOWLEDGEMENT,
        EventType.INVOICE_CLAIM,
        EventType.GOODS_OR_SERVICES_RECEIPT,
        EventType.EXPRESS_ACCEPTANCE,
        EventType.TACIT_ACCEPTANCE,
    )
)


def invoice_event_code(value: EventType) -> None:
    """Require an existing EventType member supported by this emission API."""
    if not isinstance(value, EventType):
        raise TypeError("code must be an EventType.")
    if value not in INVOICE_EVENT_TYPES:
        raise ValueError("Only invoice event codes 030-034 are supported.")


@dataclass(frozen=True, slots=True, kw_only=True)
class InvoiceEventParty:
    """Event participant; organization and tax details are explicitly supplied."""

    name: str
    tax_number: str
    identification_type: IdentificationType
    organization_type: OrganizationType
    verification_digit: str | None = None
    tax_scheme: PartyTaxScheme = PartyTaxScheme.VAT

    def __post_init__(self) -> None:
        text(self.name, "name", maximum=450)
        identity(self.tax_number, self.identification_type, self.verification_digit)
        if not isinstance(self.organization_type, OrganizationType):
            raise TypeError("organization_type must be an OrganizationType.")
        if not isinstance(self.tax_scheme, PartyTaxScheme):
            raise TypeError("tax_scheme must be a PartyTaxScheme.")


@dataclass(frozen=True, slots=True, kw_only=True)
class InvoiceEventPerson:
    """Person who received the invoice or goods/services, not the XML signer."""

    identification_number: str
    identification_type: IdentificationType
    first_name: str
    family_name: str
    verification_digit: str | None = None
    job_title: str | None = None
    organization_department: str | None = None

    def __post_init__(self) -> None:
        identity(
            self.identification_number,
            self.identification_type,
            self.verification_digit,
        )
        for name, value in (
            ("first_name", self.first_name),
            ("family_name", self.family_name),
        ):
            text(value, name, maximum=100)
        for name, optional_value in (
            ("job_title", self.job_title),
            ("organization_department", self.organization_department),
        ):
            if optional_value is not None:
                text(optional_value, name, maximum=100)


@dataclass(frozen=True, slots=True, kw_only=True)
class InvoiceEventDocumentReference:
    """One invoice and its original CUFE; defaults to a sales invoice (01)."""

    document_number: str
    uuid: str
    document_type: DocumentType = DocumentType.SALES_INVOICE

    def __post_init__(self) -> None:
        text(self.document_number, "document_number")
        digest(self.uuid, "uuid")
        if not isinstance(self.document_type, DocumentType):
            raise TypeError("document_type must be a DocumentType.")
        if self.document_type not in (
            DocumentType.SALES_INVOICE,
            DocumentType.EXPORT_INVOICE,
            DocumentType.PAPER_INVOICE_TRANSMISSION,
            DocumentType.DIAN_CONTINGENCY_INVOICE,
        ):
            raise ValueError("Invoice events must reference invoice types 01-04.")


@dataclass(frozen=True, slots=True, kw_only=True)
class InvoiceResponseEvent:
    """Validated event inputs; notes and sworn statements remain caller supplied.

    Events 030-033 require the invoice issuer as receiver. Event 034 targets DIAN
    internally and requires notes containing the applicable sworn statement.
    Business deadlines, prior events and representation are caller responsibilities.
    """

    code: EventType
    event_number: str
    issue_date: dt.date
    issue_time: dt.time
    sender_party: InvoiceEventParty
    document_reference: InvoiceEventDocumentReference
    receiver_party: InvoiceEventParty | None = None
    issuer_person: InvoiceEventPerson | None = None
    claim_reason: InvoiceClaimReason | None = None
    notes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        invoice_event_code(self.code)
        text(self.event_number, "event_number", maximum=50)
        if type(self.issue_date) is not dt.date:
            raise TypeError("issue_date must be a native date.")
        if not isinstance(self.issue_time, dt.time):
            raise TypeError("issue_time must be a native time.")
        if not isinstance(self.sender_party, InvoiceEventParty):
            raise TypeError("sender_party must be an InvoiceEventParty.")
        if self.sender_party.identification_type is not IdentificationType.NIT:
            raise ValueError("sender_party must be identified by NIT.")
        if not isinstance(self.document_reference, InvoiceEventDocumentReference):
            raise TypeError(
                "document_reference must be an InvoiceEventDocumentReference."
            )
        if self.code is EventType.TACIT_ACCEPTANCE:
            if self.receiver_party is not None:
                raise ValueError(
                    "Event 034 uses the internally generated DIAN receiver."
                )
        elif not isinstance(self.receiver_party, InvoiceEventParty):
            raise TypeError(
                "Events 030-033 require an InvoiceEventParty receiver_party."
            )
        if self.code in (
            EventType.INVOICE_ACKNOWLEDGEMENT,
            EventType.GOODS_OR_SERVICES_RECEIPT,
        ):
            if not isinstance(self.issuer_person, InvoiceEventPerson):
                raise TypeError("Events 030 and 032 require an InvoiceEventPerson.")
        elif self.issuer_person is not None:
            raise ValueError("issuer_person is only applicable to events 030 and 032.")
        if self.code is EventType.INVOICE_CLAIM:
            if not isinstance(self.claim_reason, InvoiceClaimReason):
                raise TypeError("Event 031 requires an InvoiceClaimReason.")
        elif self.claim_reason is not None:
            raise ValueError("claim_reason is only applicable to event 031.")
        if not isinstance(self.notes, tuple):
            raise TypeError("notes must be a tuple.")
        for note in self.notes:
            text(note, "note", maximum=10_000)
        if self.code is EventType.TACIT_ACCEPTANCE and not self.notes:
            raise ValueError("Event 034 requires an explicit sworn statement in notes.")

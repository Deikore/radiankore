"""Typed operation results returned by the public client."""

from radiankore.models.responses.acquirer import AcquirerResult
from radiankore.models.responses.document_info import (
    DocumentCorrection,
    DocumentEvent,
    DocumentHolder,
    DocumentInfo,
    DocumentInfoResult,
    DocumentNote,
    DocumentNumber,
    DocumentParty,
    DocumentReference,
    DocumentState,
    DocumentTotals,
    DocumentValidation,
)
from radiankore.models.responses.document_status import DocumentStatusResult
from radiankore.models.responses.exchange_emails import ExchangeEmailsResult
from radiankore.models.responses.invoice_events import (
    EventParty,
    InvoiceEvent,
    InvoiceEventsResult,
)
from radiankore.models.responses.numbering_range import (
    NumberingRange,
    NumberingRangeResult,
)
from radiankore.models.responses.reference_notes import (
    NoteDocumentReference,
    NoteLineResponse,
    NoteResponse,
    ReferenceNote,
    ReferenceNotesResult,
)
from radiankore.models.responses.send_event import SendEventResult
from radiankore.models.responses.xml_document import XmlDocumentResult

__all__ = [
    "AcquirerResult",
    "DocumentCorrection",
    "DocumentEvent",
    "DocumentHolder",
    "DocumentInfo",
    "DocumentInfoResult",
    "DocumentNote",
    "DocumentNumber",
    "DocumentParty",
    "DocumentReference",
    "DocumentState",
    "DocumentStatusResult",
    "DocumentTotals",
    "DocumentValidation",
    "EventParty",
    "ExchangeEmailsResult",
    "InvoiceEvent",
    "InvoiceEventsResult",
    "NoteDocumentReference",
    "NoteLineResponse",
    "NoteResponse",
    "NumberingRange",
    "NumberingRangeResult",
    "ReferenceNote",
    "ReferenceNotesResult",
    "SendEventResult",
    "XmlDocumentResult",
]

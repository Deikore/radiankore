"""Immutable GetReferenceNotes metadata and independent binary payloads."""

import datetime as dt
from dataclasses import dataclass, field

from radiankore.catalogs import DocumentType
from radiankore.models.responses.invoice_events import EventParty


@dataclass(frozen=True, slots=True, kw_only=True)
class NoteDocumentReference:
    """One referenced note document, retaining its original identifier text."""

    id: str
    uuid: str | None = None


@dataclass(frozen=True, slots=True, kw_only=True)
class NoteResponse:
    """A line-level response with a textual code and native effective date/time."""

    reference_id: str | None = None
    code: str | None = None
    description: str = ""
    date: dt.date | None = None
    time: dt.time | None = None


@dataclass(frozen=True, slots=True, kw_only=True)
class NoteLineResponse:
    """One identified line with all of its responses in XML order."""

    line_id: str
    responses: tuple[NoteResponse, ...] = ()


@dataclass(frozen=True, slots=True, kw_only=True)
class ReferenceNote:
    """One DocumentResponse, distinct from RADIAN events and DocumentInfo notes."""

    reference_id: str | None = None
    code: DocumentType | None = None
    description: str = ""
    date: dt.date | None = None
    time: dt.time | None = None
    references: tuple[NoteDocumentReference, ...] = ()
    issuer: EventParty | None = None
    recipient: EventParty | None = None
    line_responses: tuple[NoteLineResponse, ...] = ()

    def __post_init__(self) -> None:
        """Accept only credit/debit DocumentType members or None."""
        if self.code is None:
            return
        if not isinstance(self.code, DocumentType):
            raise TypeError("code must be a DocumentType or None.")
        if self.code not in {DocumentType.CREDIT_NOTE, DocumentType.DEBIT_NOTE}:
            raise ValueError("code must be CREDIT_NOTE or DEBIT_NOTE.")


@dataclass(frozen=True, slots=True, kw_only=True)
class ReferenceNotesResult:
    """DianResponse metadata, typed notes and independently decoded payloads.

    Notes are parsed from xml_base64_bytes, whose original bytes are retained.
    xml_bytes is independent and is never used as a fallback or decompressed.
    """

    is_valid: bool | None = None
    status_code: str | None = None
    status_description: str | None = None
    status_message: str | None = None
    messages: tuple[str | None, ...] = ()
    document_key: str | None = None
    file_name: str | None = None
    xml_base64_bytes: bytes | None = field(default=None, repr=False)
    xml_bytes: bytes | None = field(default=None, repr=False)
    notes: tuple[ReferenceNote, ...] = ()

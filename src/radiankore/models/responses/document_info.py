"""Immutable GetDocumentInfo records matching the published DIAN data contracts.

Date fields use native Python dates parsed from ISO calendar dates.
Collections preserve XML order and nullable items where the schema permits them.
"""

import datetime as dt
from dataclasses import dataclass, field
from decimal import Decimal
from http import HTTPStatus

from radiankore.catalogs import (
    CreditNoteReason,
    DebitNoteReason,
    DocumentType,
    EventType,
    IdentificationType,
)


@dataclass(frozen=True, slots=True, kw_only=True)
class DocumentParty:
    """An Entidad, including its origin and optional identification type."""

    name: str | None = None
    tax_number: str | None = None
    identification_type: IdentificationType | None = None
    identification_type_raw: str | None = None
    origin: str | None = None

    def __post_init__(self) -> None:
        """Require the identification enum without coercing strings."""
        if self.identification_type is not None and not isinstance(
            self.identification_type, IdentificationType
        ):
            raise TypeError(
                "identification_type must be an IdentificationType or None."
            )
        if self.identification_type_raw is not None and not isinstance(
            self.identification_type_raw, str
        ):
            raise TypeError("identification_type_raw must be a string or None.")


@dataclass(frozen=True, slots=True, kw_only=True)
class DocumentNumber:
    """Document series, folio and native issue and signature dates."""

    issue_date: dt.date | None = None
    signature_date: dt.date | None = None
    folio: str | None = None
    series: str | None = None


@dataclass(frozen=True, slots=True, kw_only=True)
class DocumentHolder:
    """Legitimate holder and its native title registration date."""

    name: str | None = None
    title_registration_date: dt.date | None = None


@dataclass(frozen=True, slots=True, kw_only=True)
class DocumentTotals:
    """VAT and total parsed directly into Decimal, without float rounding."""

    vat: Decimal | None = None
    total: Decimal | None = None


@dataclass(frozen=True, slots=True, kw_only=True)
class DocumentState:
    """One Estado key/value entry; duplicate keys are preserved in the sequence."""

    key: int
    value: str | None = None


@dataclass(frozen=True, slots=True, kw_only=True)
class DocumentValidation:
    """Optional DIAN validation flags and uninterpreted status information."""

    is_notification: bool | None = None
    is_valid: bool | None = None
    error_message: str | None = None
    name: str | None = None
    status: str | None = None


@dataclass(frozen=True, slots=True, kw_only=True)
class DocumentCorrection:
    """Correction code, name and description without an inferred code catalog."""

    code: str | None = None
    description: str | None = None
    name: str | None = None


@dataclass(frozen=True, slots=True, kw_only=True)
class DocumentReference:
    """A referenced document with optional parties, type and native date."""

    description: str | None = None
    document_type_id: DocumentType | None = None
    document_type_name: str | None = None
    issuer: DocumentParty | None = None
    recipient: DocumentParty | None = None
    date: dt.date | None = None
    uuid: str | None = None

    def __post_init__(self) -> None:
        """Require a DocumentType member or None without coercing strings."""
        if self.document_type_id is not None and not isinstance(
            self.document_type_id, DocumentType
        ):
            raise TypeError("document_type_id must be a DocumentType or None.")


@dataclass(frozen=True, slots=True, kw_only=True)
class DocumentEvent:
    """An Evento data contract, distinct from the GetStatusEvent UBL record."""

    code: EventType | None = None
    description: str | None = None
    issuer: DocumentParty | None = None
    recipient: DocumentParty | None = None
    number: DocumentNumber | None = None
    references: tuple[DocumentReference | None, ...] = ()
    uuid: str | None = None
    validations: tuple[DocumentValidation | None, ...] = ()

    def __post_init__(self) -> None:
        """Require the event enum without coercing strings."""
        if self.code is not None and not isinstance(self.code, EventType):
            raise TypeError("code must be an EventType or None.")


@dataclass(frozen=True, slots=True, kw_only=True)
class DocumentNote:
    """A Nota returned in DocumentTags, with its own shared nested records."""

    correction: DocumentCorrection | None = None
    document_type_name: str | None = None
    issuer: DocumentParty | None = None
    recipient: DocumentParty | None = None
    number: DocumentNumber | None = None
    holder: DocumentHolder | None = None
    totals: DocumentTotals | None = None
    uuid: str | None = None
    validations: tuple[DocumentValidation | None, ...] = ()


@dataclass(frozen=True, slots=True, kw_only=True)
class DocumentInfo:
    """One Documento with reason enums for known note codes and text otherwise."""

    document_code: CreditNoteReason | DebitNoteReason | str | None = None
    description: str | None = None
    document_type_id: DocumentType | None = None
    document_type_name: str | None = None
    uuid: str | None = None
    issuer: DocumentParty | None = None
    recipient: DocumentParty | None = None
    number: DocumentNumber | None = None
    holder: DocumentHolder | None = None
    totals: DocumentTotals | None = None
    states: tuple[DocumentState, ...] = ()
    events: tuple[DocumentEvent | None, ...] = ()
    references: tuple[DocumentReference | None, ...] = ()
    notes: tuple[DocumentNote | None, ...] = ()
    validations: tuple[DocumentValidation | None, ...] = ()

    def __post_init__(self) -> None:
        """Require the document type and its matching note reason without coercion."""
        if self.document_type_id is not None and not isinstance(
            self.document_type_id, DocumentType
        ):
            raise TypeError("document_type_id must be a DocumentType or None.")
        if self.document_code is None:
            return
        if self.document_type_id is DocumentType.CREDIT_NOTE:
            if type(self.document_code) is not str and not isinstance(
                self.document_code, CreditNoteReason
            ):
                raise TypeError(
                    "document_code must be a CreditNoteReason, text or None."
                )
        elif self.document_type_id is DocumentType.DEBIT_NOTE:
            if type(self.document_code) is not str and not isinstance(
                self.document_code, DebitNoteReason
            ):
                raise TypeError(
                    "document_code must be a DebitNoteReason, text or None."
                )
        elif not isinstance(self.document_code, str) or isinstance(
            self.document_code, (CreditNoteReason, DebitNoteReason)
        ):
            raise TypeError(
                "document_code must be text or None for this document type."
            )


@dataclass(frozen=True, slots=True, kw_only=True)
class DocumentInfoResult:
    """Optional status, structured documents and uninterpreted compressed text.

    compressed_document_info preserves whitespace and empty strings, is omitted
    from repr and is never used as an implicit replacement for documents.
    status_code maps SOAP StatusCode to HTTPStatus, independently of transport.
    """

    status_code: HTTPStatus | None = None
    status_description: str | None = None
    documents: tuple[DocumentInfo | None, ...] = ()
    compressed_document_info: str | None = field(default=None, repr=False)

    def __post_init__(self) -> None:
        """Require an HTTPStatus member or None without coercing other values."""
        if self.status_code is not None and not isinstance(
            self.status_code, HTTPStatus
        ):
            raise TypeError("status_code must be an HTTPStatus or None.")

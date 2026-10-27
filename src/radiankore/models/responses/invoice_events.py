"""Immutable results of an invoice event query."""

import datetime as dt
from dataclasses import dataclass, field

from radiankore.catalogs import EventType, IdentificationType


@dataclass(frozen=True, slots=True, kw_only=True)
class EventParty:
    """Optional identification and registered name of an event participant.

    CompanyID supplies tax_number, schemeID supplies verification_digit, and
    schemeName supplies identification_type when recognized, while
    identification_type_raw preserves the original code or label.
    Identification codes are available through the member's value property.
    """

    tax_number: str | None = None
    name: str | None = None
    verification_digit: str | None = None
    identification_type: IdentificationType | None = None
    identification_type_raw: str | None = None

    def __post_init__(self) -> None:
        """Require an IdentificationType member or None without coercing strings."""
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
class InvoiceEvent:
    """One event record in a GetStatusEvent response.

    ``description`` joins non-empty Response/Description values with newlines.
    ``id`` is required; ``uuid`` and ``id`` identify the first DocumentReference,
    not the root document. ``code`` is the optional Response/ResponseCode,
    represented by an EventType member.
    ``reference_id`` is the separate Response/ReferenceID value. ``date`` and
    ``time`` come from Response/EffectiveDate and Response/EffectiveTime, without
    falling back to the containing ApplicationResponse's issue date or time.
    Parsed times use Colombia's fixed UTC-05:00 offset; the date is adjusted
    when conversion crosses midnight. Times without an offset are local to
    Colombia. Missing dates and times remain None.
    """

    id: str
    code: EventType | None = None
    description: str = ""
    reference_id: str | None = None
    date: dt.date | None = None
    time: dt.time | None = None
    uuid: str | None = None
    issuer: EventParty | None = None
    recipient: EventParty | None = None

    def __post_init__(self) -> None:
        """Require an EventType member or None without coercing strings."""
        if self.code is not None and not isinstance(self.code, EventType):
            raise TypeError("code must be an EventType or None.")


@dataclass(frozen=True, slots=True, kw_only=True)
class InvoiceEventsResult:
    """DIAN status metadata and ordered events, with optional decoded source XML.

    ``events`` is sorted by numeric ReferenceID, with missing or nonnumeric
    references last. Equal keys preserve XML order; no events are deduplicated.
    ``messages`` preserves ErrorMessage entries, including notifications on
    successful results. ``document_key`` and ``file_name`` preserve DIAN's
    XmlDocumentKey and XmlFileName values without inferring their meaning.
    """

    is_valid: bool
    status_code: str
    status_description: str | None = None
    status_message: str | None = None
    messages: tuple[str, ...] = ()
    document_key: str | None = None
    file_name: str | None = None
    events: tuple[InvoiceEvent, ...] = ()
    application_response_xml: bytes | None = field(default=None, repr=False)

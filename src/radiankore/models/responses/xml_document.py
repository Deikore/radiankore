"""Immutable downloaded document and its EventResponse metadata."""

import datetime as dt
from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True, kw_only=True)
class XmlDocumentResult:
    """Decoded document bytes, retaining their original encoding and formatting.

    validation_date preserves the received precision: date for ISO dates and
    datetime for ISO timestamps, including any supplied timezone offset.
    """

    status_code: str | None = None
    message: str | None = None
    validation_date: dt.date | dt.datetime | None = None
    document_xml: bytes | None = field(default=None, repr=False)

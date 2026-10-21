"""Immutable downloaded document and its EventResponse metadata."""

import datetime as dt
from dataclasses import dataclass, field
from http import HTTPStatus


@dataclass(frozen=True, slots=True, kw_only=True)
class XmlDocumentResult:
    """Decoded document bytes, retaining their original encoding and formatting.

    validation_date preserves the received precision: date for ISO dates and
    datetime for ISO timestamps, including any supplied timezone offset.
    status_code maps the SOAP Code to HTTPStatus, independently of HTTP transport.
    """

    status_code: HTTPStatus | None = None
    message: str | None = None
    validation_date: dt.date | dt.datetime | None = None
    document_xml: bytes | None = field(default=None, repr=False)

    def __post_init__(self) -> None:
        """Require an HTTPStatus member or None without coercing other values."""
        if self.status_code is not None and not isinstance(
            self.status_code, HTTPStatus
        ):
            raise TypeError("status_code must be an HTTPStatus or None.")

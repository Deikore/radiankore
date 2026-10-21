"""Immutable document validation status returned by GetStatus."""

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True, kw_only=True)
class DocumentStatusResult:
    """DianResponse metadata and independent, uninterpreted decoded payloads.

    A negative is_valid flag is a business result, not a transport error.
    Both binary fields retain their exact bytes and are omitted from repr.
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

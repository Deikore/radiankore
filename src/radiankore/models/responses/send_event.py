"""Result of sending a RADIAN event through SendEventUpdateStatus."""

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True, kw_only=True)
class SendEventResult:
    """DIAN synchronous response to an emitted event.

    Both binary fields are independently base64-decoded without interpreting
    their XML. ``messages`` preserves validation messages in order.
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

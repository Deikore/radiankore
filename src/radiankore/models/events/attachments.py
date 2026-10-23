"""In-memory evidence shared by authority and protest event profiles."""

from dataclasses import dataclass, field

from radiankore.models.events._validation import text


@dataclass(frozen=True, slots=True, kw_only=True)
class RadianPdfAttachment:
    """Caller-supplied PDF bytes; profile-specific XML metadata is fixed separately."""

    filename: str
    content_bytes: bytes = field(repr=False)

    def __post_init__(self) -> None:
        text(self.filename, "filename")
        if not isinstance(self.content_bytes, bytes):
            raise TypeError("content_bytes must be immutable bytes.")
        if not self.content_bytes.startswith(b"%PDF-"):
            raise ValueError("Attachment must contain PDF bytes.")


def pdf_attachment(value: RadianPdfAttachment, filename: str) -> None:
    """Validate evidence and the filename literal mandated by the DIAN profile."""
    if not isinstance(value, RadianPdfAttachment):
        raise TypeError("attachment must be a RadianPdfAttachment.")
    if value.filename != filename:
        raise ValueError(f"This profile requires filename {filename!r}.")

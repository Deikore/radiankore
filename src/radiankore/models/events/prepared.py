"""Software credentials and prepared event artifacts."""

from dataclasses import dataclass, field
from typing import Literal

from radiankore.catalogs import EventType, IdentificationType
from radiankore.environment import Environment
from radiankore.models.events._validation import identity as _identity
from radiankore.models.events._validation import text as _text


@dataclass(frozen=True, slots=True, kw_only=True)
class RadianSoftware:
    """DIAN software credentials; PIN never appears in the representation."""

    software_id: str
    pin: str = field(repr=False)
    provider_tax_number: str
    provider_verification_digit: str
    signer_role: Literal["supplier", "thirdparty"]

    def __post_init__(self) -> None:
        _text(self.software_id, "software_id")
        _text(self.pin, "pin")
        _identity(
            self.provider_tax_number,
            IdentificationType.NIT,
            self.provider_verification_digit,
        )
        if self.signer_role not in ("supplier", "thirdparty"):
            raise ValueError("signer_role must be supplier or thirdparty.")


def _validate_prepared(
    event_number: str,
    cude: str,
    environment: Environment,
    xml_bytes: bytes,
    zip_bytes: bytes,
) -> None:
    """Validate common artifact fields without coupling one event to another."""
    _text(event_number, "event_number")
    if not isinstance(environment, Environment):
        raise TypeError("environment must be an Environment.")
    if not isinstance(xml_bytes, bytes) or not isinstance(zip_bytes, bytes):
        raise TypeError("Prepared XML and ZIP must be immutable bytes.")
    if not xml_bytes or not zip_bytes:
        raise ValueError("Prepared XML and ZIP must not be empty.")
    if (
        not isinstance(cude, str)
        or len(cude) != 96
        or any(c not in "0123456789abcdef" for c in cude)
    ):
        raise ValueError("cude must be a 96-character lowercase hexadecimal digest.")


@dataclass(frozen=True, slots=True, kw_only=True)
class PreparedRadianEvent:
    """Exact, signed bytes for a supported RADIAN event code."""

    code: EventType
    event_number: str
    cude: str
    environment: Environment
    xml_bytes: bytes = field(repr=False)
    zip_bytes: bytes = field(repr=False)

    def __post_init__(self) -> None:
        if not isinstance(self.code, EventType):
            raise TypeError("code must be an EventType.")
        if self.code in (EventType.DIAN_VALIDATED, EventType.DIAN_REJECTED):
            raise ValueError("Unsupported code for a PreparedRadianEvent.")
        _validate_prepared(
            self.event_number,
            self.cude,
            self.environment,
            self.xml_bytes,
            self.zip_bytes,
        )

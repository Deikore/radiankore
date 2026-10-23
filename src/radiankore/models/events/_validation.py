"""Pure input validation shared by event models, independent of XML and I/O."""

from radiankore.catalogs import IdentificationType


def text(value: str, name: str, *, maximum: int | None = None) -> None:
    """Require nonblank text without modifying the caller's value."""
    if not isinstance(value, str):
        raise TypeError(f"{name} must be a string.")
    if not value.strip():
        raise ValueError(f"{name} must not be empty.")
    if maximum is not None and len(value) > maximum:
        raise ValueError(f"{name} must contain at most {maximum} characters.")


def identity(number: str, kind: IdentificationType, digit: str | None) -> None:
    """Validate an identity; only NIT uses a caller-supplied verification digit."""
    text(number, "identification number")
    if not isinstance(kind, IdentificationType):
        raise TypeError("identification_type must be an IdentificationType.")
    if kind is IdentificationType.NIT:
        if not number.isascii() or not number.isdecimal():
            raise ValueError("NIT must contain digits without the verification digit.")
        if digit is None or len(digit) != 1 or digit not in "0123456789":
            raise ValueError("NIT requires a single verification digit.")
    elif digit is not None:
        raise ValueError("verification_digit is only applicable to NIT.")


def digest(value: str, name: str, *, lowercase: bool = False) -> None:
    """Require a SHA-384 hexadecimal identifier, preserving its original bytes."""
    alphabet = "0123456789abcdef" if lowercase else "0123456789abcdefABCDEF"
    if (
        not isinstance(value, str)
        or len(value) != 96
        or any(c not in alphabet for c in value)
    ):
        raise ValueError(f"{name} must be a 96-character hexadecimal digest.")

"""Immutable numbering ranges and operation metadata returned by DIAN."""

from dataclasses import dataclass, field
from datetime import date


@dataclass(frozen=True, slots=True, kw_only=True)
class NumberingRange:
    """One authorization, native calendar dates and optional signed 64-bit bounds."""

    resolution_number: str | None = None
    resolution_date: date | None = None
    prefix: str | None = None
    from_number: int | None = None
    to_number: int | None = None
    valid_date_from: date | None = None
    valid_date_to: date | None = None
    technical_key: str | None = field(default=None, repr=False)


@dataclass(frozen=True, slots=True, kw_only=True)
class NumberingRangeResult:
    """Uninterpreted business status and ranges in XML order, including nil items."""

    operation_code: str | None = None
    operation_description: str | None = None
    ranges: tuple[NumberingRange | None, ...] = ()

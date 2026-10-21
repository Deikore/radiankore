"""Immutable result of an acquirer information query."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True, kw_only=True)
class AcquirerResult:
    """Optional GetAcquirer fields, without interpreting DIAN business statuses.

    name and email map ReceiverName and ReceiverEmail. status_code and message
    preserve StatusCode and Message; none of these fields implies success.
    """

    name: str | None = None
    email: str | None = None
    status_code: str | None = None
    message: str | None = None

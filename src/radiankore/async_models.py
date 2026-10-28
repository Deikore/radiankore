"""Configuration and streaming results for the asynchronous public API."""

from dataclasses import dataclass, field
from math import isfinite


def positive(value: float, name: str) -> None:
    """Require positive finite numeric configuration, excluding booleans."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{name} must be a number.")
    if not isfinite(value) or value <= 0:
        raise ValueError(f"{name} must be positive and finite.")


def count(value: int, name: str) -> None:
    """Require a strictly positive integer."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{name} must be an integer.")
    if value <= 0:
        raise ValueError(f"{name} must be positive.")


@dataclass(frozen=True, slots=True, kw_only=True)
class DianTimeouts:
    """HTTP phase timeouts and total operation deadline, in seconds.

    Total includes admission and local processing. None disables only the total
    deadline; a running native function cannot be forcibly stopped on expiry.
    """

    connect: float = 5.0
    read: float = 30.0
    write: float = 30.0
    pool: float = 5.0
    total: float | None = 60.0

    def __post_init__(self) -> None:
        for name in ("connect", "read", "write", "pool"):
            positive(getattr(self, name), name)
        if self.total is not None:
            positive(self.total, "total")


@dataclass(frozen=True, slots=True, kw_only=True)
class QueryResult[T, R]:
    """One completion: index correlates duplicates; error=None denotes success.

    A successful query may return None. Payloads and exceptions are excluded
    from repr because they may carry private data. No retries are performed.
    """

    index: int
    item: T = field(repr=False)
    value: R | None = field(default=None, repr=False)
    error: Exception | None = field(default=None, repr=False)

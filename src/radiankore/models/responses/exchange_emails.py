"""Immutable metadata and downloaded exchange-email directory."""

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True, kw_only=True)
class ExchangeEmailsResult:
    """SOAP metadata and CSV dictionaries parsed in memory.

    status_code preserves the SOAP business code independently of HTTP transport.
    download_url is short-lived; neither the URL nor the records appear in repr.
    The record tuple preserves order; its row dictionaries remain mutable.
    """

    success: bool | None = None
    status_code: str | None = None
    message: str | None = None
    download_url: str | None = field(default=None, repr=False)
    csv: tuple[dict[str, str], ...] | None = field(default=None, repr=False)

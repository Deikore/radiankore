"""HTTP error classification shared by both transports."""

from contextlib import suppress
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from math import isfinite

import httpx

from radiankore._soap.parsing import soap_body
from radiankore.exceptions import DianResponseError, DianTransportError


def retry_after(value: str | None) -> float | None:
    """Read delta-seconds or HTTP-date without retaining the original header."""
    if value is None:
        return None
    try:
        value = value.strip()
        if value.isascii() and value.isdecimal():
            seconds = float(value)
        else:
            stamp = parsedate_to_datetime(value)
            if stamp.tzinfo is None:
                stamp = stamp.replace(tzinfo=UTC)
            seconds = max(0.0, (stamp - datetime.now(UTC)).total_seconds())
        return seconds if isfinite(seconds) else None
    except (ValueError, TypeError, OverflowError):
        return None


def check_response(response: httpx.Response, data: bytes, soap: bool) -> bytes:
    """Preserve SOAP Fault precedence and HTTP error causes."""
    try:
        response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        if soap:
            with suppress(DianResponseError):
                soap_body(data)
        prefix = "DIAN returned" if soap else "DIAN download returned"
        raise DianTransportError(
            f"{prefix} HTTP {response.status_code}.",
            status_code=response.status_code,
            retry_after=retry_after(response.headers.get("Retry-After")),
        ) from exc
    return data

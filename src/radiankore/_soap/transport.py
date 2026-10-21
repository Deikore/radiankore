"""HTTPX transport for signed SOAP messages and exchange-email downloads."""

from contextlib import suppress

import httpx

from radiankore._soap.parsing import soap_body
from radiankore.exceptions import DianResponseError, DianTransportError


def create_http_client(timeout: float) -> httpx.Client:
    """Create an owned client without opening network connections."""
    return httpx.Client(timeout=timeout, follow_redirects=False)


class SoapTransport:
    """Close each operation's HTTP client before returning response bytes."""

    def __init__(self, *, timeout: float) -> None:
        self._timeout = timeout

    def post(self, endpoint: str, payload: bytes, *, action: str) -> bytes:
        """Send bytes unchanged and recognize SOAP Faults in HTTP error bodies."""
        try:
            with (
                create_http_client(self._timeout) as client,
                client.stream(
                    "POST",
                    endpoint,
                    content=payload,
                    headers={
                        "Content-Type": (
                            f'application/soap+xml; charset=utf-8; action="{action}"'
                        )
                    },
                    timeout=self._timeout,
                    follow_redirects=False,
                ) as response,
            ):
                data = response.read()
                try:
                    response.raise_for_status()
                except httpx.HTTPStatusError as exc:
                    with suppress(DianResponseError):
                        soap_body(data)
                    raise DianTransportError(
                        f"DIAN returned HTTP {response.status_code}.",
                        status_code=response.status_code,
                    ) from exc
                return data
        except httpx.RequestError as exc:
            raise DianTransportError(
                "Unable to communicate with the DIAN service."
            ) from exc

    def get(self, url: str) -> bytes:
        """Download exact bytes with no SOAP credentials, redirects or retries."""
        try:
            with (
                create_http_client(self._timeout) as client,
                client.stream(
                    "GET", url, timeout=self._timeout, follow_redirects=False
                ) as response,
            ):
                try:
                    response.raise_for_status()
                except httpx.HTTPStatusError as exc:
                    raise DianTransportError(
                        f"DIAN download returned HTTP {response.status_code}.",
                        status_code=response.status_code,
                    ) from exc
                return response.read()
        except httpx.RequestError as exc:
            raise DianTransportError("Unable to download the DIAN archive.") from exc

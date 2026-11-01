"""HTTPX transport for signed SOAP messages and exchange-email downloads."""

from collections.abc import Iterator
from contextlib import contextmanager

import httpx

from radiankore._soap.body import read_body
from radiankore._soap.http import check_response
from radiankore.exceptions import DianTransportError
from radiankore.limits import DianResponseLimits


def create_http_client(timeout: float) -> httpx.Client:
    """Create an owned client without opening network connections."""
    return httpx.Client(timeout=timeout, follow_redirects=False)


class SoapTransport:
    """Own isolated SOAP/download pools, optionally retained between operations."""

    def __init__(
        self,
        *,
        timeout: float,
        reuse_connections: bool = False,
        response_limits: DianResponseLimits | None = None,
    ) -> None:
        self._timeout = timeout
        self._reuse_connections = reuse_connections
        self._response_limits = response_limits or DianResponseLimits()
        self._clients: dict[str, httpx.Client] = {}
        self._closed = False

    def ensure_open(self) -> None:
        if self._closed:
            raise RuntimeError("DianClient is closed.")

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        error: Exception | None = None
        try:
            for client in self._clients.values():
                try:
                    client.close()
                except Exception as exc:
                    if error is None:
                        error = exc
        finally:
            self._clients.clear()
        if error is not None:
            raise error

    @contextmanager
    def _client(self, kind: str) -> Iterator[httpx.Client]:
        self.ensure_open()
        if not self._reuse_connections:
            with create_http_client(self._timeout) as client:
                yield client
            return
        if kind not in self._clients:
            self._clients[kind] = create_http_client(self._timeout)
        client = self._clients[kind]
        # HTTPX persists cookies; signed SOAP authentication must be per message.
        client.cookies.clear()
        try:
            yield client
        finally:
            client.cookies.clear()

    def post(self, endpoint: str, payload: bytes, *, action: str) -> bytes:
        """Send bytes unchanged and recognize SOAP Faults in HTTP error bodies."""
        try:
            with (
                self._client("soap") as client,
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
                data = read_body(response, self._response_limits.soap_bytes, "SOAP")
                return check_response(response, data, True)
        except httpx.RequestError as exc:
            raise DianTransportError(
                "Unable to communicate with the DIAN service."
            ) from exc

    def get(self, url: str) -> bytes:
        """Download exact bytes with no SOAP credentials, redirects or retries."""
        try:
            with (
                self._client("download") as client,
                client.stream(
                    "GET", url, timeout=self._timeout, follow_redirects=False
                ) as response,
            ):
                check_response(response, b"", False)
                return read_body(
                    response, self._response_limits.download_bytes, "download"
                )
        except httpx.RequestError as exc:
            raise DianTransportError("Unable to download the DIAN archive.") from exc

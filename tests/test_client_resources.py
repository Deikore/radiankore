"""Resource contracts for clients built from memory, without DIAN access."""

from pathlib import Path

import httpx
import pytest

from radiankore import DianClient, DigitalCertificate, DigitalCertificateError
from radiankore._soap import transport


def test_memory_constructors(
    encrypted_pfx_path: Path, digital_certificate: DigitalCertificate
) -> None:
    with DianClient.from_pfx(
        encrypted_pfx_path.read_bytes(), password="test-password"
    ) as client:
        assert client.certificate.certificate == digital_certificate.certificate
    with DianClient.from_certificate(digital_certificate) as client:
        assert client.certificate is digital_certificate
    with pytest.raises(DigitalCertificateError):
        DianClient.from_pfx(encrypted_pfx_path.read_bytes(), password="wrong")


def test_persistent_connections_and_isolated_downloads(
    digital_certificate: DigitalCertificate,
    mock_http: tuple[list[httpx.Client], list[httpx.Request]],
) -> None:
    clients, requests = mock_http
    with DianClient.from_certificate(
        digital_certificate, reuse_connections=True
    ) as client:
        assert not clients  # No HTTP resources until the first operation.
        client.get_invoice_events("FIRST")
        clients[0].cookies.set("secret", "soap-cookie")
        client.get_invoice_events("SECOND")
        assert len(clients) == 1 and not clients[0].is_closed
        assert "cookie" not in requests[-1].headers
        # Exercise the transport boundary without requiring an archive fixture.
        client._transport.get("https://example.test/download")
        assert len(clients) == 2
        assert "cookie" not in requests[-1].headers
    assert all(c.is_closed for c in clients)
    client.close()
    with pytest.raises(RuntimeError, match="closed"):
        client.get_invoice_events("THIRD")
    with pytest.raises(RuntimeError, match="closed"), client:
        pass


def test_error_resources_close_on_context_exit(
    digital_certificate: DigitalCertificate, monkeypatch: pytest.MonkeyPatch
) -> None:
    clients: list[httpx.Client] = []

    def create(timeout: float) -> httpx.Client:
        def fail(request: httpx.Request) -> httpx.Response:
            raise httpx.ConnectError("synthetic", request=request)

        client = httpx.Client(transport=httpx.MockTransport(fail), timeout=timeout)
        clients.append(client)
        return client

    monkeypatch.setattr(transport, "create_http_client", create)
    from radiankore import DianTransportError

    with (
        pytest.raises(DianTransportError),
        DianClient.from_certificate(
            digital_certificate, reuse_connections=True
        ) as client,
    ):
        client.get_invoice_events("SYNTHETIC")
    assert clients[0].is_closed


def test_pool_reuses_real_local_connection(monkeypatch: pytest.MonkeyPatch) -> None:
    """MockTransport cannot establish whether TCP connections are reused."""
    import threading
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

    peers: list[int] = []

    class Handler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def do_POST(self) -> None:
            self.rfile.read(int(self.headers["Content-Length"]))
            peers.append(self.client_address[1])
            self.send_response(200)
            self.send_header("Content-Length", "2")
            self.end_headers()
            self.wfile.write(b"ok")

        def log_message(self, *_: object) -> None:
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    url = f"http://127.0.0.1:{server.server_port}/"
    monkeypatch.setattr(
        transport,
        "create_http_client",
        lambda timeout: httpx.Client(timeout=timeout, trust_env=False),
    )
    try:
        for reuse in (False, True):
            pool = transport.SoapTransport(timeout=2, reuse_connections=reuse)
            try:
                pool.post(url, b"first", action="synthetic")
                pool.post(url, b"second", action="synthetic")
            finally:
                pool.close()
        assert peers[0] != peers[1]
        assert peers[2] == peers[3]
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)

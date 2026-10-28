"""Real localhost HTTP/TLS proves pooling independently of MockTransport."""

import asyncio
import socket
import ssl
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

from radiankore import AsyncDianClient, DigitalCertificate, Environment
from tests.network_support import localhost_identity


@pytest.mark.parametrize("tls", [False, True])
def test_real_local_connections_are_reused_and_closed(
    digital_certificate: DigitalCertificate,
    soap_response: bytes,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    tls: bool,
) -> None:
    peers: list[int] = []
    cookies: list[str | None] = []

    class Handler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def do_POST(self) -> None:
            self.connection.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            self.rfile.read(int(self.headers["Content-Length"]))
            peers.append(self.client_address[1])
            cookies.append(self.headers.get("Cookie"))
            self.send_response(200)
            self.send_header("Content-Length", str(len(soap_response)))
            self.send_header("Set-Cookie", "secret=synthetic; Path=/")
            self.end_headers()
            self.wfile.write(soap_response)

        def log_message(self, *_: object) -> None:
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    if tls:
        cert_path, key_path = localhost_identity(tmp_path)
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.load_cert_chain(cert_path, key_path)
        server.socket = context.wrap_socket(server.socket, server_side=True)
        monkeypatch.setenv("SSL_CERT_FILE", str(cert_path))
    monkeypatch.setenv("NO_PROXY", "127.0.0.1")
    url = f"{'https' if tls else 'http'}://127.0.0.1:{server.server_port}/"
    monkeypatch.setattr(Environment, "endpoint", property(lambda self: url))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    async def exercise() -> None:
        async with AsyncDianClient(digital_certificate, concurrency=2) as client:
            await client.get_invoice_events("first")
            await client.get_invoice_events("second")
            assert peers[0] == peers[1]
            await asyncio.gather(*(client.get_invoice_events(str(i)) for i in range(6)))
            pool = await client._transport.ready("soap")
        assert pool.is_closed
        assert 1 <= len(set(peers)) <= 2
        assert len(peers) == 8 and not any(cookies)

    try:
        asyncio.run(exercise())
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)

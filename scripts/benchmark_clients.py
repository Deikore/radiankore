"""Offline process/HTTP benchmark. Never contacts DIAN or uses real certificates."""

import argparse
import json
import multiprocessing
import resource
import statistics
import threading
import time
from concurrent.futures import ProcessPoolExecutor
from datetime import UTC, datetime, timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import ClassVar

import httpx
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.serialization import pkcs12
from cryptography.x509.oid import NameOID
from lxml import etree

from radiankore import DianClient
from radiankore._soap import transport
from radiankore._soap.namespaces import RESPONSE, SOAP, WCF
from radiankore._soap.signing import certificate_key


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    peers: ClassVar[set[tuple[str, int]]] = set()
    payload: bytes = b""

    def do_POST(self) -> None:
        self.rfile.read(int(self.headers["Content-Length"]))
        self.peers.add(self.client_address)
        self.send_response(200)
        self.send_header("Content-Length", str(len(self.payload)))
        self.end_headers()
        self.wfile.write(self.payload)

    def log_message(self, *_: object) -> None:
        pass


def exercise(arguments: tuple[bytes, str, int, bool]) -> dict[str, object]:
    data, url, count, reuse = arguments
    original = transport.SoapTransport.post

    def local_post(
        self: transport.SoapTransport, endpoint: str, payload: bytes, *, action: str
    ) -> bytes:
        return original(self, url, payload, action=action)

    transport.SoapTransport.post = local_post  # type: ignore[method-assign]
    transport.create_http_client = lambda timeout: httpx.Client(
        timeout=timeout, trust_env=False
    )
    latencies: list[float] = []
    loads: list[float] = []
    client = None
    cpu = time.process_time()
    try:
        for _ in range(count):
            start = time.perf_counter()
            if client is None or not reuse:
                load = time.perf_counter()
                client = DianClient.from_pfx(
                    data, password="synthetic", reuse_connections=reuse
                )
                loads.append(time.perf_counter() - load)
            client.get_invoice_events("SYNTHETIC-CUFE")
            if not reuse:
                client.close()
            latencies.append(time.perf_counter() - start)
        assert client is not None
        preparation = []
        for _ in range(20):
            start = time.perf_counter()
            certificate_key(client.certificate)
            preparation.append(time.perf_counter() - start)
        return {
            "latencies": latencies,
            "pfx_load_ms": statistics.median(loads) * 1000,
            "key_preparation_ms": statistics.median(preparation) * 1000,
            "cpu_seconds": time.process_time() - cpu,
            "max_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        }
    finally:
        if client:
            client.close()
        transport.SoapTransport.post = original  # type: ignore[method-assign]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--counts", nargs="+", type=int, default=[1, 4, 8, 12, 16])
    parser.add_argument("--requests-per-process", type=int, default=10)
    args = parser.parse_args()
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "Synthetic benchmark")])
    now = datetime.now(UTC)
    certificate = (
        x509.CertificateBuilder()
        .subject_name(name)
        .issuer_name(name)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - timedelta(days=1))
        .not_valid_after(now + timedelta(days=1))
        .sign(key, hashes.SHA256())
    )
    data = pkcs12.serialize_key_and_certificates(
        b"synthetic",
        key,
        certificate,
        None,
        serialization.BestAvailableEncryption(b"synthetic"),
    )
    root = etree.Element(f"{{{SOAP}}}Envelope")
    body = etree.SubElement(root, f"{{{SOAP}}}Body")
    response = etree.SubElement(body, f"{{{WCF}}}GetStatusEventResponse")
    result = etree.SubElement(response, f"{{{WCF}}}GetStatusEventResult")
    etree.SubElement(result, f"{{{RESPONSE}}}IsValid").text = "true"
    etree.SubElement(result, f"{{{RESPONSE}}}StatusCode").text = "00"
    Handler.payload = etree.tostring(root)
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    results = []
    try:
        for workers in args.counts:
            for reuse in (False, True):
                Handler.peers.clear()
                start = time.perf_counter()
                with ProcessPoolExecutor(
                    max_workers=workers, mp_context=multiprocessing.get_context("spawn")
                ) as pool:
                    rows = list(
                        pool.map(
                            exercise,
                            [
                                (
                                    data,
                                    f"http://127.0.0.1:{server.server_port}/",
                                    args.requests_per_process,
                                    reuse,
                                )
                            ]
                            * workers,
                        )
                    )
                elapsed = time.perf_counter() - start
                samples = sorted(value for row in rows for value in row["latencies"])
                results.append(
                    {
                        "workers": workers,
                        "reuse": reuse,
                        "requests": len(samples),
                        "elapsed_seconds_including_spawn": elapsed,
                        "p50_ms": statistics.median(samples) * 1000,
                        "p95_ms": samples[
                            min(len(samples) - 1, int(len(samples) * 0.95))
                        ]
                        * 1000,
                        "tcp_connections": len(Handler.peers),
                        "median_pfx_load_ms": statistics.median(
                            row["pfx_load_ms"] for row in rows
                        ),
                        "median_key_preparation_ms": statistics.median(
                            row["key_preparation_ms"] for row in rows
                        ),
                        "cpu_seconds": sum(row["cpu_seconds"] for row in rows),
                        "max_process_rss_kib": max(row["max_rss_kib"] for row in rows),
                    }
                )
        print(
            json.dumps(
                {
                    "environment": (
                        "local HTTP, shared host, synthetic certificate, no DIAN/TLS"
                    ),
                    "results": results,
                },
                indent=2,
            )
        )
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


if __name__ == "__main__":
    main()

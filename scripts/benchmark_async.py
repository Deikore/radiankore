"""Offline HTTP/TLS comparison of sync, threads, adapters, native and hybrid.

Only a synthetic localhost SOAP server is used. Each measurement runs in a fresh
process; PKCS#12 loading and warmup are excluded from measured latency and CPU.
"""

import argparse
import asyncio
import json
import multiprocessing as mp
import os
import platform
import random
import resource
import runpy
import socket
import ssl
import statistics
import tempfile
import threading
import time
from base64 import b64encode
from collections.abc import Callable
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
from contextlib import suppress
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from importlib.metadata import version
from io import BytesIO
from ipaddress import ip_address
from math import isfinite
from pathlib import Path
from typing import Any, TextIO
from zipfile import ZIP_DEFLATED, ZipFile

import httpx
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.serialization import pkcs12
from cryptography.x509.oid import NameOID

from radiankore import (
    AsyncDianClient,
    DianError,
    DianTimeouts,
    DianTransportError,
    DigitalCertificate,
    Environment,
)
from radiankore._async_runtime import BoundedProcessor
from radiankore._soap.namespaces import EXCHANGE_EMAIL_RESPONSE, RESPONSE, SOAP, WCF


def _identity(directory: Path) -> tuple[bytes, str, str]:
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    name = x509.Name(
        [x509.NameAttribute(NameOID.COMMON_NAME, "Synthetic localhost benchmark")]
    )
    now = datetime.now(UTC)
    cert = (
        x509.CertificateBuilder()
        .subject_name(name)
        .issuer_name(name)
        .public_key(key.public_key())
        .serial_number(123456789)
        .not_valid_before(now - timedelta(days=1))
        .not_valid_after(now + timedelta(days=1))
        .add_extension(x509.BasicConstraints(ca=True, path_length=None), critical=True)
        .add_extension(
            x509.SubjectAlternativeName([x509.IPAddress(ip_address("127.0.0.1"))]),
            critical=False,
        )
        .sign(key, hashes.SHA256())
    )
    cert_path, key_path = directory / "localhost.pem", directory / "localhost-key.pem"
    cert_path.write_bytes(cert.public_bytes(serialization.Encoding.PEM))
    key_path.write_bytes(
        key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        )
    )
    return (
        pkcs12.serialize_key_and_certificates(
            b"synthetic",
            key,
            cert,
            None,
            serialization.BestAvailableEncryption(b"synthetic"),
        ),
        str(cert_path),
        str(key_path),
    )


def _serve(
    pipe: Any, stop: Any, connections: Any, requests: Any, settings: dict[str, Any]
) -> None:
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

    operation = settings.get("operation", "events")
    response_operation = (
        "SendEventUpdateStatus" if operation == "emit" else "GetStatusEvent"
    )
    payload = (
        f'<s:Envelope xmlns:s="{SOAP}" xmlns:w="{WCF}" xmlns:r="{RESPONSE}">'
        f"<s:Body><w:{response_operation}Response><w:{response_operation}Result>"
        "<r:IsValid>true</r:IsValid><r:StatusCode>00</r:StatusCode>"
        "<r:StatusDescription>"
        + "x"
        * settings["payload_bytes"]
        + f"</r:StatusDescription></w:{response_operation}Result>"
        f"</w:{response_operation}Response></s:Body></s:Envelope>"
    ).encode()
    archive_buffer = BytesIO()
    with ZipFile(archive_buffer, "w", compression=ZIP_DEFLATED) as archive:
        archive.writestr(
            "directory.csv",
            "email\n"
            + "synthetic@example.invalid\n" * max(1, settings["payload_bytes"] // 26),
        )
    archive_bytes = archive_buffer.getvalue()

    class Handler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def setup(self) -> None:
            super().setup()
            self.connection.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            with connections.get_lock():
                connections.value += 1

        def do_POST(self) -> None:
            self.rfile.read(int(self.headers["Content-Length"]))
            body = payload
            if operation == "emails":
                namespace = EXCHANGE_EMAIL_RESPONSE
                encoded_url = b64encode(
                    f"https://127.0.0.1:{self.server.server_port}/archive.zip".encode()
                ).decode()
                body = (
                    f'<s:Envelope xmlns:s="{SOAP}" xmlns:w="{WCF}" '
                    f'xmlns:e="{namespace}">'
                    "<s:Body><w:GetExchangeEmailsResponse><w:GetExchangeEmailsResult>"
                    f"<e:CsvBase64Bytes>{encoded_url}</e:CsvBase64Bytes>"
                    "</w:GetExchangeEmailsResult></w:GetExchangeEmailsResponse>"
                    "</s:Body></s:Envelope>"
                ).encode()
            self._respond(body)

        def do_GET(self) -> None:
            self._respond(archive_bytes)

        def _respond(self, body: bytes) -> None:
            with requests.get_lock():
                requests.value += 1
                number = requests.value
            time.sleep(settings["latency_ms"] / 1000)
            bad = settings["scenario"] != "ok" and number % 10 == 0
            if bad and settings["scenario"] == "disconnect":
                self.connection.close()
                self.close_connection = True
                return
            code = 429 if bad and settings["scenario"] == "saturation" else 200
            if bad and settings["scenario"] == "malformed":
                body = b"malformed"
            try:
                self.send_response(code)
                self.send_header("Content-Length", str(len(body)))
                if code == 429:
                    self.send_header("Retry-After", "0")
                self.end_headers()
                self.wfile.write(body)
            except (BrokenPipeError, ConnectionResetError, ssl.SSLError):
                self.close_connection = True

        def log_message(self, *_: object) -> None:
            pass

    class Server(ThreadingHTTPServer):
        request_queue_size = 512

    server = Server(("127.0.0.1", 0), Handler)
    server.timeout = 0.1
    if settings["tls"]:
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.load_cert_chain(settings["cert"], settings["key"])
        server.socket = context.wrap_socket(server.socket, server_side=True)
    pipe.send(
        f"{'https' if settings['tls'] else 'http'}://127.0.0.1:{server.server_port}/"
    )
    pipe.close()
    try:
        while not stop.is_set():
            server.handle_request()
    finally:
        server.server_close()


def _percentile(values: list[float], percentile: float) -> float:
    if not values:
        return 0.0
    return values[min(len(values) - 1, int((len(values) - 1) * percentile))] * 1000


def _is_timeout(error: BaseException) -> bool:
    """Recognize HTTP phase and total timeouts through SDK exception causes."""
    seen: set[int] = set()
    current: BaseException | None = error
    while current is not None and id(current) not in seen:
        seen.add(id(current))
        if isinstance(current, (TimeoutError, httpx.TimeoutException)):
            return True
        current = current.__cause__
    return False


def _exercise(config: dict[str, Any]) -> dict[str, Any]:
    with tempfile.TemporaryFile(mode="w+t") as samples:
        return _measure(config, samples)


def _measure(config: dict[str, Any], samples: TextIO) -> dict[str, Any]:
    import radiankore.async_client as async_module
    import radiankore.client as sync_module

    # Only this isolated benchmark process changes the endpoint, always to loopback.
    url = config["url"]
    if not url.startswith(("http://127.0.0.1:", "https://127.0.0.1:")):
        raise ValueError("Benchmarks require the controlled localhost endpoint.")
    Environment.endpoint = property(lambda self: url)  # type: ignore[assignment]
    os.environ["NO_PROXY"] = "127.0.0.1"
    if config["tls"]:
        os.environ["SSL_CERT_FILE"] = config["cert"]
    width = min(config["concurrency"], config["count"])
    stages: dict[str, list[float]] = {}
    errors: dict[str, int] = {}
    lock = threading.Lock()
    peak_threads = 1
    lag_samples: list[float] = []
    lag_count = 0
    rng = random.Random(0)

    def stage(name: str, duration: float) -> None:
        with lock:
            row = stages.setdefault(name, [0.0, 0.0])
            row[0] += 1
            row[1] += duration

    def complete(start: float, error: DianError | None) -> None:
        nonlocal peak_threads
        with lock:
            samples.write(f"{time.perf_counter() - start}\n")
            peak_threads = max(peak_threads, threading.active_count())
            if error is not None:
                name = type(error).__name__
                if isinstance(error, DianTransportError) and _is_timeout(error):
                    name = "Timeout"
                errors[name] = errors.get(name, 0) + 1

    class MeasuredProcessor(BoundedProcessor):
        async def run[T](self, function: Callable[..., T], *args: object) -> T:
            queued = time.perf_counter()

            def invoke() -> T:
                started = time.perf_counter()
                stage("processing_queue", started - queued)
                try:
                    return function(*args)
                finally:
                    stage(
                        getattr(function, "__name__", "processing"),
                        time.perf_counter() - started,
                    )

            if config["mode"] == "native":
                return invoke()
            return await super().run(invoke)

    async_module.BoundedProcessor = MeasuredProcessor
    original_build = sync_module.build_signed_request

    def build(*args: Any, **kwargs: Any) -> bytes:
        start = time.perf_counter()
        try:
            return original_build(*args, **kwargs)
        finally:
            stage("sync_build_signed_request", time.perf_counter() - start)

    sync_module.build_signed_request = build

    from radiankore._soap import async_transport, transport

    original_sync_post = transport.SoapTransport.post
    original_async_post = async_transport.AsyncSoapTransport.post

    def sync_post(self: Any, *args: Any, **kwargs: Any) -> bytes:
        start = time.perf_counter()
        try:
            return original_sync_post(self, *args, **kwargs)
        finally:
            stage("transport", time.perf_counter() - start)

    async def async_post(self: Any, *args: Any, **kwargs: Any) -> bytes:
        start = time.perf_counter()
        try:
            return await original_async_post(self, *args, **kwargs)
        finally:
            stage("transport", time.perf_counter() - start)

    transport.SoapTransport.post = sync_post
    async_transport.AsyncSoapTransport.post = async_post

    async def ticker(stop: asyncio.Event) -> None:
        nonlocal lag_count
        loop = asyncio.get_running_loop()
        while not stop.is_set():
            expected = loop.time() + 0.005
            await asyncio.sleep(0.005)
            lag = max(0.0, loop.time() - expected)
            lag_count += 1
            if len(lag_samples) < 4096:
                lag_samples.append(lag)
            elif (position := rng.randrange(lag_count)) < 4096:
                lag_samples[position] = lag

    operation = config.get("operation", "events")
    prepared_artifacts: dict[int, Any] = {}
    event = software = None
    if operation in {"prepare", "emit"}:
        from radiankore.models.events import RadianSoftware

        factory_path = Path(__file__).resolve().parents[1] / "tests/event_factories.py"
        factory = runpy.run_path(str(factory_path))["radian_event_factory"]()
        event = factory("441")
        event = replace(
            event,
            header=replace(
                event.header,
                notes=tuple(
                    "x" * min(5000, max(1, config["payload_bytes"]) - offset)
                    for offset in range(0, max(1, config["payload_bytes"]), 5000)
                ),
            ),
        )
        software = RadianSoftware(
            software_id="synthetic-benchmark",
            pin="synthetic",
            provider_tax_number="900000002",
            provider_verification_digit="2",
            signer_role="thirdparty",
        )

    def invoke(client: Any, item: str) -> Any:
        if operation == "emails":
            return client.get_exchange_emails()
        if operation == "prepare":
            return client.prepare_radian_event(event=event, software=software)
        if operation == "emit":
            if isinstance(client, AsyncDianClient):

                async def send() -> Any:
                    if id(client) not in prepared_artifacts:
                        prepared_artifacts[
                            id(client)
                        ] = await client.prepare_radian_event(
                            event=event, software=software
                        )
                    return await client.send_radian_event(
                        prepared_artifacts[id(client)]
                    )

                return send()
            if id(client) not in prepared_artifacts:
                prepared_artifacts[id(client)] = client.prepare_radian_event(
                    event=event, software=software
                )
            return client.send_radian_event(prepared_artifacts[id(client)])
        return client.get_invoice_events(item)

    def sync_run() -> None:
        from radiankore import DianClient

        local = threading.local()
        clients: list[DianClient] = []
        iterator = iter(range(config["count"]))
        barrier = threading.Barrier(width + 1)
        go = threading.Event()

        def worker() -> None:
            local.client = DianClient.from_pfx(
                config["pfx"],
                password="synthetic",
                reuse_connections=True,
                timeout=config["timeout"],
            )
            with lock:
                clients.append(local.client)
            try:
                with suppress(DianError):
                    invoke(local.client, "warmup")
            except BaseException:
                barrier.abort()
                raise
            barrier.wait(timeout=max(60, width))
            go.wait()
            while True:
                with lock:
                    item = next(iterator, None)
                if item is None:
                    return
                started = time.perf_counter()
                error = None
                try:
                    invoke(local.client, str(item))
                except DianError as exc:
                    error = exc
                complete(started, error)

        nonlocal started_at, cpu_started
        if config["mode"] == "sync":
            with DianClient.from_pfx(
                config["pfx"],
                password="synthetic",
                reuse_connections=True,
                timeout=config["timeout"],
            ) as client:
                with suppress(DianError):
                    invoke(client, "warmup")
                stages.clear()
                started_at, cpu_started = time.perf_counter(), time.process_time()
                for item in range(config["count"]):
                    start = time.perf_counter()
                    error = None
                    try:
                        invoke(client, str(item))
                    except DianError as exc:
                        error = exc
                    complete(start, error)
            return
        with ThreadPoolExecutor(max_workers=width) as pool:
            futures = [pool.submit(worker) for _ in range(width)]
            try:
                barrier.wait(timeout=max(60, width))
            except BaseException:
                go.set()
                raise
            stages.clear()
            started_at, cpu_started = time.perf_counter(), time.process_time()
            go.set()
            for future in futures:
                future.result()
        for client in clients:
            client.close()

    async def async_run() -> None:
        from radiankore import DianClient

        nonlocal started_at, cpu_started
        stop = asyncio.Event()
        adapter_clients: list[DianClient] = []
        local = threading.local()
        pool: ThreadPoolExecutor | None = None
        loop = asyncio.get_running_loop()
        if config["mode"] == "adapter":

            def initialize() -> None:
                local.client = DianClient.from_pfx(
                    config["pfx"],
                    password="synthetic",
                    reuse_connections=True,
                    timeout=config["timeout"],
                )
                with lock:
                    adapter_clients.append(local.client)

            pool = ThreadPoolExecutor(max_workers=width, initializer=initialize)
            barrier = threading.Barrier(width)

            def warm() -> None:
                try:
                    with suppress(DianError):
                        invoke(local.client, "warmup")
                except BaseException:
                    barrier.abort()
                    raise
                barrier.wait(timeout=max(60, width))

            await asyncio.gather(
                *(loop.run_in_executor(pool, warm) for _ in range(width))
            )
        material = DigitalCertificate.from_pfx(config["pfx"], password="synthetic")
        async with AsyncDianClient(
            material,
            concurrency=width,
            processing_workers=config.get("processing_workers", 2),
            timeouts=DianTimeouts(read=config["timeout"], total=config["timeout"]),
        ) as client:
            if pool is None:
                await asyncio.gather(
                    *(invoke(client, "warmup") for _ in range(width)),
                    return_exceptions=True,
                )
            stages.clear()
            monitor = asyncio.create_task(ticker(stop))
            started_at, cpu_started = time.perf_counter(), time.process_time()

            async def query(item: int) -> None:
                start = time.perf_counter()
                error = None
                try:
                    if pool is None:
                        await invoke(client, str(item))
                    else:
                        await loop.run_in_executor(
                            pool, lambda: invoke(local.client, str(item))
                        )
                except DianError as exc:
                    error = exc
                complete(start, error)

            async for result in client.iter_queries(
                range(config["count"]), query, workers=width
            ):
                if result.error is not None:
                    raise result.error
            stop.set()
            await monitor
        if pool is not None:
            pool.shutdown(wait=True)
            for client_sync in adapter_clients:
                client_sync.close()

    started_at = cpu_started = 0.0
    if config["mode"] in {"sync", "threads"}:
        if config["mode"] == "sync":
            width = 1
        sync_run()
    else:
        asyncio.run(async_run())
    elapsed = time.perf_counter() - started_at
    cpu = time.process_time() - cpu_started
    # Capture resource use before loading latency samples for percentile analysis.
    rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    samples.seek(0)
    latencies = sorted(float(line) for line in samples)
    lag_samples.sort()
    return {
        "mode": config["mode"],
        "count": config["count"],
        "concurrency": width,
        "elapsed_seconds": elapsed,
        "operations_per_second": config["count"] / elapsed,
        "p50_ms": statistics.median(latencies) * 1000,
        "p95_ms": _percentile(latencies, 0.95),
        "p99_ms": _percentile(latencies, 0.99),
        "cpu_seconds": cpu,
        "max_rss_kib": rss,
        "peak_client_threads": peak_threads,
        "loop_lag_p99_ms": _percentile(lag_samples, 0.99) if lag_samples else None,
        "loop_lag_samples": lag_count,
        "errors": errors,
        "timeouts": errors.get("Timeout", 0),
        "retries": 0,
        "successful_operations_per_second": (config["count"] - sum(errors.values()))
        / elapsed,
        "operations_per_cpu_second": config["count"] / cpu if cpu else None,
        "stage_mean_ms": {k: v[1] / v[0] * 1000 for k, v in stages.items() if v[0]},
    }


def _write_report(path: Path, settings: dict[str, Any], records: list[Any]) -> None:
    report = {
        "environment": {
            "python": os.sys.version,
            "platform": platform.platform(),
            "cpu_count": os.cpu_count(),
            "dependencies": {
                name: version(name)
                for name in ("httpx", "lxml", "xmlsec", "cryptography")
            },
            "tls": settings["tls"],
            "latency_ms": settings["latency_ms"],
            "payload_bytes": settings["payload_bytes"],
            "scenario": settings["scenario"],
            "loop_lag_reservoir": 4096,
            "processing_workers": settings["processing_workers"],
            "operation": settings.get("operation", "events"),
            "note": "localhost SOAP; peaks exclude percentile analysis; no DIAN",
        },
        "results": records,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps(report, indent=2) + "\n")
    temporary.replace(path)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--counts", type=int, nargs="+", default=[100])
    parser.add_argument(
        "--concurrency", type=int, nargs="+", default=[1, 5, 10, 25, 50, 100, 200]
    )
    parser.add_argument(
        "--modes",
        nargs="+",
        choices=["sync", "threads", "adapter", "native", "hybrid"],
        default=["sync", "threads", "adapter", "native", "hybrid"],
    )
    parser.add_argument("--repetitions", type=int, default=3)
    parser.add_argument("--latency-ms", type=float, default=100)
    parser.add_argument("--payload-bytes", type=int, default=10000)
    parser.add_argument("--timeout", type=float, default=60)
    parser.add_argument("--processing-workers", type=int, default=2)
    parser.add_argument("--tls", action="store_true")
    parser.add_argument(
        "--operation", choices=["events", "emails", "prepare", "emit"], default="events"
    )
    parser.add_argument(
        "--scenario",
        choices=["ok", "saturation", "malformed", "disconnect"],
        default="ok",
    )
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if (
        min(*args.counts, *args.concurrency, args.repetitions, args.processing_workers)
        <= 0
        or not isfinite(args.latency_ms)
        or not isfinite(args.timeout)
        or args.timeout <= 0
        or args.latency_ms < 0
        or args.payload_bytes < 0
    ):
        parser.error(
            "Counts, concurrency and repetitions must be positive; "
            "latency and payload must be nonnegative."
        )
    if args.operation == "emails" and not args.tls:
        parser.error("Exchange-email download URLs require --tls.")
    context = mp.get_context("spawn")
    records = []
    with tempfile.TemporaryDirectory(prefix="radiankore-bench-") as directory:
        pfx, cert, key = _identity(Path(directory))
        settings = vars(args) | {"cert": cert, "key": key}
        parent, child = context.Pipe(duplex=False)
        stop = context.Event()
        connections, requests = context.Value("i", 0), context.Value("i", 0)
        server = context.Process(
            target=_serve, args=(child, stop, connections, requests, settings)
        )
        server.start()
        child.close()
        try:
            if not parent.poll(15):
                raise RuntimeError("Local SOAP benchmark server did not start.")
            url = parent.recv()
            for size in args.counts:
                for width in args.concurrency:
                    for mode in args.modes:
                        if mode == "sync" and width != args.concurrency[0]:
                            continue
                        for repetition in range(args.repetitions):
                            config = settings | {
                                "url": url,
                                "pfx": pfx,
                                "count": size,
                                "concurrency": width,
                                "mode": mode,
                            }
                            before_connections, before_requests = (
                                connections.value,
                                requests.value,
                            )
                            with ProcessPoolExecutor(
                                max_workers=1, mp_context=context
                            ) as executor:
                                row = executor.submit(_exercise, config).result()
                            row.update(
                                repetition=repetition + 1,
                                tcp_connections=connections.value - before_connections,
                                server_requests_including_warmup=requests.value
                                - before_requests,
                            )
                            records.append(row)
                            print(
                                f"{mode} n={size} c={row['concurrency']} "
                                f"{row['operations_per_second']:.1f} ops/s "
                                f"errors={sum(row['errors'].values())}",
                                flush=True,
                            )
                            if args.output:
                                _write_report(args.output, settings, records)

        finally:
            stop.set()
            server.join(timeout=5)
            if server.is_alive():
                server.terminate()
                server.join()
            parent.close()
    if not args.output:
        print(json.dumps(records, indent=2))


if __name__ == "__main__":
    main()

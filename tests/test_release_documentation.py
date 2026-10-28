"""Execute published async examples and audit aggregate benchmark evidence."""

import asyncio
import json
from base64 import b64decode
from collections.abc import Callable
from dataclasses import replace
from datetime import datetime
from pathlib import Path
from statistics import median
from typing import Any
from zoneinfo import ZoneInfo

import httpx
import pytest
from lxml import etree

from radiankore import AsyncDianClient, DigitalCertificate
from radiankore._soap import transport
from radiankore._soap.namespaces import WCF
from radiankore.catalogs import EventType
from radiankore.models.events import InvoiceResponseEvent, RadianSoftware
from tests.async_support import install_http
from tests.test_documentation_examples import python_blocks
from tests.test_send_radian_event import result_xml
from tests.test_signing import _verify

ROOT = Path(__file__).resolve().parents[1]


def namespace(path: Path) -> dict[str, Any]:
    """Load real Markdown examples without running command-line entry points."""
    if not path.is_file():
        pytest.skip("Documentation is excluded from this distribution.")
    values: dict[str, Any] = {"__name__": "published_examples"}
    for number, block in enumerate(python_blocks(path)):
        exec(compile(block, f"{path}:block-{number}", "exec"), values)
    return values


def test_readme_queries_and_send_use_public_contracts(
    encrypted_pfx_path: Path,
    digital_certificate: DigitalCertificate,
    soap_response: bytes,
    invoice_event_factory: Callable[[EventType], InvoiceResponseEvent],
    radian_software: RadianSoftware,
    verify_event_signature: Callable[[bytes, DigitalCertificate], None],
    wrap_soap: Callable[[etree._Element], bytes],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    values = namespace(ROOT / "README.md")
    pfx = encrypted_pfx_path.read_bytes()
    requests: list[httpx.Request] = []

    def response(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        _verify(request.content, digital_certificate)
        sending = "SendEventUpdateStatus" in request.headers["content-type"]
        return httpx.Response(
            200, content=result_xml(wrap_soap) if sending else soap_response
        )

    async def handle(request: httpx.Request) -> httpx.Response:
        return response(request)

    async def from_file(path: str, **options: Any) -> AsyncDianClient:
        return await AsyncDianClient.from_pfx(pfx, **options)

    clients = install_http(monkeypatch, handle)
    monkeypatch.setattr(AsyncDianClient, "from_file", from_file)
    sync_clients: list[httpx.Client] = []

    def sync_http(timeout: float) -> httpx.Client:
        client = httpx.Client(transport=httpx.MockTransport(response), timeout=timeout)
        sync_clients.append(client)
        return client

    monkeypatch.setattr(transport, "create_http_client", sync_http)

    async def exercise() -> None:
        result = await values["query_events"]("synthetic-query", "test-password")
        assert len(result.events) == 9
        event = replace(
            invoice_event_factory(EventType.INVOICE_ACKNOWLEDGEMENT),
            issue_date=datetime.now(ZoneInfo("America/Bogota")).date(),
        )
        prepared, sent = await values["send_event"](
            pfx, "test-password", event, radian_software
        )
        verify_event_signature(prepared.xml_bytes, digital_certificate)
        assert sent is not None and sent.status_code == "99"
        encoded = etree.fromstring(requests[-1].content).findtext(
            f".//{{{WCF}}}contentFile"
        )
        assert encoded and b64decode(encoded) == prepared.zip_bytes

    asyncio.run(exercise())
    sync_result = values["query_events_sync"](pfx, "test-password", "synthetic-sync")
    assert len(sync_result.events) == 9
    assert len(requests) == 3
    assert all(client.is_closed for client in [*clients, *sync_clients])


def test_guide_batch_bridge_and_complete_acknowledgement(
    encrypted_pfx_path: Path,
    digital_certificate: DigitalCertificate,
    soap_response: bytes,
    verify_event_signature: Callable[[bytes, DigitalCertificate], None],
    wrap_soap: Callable[[etree._Element], bytes],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    values = namespace(ROOT / "docs/guides/async.md")
    pfx = encrypted_pfx_path.read_bytes()
    sends: list[httpx.Request] = []

    async def handle(request: httpx.Request) -> httpx.Response:
        _verify(request.content, digital_certificate)
        root = etree.fromstring(request.content)
        if "SendEventUpdateStatus" in request.headers["content-type"]:
            sends.append(request)
            return httpx.Response(200, content=result_xml(wrap_soap))
        if root.findtext(f".//{{{WCF}}}trackId") == "synthetic-failure":
            return httpx.Response(404, content=b"Missing synthetic document")
        return httpx.Response(200, content=soap_response)

    clients = install_http(monkeypatch, handle)

    def check_results(rows: list[Any]) -> None:
        assert {row.index for row in rows} == {0, 1, 2}
        assert sum(row.item == "synthetic-success" for row in rows) == 2
        assert sum(row.error is not None for row in rows) == 1
        assert all(len(row.value.events) == 9 for row in rows if row.error is None)
        values["print_event_results"](rows)

    items = ["synthetic-success", "synthetic-failure", "synthetic-success"]

    async def exercise() -> None:
        check_results(await values["query_many"](pfx, "test-password", items))
        prepared, sent = await values["send_acknowledgement"](pfx, "test-password")
        assert prepared.code is EventType.INVOICE_ACKNOWLEDGEMENT
        verify_event_signature(prepared.xml_bytes, digital_certificate)
        assert sent is not None and sent.status_code == "99"
        assert len(sends) == 1
        encoded = etree.fromstring(sends[0].content).findtext(
            f".//{{{WCF}}}contentFile"
        )
        assert encoded and b64decode(encoded) == prepared.zip_bytes

    asyncio.run(exercise())
    check_results(values["query_many_sync"](pfx, "test-password", items))
    assert all(client.is_closed for client in clients)


def test_published_benchmark_tables_match_anonymous_reports() -> None:
    guide = ROOT / "docs/guides/event-query-benchmark.md"
    if not guide.is_file():
        pytest.skip("Benchmark documentation is excluded from distributions.")
    text = guide.read_text()
    readme = (ROOT / "README.md").read_text()
    reports = sorted((ROOT / "docs/benchmarks").glob("dian-events-*.json"))
    cases: dict[tuple[int, int], float] = {}
    queries = 0

    def decimal(value: float, places: int) -> str:
        return f"{value:,.{places}f}".translate(str.maketrans(",.", ".,"))

    forbidden = {"cufes", "password", "certificate", "xml", "download_url"}

    def check_keys(value: object) -> None:
        if isinstance(value, dict):
            assert not (value.keys() & forbidden)
            for child in value.values():
                check_keys(child)
        elif isinstance(value, list):
            for child in value:
                check_keys(child)

    for path in reports:
        report = json.loads(path.read_text())
        assert report["kind"] == "real-dian-event-queries" and report["complete"]
        assert report["environment"] == "production"
        assert len(report["results"]) == 3
        assert path.name in text
        samples = report["results"]
        size, width = samples[0]["count"], samples[0]["concurrency"]
        assert all(s["count"] == size and s["concurrency"] == width for s in samples)
        assert all(s["unique_cufes"] == size for s in samples)
        assert all(
            not s["errors"] and s["timeouts"] == s["retries"] == 0 for s in samples
        )
        elapsed = median(s["elapsed_seconds"] for s in samples)
        throughput = median(s["successful_queries_per_second"] for s in samples)
        p95 = median(s["latency_success_ms"]["p95"] for s in samples)
        row = (
            f"| {size:,} | {width} | {decimal(elapsed, 3)} | "
            f"{decimal(throughput, 2)} | {decimal(p95, 2)} | 0 / 0 |"
        ).replace(f"{size:,}", f"{size:,}".replace(",", "."), 1)
        assert row in text
        cases[size, width] = elapsed
        queries += sum(s["count"] for s in samples)
        # All string-valued fields have known aggregate purposes; no raw payloads.
        check_keys(report)
    assert len(cases) == 9 and queries == 14_400
    for size in (100, 500, 1000):
        row = f"| {size:,} |".replace(",", ".") + "".join(
            f" {decimal(cases[size, width], 2)} s |" for width in (5, 10, 20)
        )
        assert row in readme

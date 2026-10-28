"""Benchmark reports remain aggregate; test traffic never reaches DIAN."""

import argparse
import asyncio
import json
import runpy
from pathlib import Path
from typing import Any, cast

import httpx
import pytest

from radiankore import AsyncDianClient, DianTransportError, DigitalCertificate
from tests.async_support import install_http

SCRIPT = Path(__file__).resolve().parents[1] / "scripts/benchmark_event_queries.py"
pytestmark = pytest.mark.skipif(
    not SCRIPT.is_file(), reason="Benchmark tools are excluded from distributions."
)


def test_aggregate_metrics_keep_failures_and_exclude_private_data(
    digital_certificate: DigitalCertificate,
    soap_response: bytes,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    benchmark = runpy.run_path(str(SCRIPT))
    requests = 0

    async def handler(request: httpx.Request) -> httpx.Response:
        nonlocal requests
        requests += 1
        if b"private-timeout-cufe" in request.content:
            raise httpx.ReadTimeout("private-error-with-sensitive-URL")
        return httpx.Response(200, content=soap_response)

    install_http(monkeypatch, handler)

    async def exercise() -> dict[str, Any]:
        async with AsyncDianClient(digital_certificate, concurrency=2) as client:
            return cast(
                dict[str, Any],
                await benchmark["measure"](
                    client,
                    [
                        "private-success-cufe",
                        "private-timeout-cufe",
                        "private-success-cufe",
                    ],
                    2,
                ),
            )

    sample = asyncio.run(exercise())
    assert requests == sample["count"] == 3
    assert sample["successful_queries"] == 2
    assert sample["errors"] == {"DianTransportError": 1}
    assert sample["timeouts"] == 1
    assert sample["events_total"] == 18
    assert sample["retries"] == 0
    assert sample["latency_success_ms"]["p95"] >= 0
    sample["repetition"] = 1
    report = {"results": [sample]}
    rendered = benchmark["markdown"](report)
    assert "private-" not in rendered + json.dumps(report)
    assert "| 3 | 2 | 1 |" in rendered


def test_timeout_percentiles_and_failed_samples_have_no_fake_latencies() -> None:
    benchmark = runpy.run_path(str(SCRIPT))
    assert benchmark["latency_summary"]([]) == {
        "p50": None,
        "p95": None,
        "p99": None,
    }
    assert benchmark["latency_summary"]([0.01, 0.02, 0.03, 0.04]) == {
        "p50": 25,
        "p95": 40,
        "p99": 40,
    }
    cause = TimeoutError()
    outer = RuntimeError("private")
    outer.__cause__ = cause
    assert benchmark["is_timeout"](outer)
    outer.__cause__ = outer
    assert not benchmark["is_timeout"](outer)


@pytest.mark.parametrize(
    "timeout",
    [
        TimeoutError,
        httpx.ConnectTimeout,
        httpx.ReadTimeout,
        httpx.WriteTimeout,
        httpx.PoolTimeout,
    ],
)
def test_local_benchmark_recognizes_http_phase_and_total_timeouts(
    timeout: type[Exception],
) -> None:
    benchmark = runpy.run_path(str(SCRIPT.with_name("benchmark_async.py")))
    wrapped = DianTransportError("synthetic")
    wrapped.__cause__ = timeout("synthetic")
    assert benchmark["_is_timeout"](wrapped)
    wrapped.__cause__ = ValueError("synthetic")
    assert not benchmark["_is_timeout"](wrapped)


def test_run_generates_anonymized_artifacts_without_extra_queries(
    digital_certificate: DigitalCertificate,
    soap_response: bytes,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    benchmark = runpy.run_path(str(SCRIPT))
    requests = 0

    async def handler(request: httpx.Request) -> httpx.Response:
        nonlocal requests
        requests += 1
        return httpx.Response(200, content=soap_response)

    async def from_file(*args: object, **kwargs: Any) -> AsyncDianClient:
        kwargs.pop("password")
        return AsyncDianClient.from_certificate(digital_certificate, **kwargs)

    install_http(monkeypatch, handler)
    monkeypatch.setattr(AsyncDianClient, "from_file", from_file)
    output = tmp_path / "measurements.json"
    options = argparse.Namespace(
        concurrency=[1, 2],
        requests_per_second=None,
        environment="habilitation",
        counts=[2],
        repetitions=1,
        processing_workers=2,
        total_timeout=60,
        warmup=1,
        seed=42,
        certificate=Path("private-certificate.pfx"),
        output=output,
    )
    asyncio.run(
        benchmark["run"](
            options, ["private-first-cufe", "private-second-cufe"], "private-password"
        )
    )
    assert requests == 6  # Two samples: two measured queries plus one warmup each.
    report = json.loads(output.read_text())
    assert report["complete"] is True
    assert len(report["results"]) == 2
    assert all(row["unique_cufes"] == 2 for row in report["results"])
    assert all(row["warmup"]["successful_queries"] == 1 for row in report["results"])
    assert "private-" not in output.read_text() + output.with_suffix(".md").read_text()

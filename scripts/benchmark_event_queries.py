"""Measure real GetStatusEvent batches; export aggregate metrics, never CUFEs."""

import argparse
import asyncio
import getpass
import json
import math
import platform
import random
import statistics
import sys
import time
from collections import Counter
from collections.abc import Sequence
from contextlib import aclosing
from datetime import UTC, datetime
from importlib.metadata import version
from pathlib import Path
from typing import Any

import httpx

from radiankore import AsyncDianClient, AsyncDianLimiter, DianTimeouts, Environment
from radiankore.models.responses import InvoiceEventsResult


def latency_summary(values: Sequence[float]) -> dict[str, float | None]:
    """Summarize seconds as milliseconds; tail percentiles use nearest rank."""
    ordered = sorted(value * 1000 for value in values)
    return {
        "p50": statistics.median(ordered) if ordered else None,
        "p95": ordered[math.ceil(len(ordered) * 0.95) - 1] if ordered else None,
        "p99": ordered[math.ceil(len(ordered) * 0.99) - 1] if ordered else None,
    }


def is_timeout(error: BaseException) -> bool:
    """Classify SDK-wrapped timeouts without retaining or serializing errors."""
    seen: set[int] = set()
    current: BaseException | None = error
    while current is not None and id(current) not in seen:
        seen.add(id(current))
        if isinstance(current, (TimeoutError, httpx.TimeoutException)):
            return True
        current = current.__cause__
    return False


async def measure(
    client: AsyncDianClient, cufes: Sequence[str], concurrency: int
) -> dict[str, Any]:
    """Measure the public operation, including admission, signing and parsing."""
    all_latencies: list[float] = []
    successful_latencies: list[float] = []
    errors: Counter[str] = Counter()
    timeouts = events = valid = empty = responses = 0

    async def query(cufe: str) -> InvoiceEventsResult:
        started = time.perf_counter()
        try:
            result = await client.get_invoice_events(cufe)
        except Exception:
            all_latencies.append(time.perf_counter() - started)
            raise
        elapsed = time.perf_counter() - started
        all_latencies.append(elapsed)
        successful_latencies.append(elapsed)
        return result

    started = time.perf_counter()
    async with aclosing(
        client.iter_queries(cufes, query, workers=concurrency)
    ) as stream:
        async for result in stream:
            if result.error is not None:
                errors[type(result.error).__name__] += 1
                timeouts += is_timeout(result.error)
            elif result.value is not None:
                responses += 1
                valid += result.value.is_valid
                events += len(result.value.events)
                empty += not result.value.events
    elapsed = time.perf_counter() - started
    successful = len(successful_latencies)
    return {
        "count": len(cufes),
        "concurrency": concurrency,
        "elapsed_seconds": elapsed,
        "successful_queries": successful,
        "successful_queries_per_second": successful / elapsed if elapsed else 0,
        "latency_success_ms": latency_summary(successful_latencies),
        "latency_all_ms": latency_summary(all_latencies),
        "errors": dict(errors),
        "timeouts": timeouts,
        "responses": responses,
        "business_valid_responses": valid,
        "responses_without_events": empty,
        "events_total": events,
        "retries": 0,
    }


def markdown(report: dict[str, Any]) -> str:
    """Render only aggregate fields; do not dump metadata or arbitrary strings."""
    rows = [
        "# Benchmark real de consulta de eventos",
        "",
        "Tiempos del consumidor: admisión, firma, red y parsing. "
        "Percentiles de consultas sin excepción; no son tiempos internos de DIAN.",
        "",
        "| CUFEs | Concurrencia | Repetición | Total, s | Éxitos/s | "
        "p50, ms | p95, ms | p99, ms | Errores | Timeouts |",
        "| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for sample in report["results"]:
        tail = sample["latency_success_ms"]
        percentiles = " | ".join(
            "—" if tail[key] is None else f"{tail[key]:.2f}"
            for key in ("p50", "p95", "p99")
        )
        rows.append(
            f"| {sample['count']} | {sample['concurrency']} | "
            f"{sample['repetition']} | {sample['elapsed_seconds']:.3f} | "
            f"{sample['successful_queries_per_second']:.2f} | {percentiles} | "
            f"{sum(sample['errors'].values())} | {sample['timeouts']} |"
        )
    rows.extend(
        [
            "",
            "Cada fila es una muestra completa, sin reintentos. "
            "Un estado de negocio negativo no se cuenta como error de transporte.",
            "",
            "El JSON contiene ambiente, fecha UTC, versiones, configuración, "
            "calentamiento y carga/cierre separados. Revise esos datos antes "
            "de publicar esta tabla; una ejecución parcial puede tener "
            "filas faltantes.",
            "",
        ]
    )
    return "\n".join(rows)


def write_report(path: Path, report: dict[str, Any]) -> None:
    """Persist completed samples and their table without recording inputs."""
    path.parent.mkdir(parents=True, exist_ok=True)
    for destination, content in (
        (path, json.dumps(report, indent=2, allow_nan=False) + "\n"),
        (path.with_suffix(".md"), markdown(report)),
    ):
        temporary = destination.with_name(destination.name + ".tmp")
        temporary.write_text(content, encoding="utf-8")
        temporary.replace(destination)


async def run(args: argparse.Namespace, cufes: list[str], password: str) -> None:
    limiter = AsyncDianLimiter(
        concurrency=max(args.concurrency),
        requests_per_second=args.requests_per_second,
    )
    report: dict[str, Any] = {
        "kind": "real-dian-event-queries",
        "complete": False,
        "started_at_utc": datetime.now(UTC).isoformat(),
        "environment": args.environment,
        "python": platform.python_version(),
        "platform": platform.platform(),
        "dependencies": {
            name: version(name)
            for name in ("radiankore", "httpx", "lxml", "xmlsec", "cryptography")
        },
        "configuration": {
            "counts": args.counts,
            "concurrency": args.concurrency,
            "processing_workers": args.processing_workers,
            "repetitions": args.repetitions,
            "requests_per_second": args.requests_per_second,
            "total_timeout_seconds": args.total_timeout,
            "warmup_queries_per_trial": args.warmup,
            "order_seed": args.seed,
            "percentile_method": "median p50; nearest-rank p95/p99",
            "pool_policy": "new client per trial; load/close excluded from batch time",
            "cufe_selection": "file prefix per count; duplicates preserved",
        },
        "results": [],
    }
    cases = [
        (size, width, repetition)
        for repetition in range(1, args.repetitions + 1)
        for size in args.counts
        for width in args.concurrency
    ]
    random.Random(args.seed).shuffle(cases)
    write_report(args.output, report)
    for size, width, repetition in cases:
        loaded_at = time.perf_counter()
        client = await AsyncDianClient.from_file(
            args.certificate,
            password=password,
            environment=Environment(args.environment),
            concurrency=width,
            processing_workers=args.processing_workers,
            timeouts=DianTimeouts(total=args.total_timeout),
            limiter=limiter,
        )
        load_seconds = time.perf_counter() - loaded_at
        try:
            warmup = (
                await measure(
                    client,
                    [cufes[index % size] for index in range(args.warmup)],
                    width,
                )
                if args.warmup
                else None
            )
            sample = await measure(client, cufes[:size], width)
        finally:
            closing_at = time.perf_counter()
            await client.aclose()
            close_seconds = time.perf_counter() - closing_at
        sample.update(
            repetition=repetition,
            recorded_at_utc=datetime.now(UTC).isoformat(),
            unique_cufes=len(set(cufes[:size])),
            certificate_load_seconds=load_seconds,
            client_close_seconds=close_seconds,
            warmup=warmup,
        )
        report["results"].append(sample)
        write_report(args.output, report)
        print(
            f"CUFEs={size} concurrency={width} repetition={repetition} "
            f"seconds={sample['elapsed_seconds']:.3f} "
            f"errors={sum(sample['errors'].values())}",
            flush=True,
        )
    report["complete"] = True
    report["finished_at_utc"] = datetime.now(UTC).isoformat()
    write_report(args.output, report)


def positive_int(value: str) -> int:
    number = int(value)
    if number <= 0:
        raise argparse.ArgumentTypeError("Expected a positive integer.")
    return number


def positive_float(value: str) -> float:
    number = float(value)
    if not math.isfinite(number) or number <= 0:
        raise argparse.ArgumentTypeError("Expected a positive finite number.")
    return number


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    execute = commands.add_parser("run", help="Query DIAN using your own material.")
    execute.add_argument("--cufes-file", type=Path, required=True)
    execute.add_argument("--certificate", type=Path, required=True)
    execute.add_argument("--environment", choices=list(Environment), required=True)
    execute.add_argument("--counts", type=positive_int, nargs="+", default=[100])
    execute.add_argument("--concurrency", type=positive_int, nargs="+", default=[5])
    execute.add_argument("--repetitions", type=positive_int, default=3)
    execute.add_argument("--processing-workers", type=positive_int, default=2)
    execute.add_argument("--total-timeout", type=positive_float, default=60)
    execute.add_argument("--requests-per-second", type=positive_float)
    execute.add_argument("--warmup", type=int, default=0)
    execute.add_argument("--seed", type=int, default=42)
    execute.add_argument("--output", type=Path, required=True)
    render = commands.add_parser("render", help="Regenerate Markdown offline.")
    render.add_argument("report", type=Path)
    args = parser.parse_args()
    if args.command == "render":
        report = json.loads(args.report.read_text(encoding="utf-8"))
        if report.get("kind") != "real-dian-event-queries":
            parser.error("Expected a real event-query benchmark report.")
        print(markdown(report))
        return 0
    if args.warmup < 0 or args.output.suffix != ".json":
        parser.error("Warmup must be nonnegative and output must end in .json.")
    inputs = {args.cufes_file.resolve(), args.certificate.resolve()}
    outputs = {
        args.output.resolve(),
        args.output.with_suffix(".md").resolve(),
        args.output.with_name(args.output.name + ".tmp").resolve(),
        args.output.with_suffix(".md.tmp").resolve(),
    }
    if inputs & outputs:
        parser.error("Reports must not overwrite CUFE or certificate inputs.")
    cufes = [
        line.strip()
        for line in args.cufes_file.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if len(cufes) < max(args.counts):
        parser.error("The CUFE file has fewer entries than the largest batch.")
    requests = (
        (sum(args.counts) + len(args.counts) * args.warmup)
        * len(args.concurrency)
        * args.repetitions
    )
    print(
        f"Environment={args.environment}; planned SOAP requests={requests}; "
        "no retries. Password is not recorded.",
        flush=True,
    )
    password = getpass.getpass("PKCS#12 password: ")
    asyncio.run(run(args, cufes, password))
    return 0


if __name__ == "__main__":
    try:
        code = main()
    except KeyboardInterrupt:
        print("Interrupted; completed samples remain in the report.", file=sys.stderr)
        code = 130
    except Exception as error:
        # Exception messages/tracebacks may contain URLs or certificate paths.
        print(f"Benchmark failed ({type(error).__name__}).", file=sys.stderr)
        code = 1
    raise SystemExit(code)

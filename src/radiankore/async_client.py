"""Asynchronous DIAN API with native HTTP and bounded local processing."""

import asyncio
import threading
from collections.abc import (
    AsyncGenerator,
    AsyncIterable,
    AsyncIterator,
    Awaitable,
    Callable,
    Iterable,
)
from contextlib import asynccontextmanager
from dataclasses import replace
from datetime import UTC, datetime
from os import PathLike
from typing import Self

import httpx

from radiankore._async_bulk import iter_queries
from radiankore._async_runtime import BoundedProcessor, LoopBound
from radiankore._soap.acquirer_response import parse_acquirer_response
from radiankore._soap.async_transport import AsyncSoapTransport
from radiankore._soap.document_info_response import parse_document_info_response
from radiankore._soap.document_status_response import parse_document_status_response
from radiankore._soap.envelope import build_signed_request
from radiankore._soap.events import parse_send_event_response
from radiankore._soap.exchange_emails_response import (
    parse_exchange_emails_csv,
    parse_exchange_emails_response,
)
from radiankore._soap.namespaces import ACTION_PREFIX
from radiankore._soap.numbering_range_response import parse_numbering_range_response
from radiankore._soap.operations import (
    acquirer_parameters,
    event_parameters,
    numbering_parameters,
    prepare_event,
    text,
)
from radiankore._soap.reference_notes_response import parse_reference_notes_response
from radiankore._soap.response import parse_invoice_events_response
from radiankore._soap.xml_document_response import parse_xml_document_response
from radiankore.async_limiter import AsyncDianLimiter
from radiankore.async_models import DianTimeouts, QueryResult, count
from radiankore.catalogs import IdentificationType
from radiankore.certificate import DigitalCertificate
from radiankore.environment import Environment
from radiankore.exceptions import DianTransportError
from radiankore.models.events import (
    InvoiceResponseEvent,
    PreparedRadianEvent,
    RadianEvent,
    RadianSoftware,
)
from radiankore.models.responses import (
    AcquirerResult,
    DocumentInfoResult,
    DocumentStatusResult,
    ExchangeEmailsResult,
    InvoiceEventsResult,
    NumberingRangeResult,
    ReferenceNotesResult,
    SendEventResult,
    XmlDocumentResult,
)


class AsyncDianClient:
    """Concurrent client owned by one process and event loop.

    Use async with or await aclose(). HTTP pools are lazy and always reused.
    Native key access is serialized within this client; do not concurrently
    share its DigitalCertificate with another client or mutate its native key.
    Loading material does not establish trust, revocation or DIAN authorization.
    There are no automatic retries, including after an uncertain event send.
    """

    def __init__(
        self,
        certificate: DigitalCertificate,
        *,
        environment: Environment | str = Environment.PRODUCTION,
        timeouts: DianTimeouts | None = None,
        concurrency: int = 5,
        processing_workers: int = 2,
        limiter: AsyncDianLimiter | None = None,
    ) -> None:
        self._validate_options(
            environment, timeouts, concurrency, processing_workers, limiter
        )
        if not isinstance(certificate, DigitalCertificate):
            raise TypeError("certificate must be a DigitalCertificate.")
        self._certificate = certificate
        self._environment = Environment(environment)
        self._timeouts = timeouts or DianTimeouts()
        self._concurrency = concurrency
        self._affinity = LoopBound()
        self._processor = BoundedProcessor(processing_workers)
        self._limiter = limiter or AsyncDianLimiter(concurrency=concurrency)
        self._transport = AsyncSoapTransport(
            self._processor, self._timeouts, concurrency, self._limiter
        )
        self._slots = asyncio.Semaphore(concurrency)
        self._crypto_lock = threading.Lock()
        self._active = 0
        self._idle = asyncio.Event()
        self._idle.set()
        self._closing = False
        self._close_task: asyncio.Task[None] | None = None
        self._batches: set[asyncio.Task[None]] = set()

    @staticmethod
    def _validate_options(
        environment: Environment | str,
        timeouts: DianTimeouts | None,
        concurrency: int,
        processing_workers: int,
        limiter: AsyncDianLimiter | None,
    ) -> None:
        Environment(environment)
        count(concurrency, "concurrency")
        count(processing_workers, "processing_workers")
        if timeouts is not None and not isinstance(timeouts, DianTimeouts):
            raise TypeError("timeouts must be DianTimeouts or None.")
        if limiter is not None and not isinstance(limiter, AsyncDianLimiter):
            raise TypeError("limiter must be AsyncDianLimiter or None.")

    @classmethod
    def from_certificate(
        cls,
        certificate: DigitalCertificate,
        *,
        environment: Environment | str = Environment.PRODUCTION,
        timeouts: DianTimeouts | None = None,
        concurrency: int = 5,
        processing_workers: int = 2,
        limiter: AsyncDianLimiter | None = None,
    ) -> Self:
        """Use decoded material without file I/O or opening connections."""
        return cls(
            certificate,
            environment=environment,
            timeouts=timeouts,
            concurrency=concurrency,
            processing_workers=processing_workers,
            limiter=limiter,
        )

    @classmethod
    async def from_file(
        cls,
        path: str | PathLike[str],
        *,
        password: str | bytes | None = None,
        environment: Environment | str = Environment.PRODUCTION,
        timeouts: DianTimeouts | None = None,
        concurrency: int = 5,
        processing_workers: int = 2,
        limiter: AsyncDianLimiter | None = None,
    ) -> Self:
        """Read and decode PKCS#12 off-loop, closing loader resources on failure."""
        cls._validate_options(
            environment, timeouts, concurrency, processing_workers, limiter
        )
        processor = BoundedProcessor(1)
        try:
            certificate = await processor.run(
                lambda: DigitalCertificate.from_file(path, password=password)
            )
        finally:
            await processor.aclose()
        return cls.from_certificate(
            certificate,
            environment=environment,
            timeouts=timeouts,
            concurrency=concurrency,
            processing_workers=processing_workers,
            limiter=limiter,
        )

    @classmethod
    async def from_pfx(
        cls,
        data: bytes,
        *,
        password: str | bytes | None = None,
        environment: Environment | str = Environment.PRODUCTION,
        timeouts: DianTimeouts | None = None,
        concurrency: int = 5,
        processing_workers: int = 2,
        limiter: AsyncDianLimiter | None = None,
    ) -> Self:
        """Decode in-memory PKCS#12 off-loop; never retain password or PFX bytes."""
        cls._validate_options(
            environment, timeouts, concurrency, processing_workers, limiter
        )
        processor = BoundedProcessor(1)
        try:
            certificate = await processor.run(
                lambda: DigitalCertificate.from_pfx(data, password=password)
            )
        finally:
            await processor.aclose()
        return cls.from_certificate(
            certificate,
            environment=environment,
            timeouts=timeouts,
            concurrency=concurrency,
            processing_workers=processing_workers,
            limiter=limiter,
        )

    @property
    def certificate(self) -> DigitalCertificate:
        """Return the loaded material; callers must not mutate its native key."""
        return self._certificate

    @property
    def environment(self) -> Environment:
        """Return the fixed deployment environment."""
        return self._environment

    def _ensure_open(self) -> asyncio.AbstractEventLoop:
        loop = self._affinity.bind()
        if self._closing:
            raise RuntimeError("AsyncDianClient is closed.")
        return loop

    async def __aenter__(self) -> Self:
        self._ensure_open()
        return self

    async def __aexit__(self, *_: object) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        """Reject new work, drain owned tasks and physical jobs, and close pools.

        Cancellation of a close waiter does not abandon shutdown. Await aclose()
        again to join it. A native function already running must finish first.
        """
        loop = self._affinity.bind()
        if self._close_task is None:
            self._closing = True
            self._close_task = loop.create_task(self._close(), name="radiankore-close")
            self._close_task.add_done_callback(self._closed)
        await asyncio.shield(self._close_task)

    @staticmethod
    def _closed(task: asyncio.Task[None]) -> None:
        if not task.cancelled():
            task.exception()

    async def _close(self) -> None:
        for batch in self._batches:
            batch.cancel()
        await asyncio.gather(*self._batches, return_exceptions=True)
        await self._idle.wait()
        try:
            await self._transport.aclose()
        finally:
            await self._processor.aclose()

    @asynccontextmanager
    async def _operation(self) -> AsyncIterator[None]:
        self._ensure_open()
        self._active += 1
        self._idle.clear()
        deadline = asyncio.timeout(self._timeouts.total)
        try:
            try:
                async with deadline, self._slots:
                    yield
            except TimeoutError as exc:
                if deadline.expired():
                    raise DianTransportError(
                        "The DIAN operation exceeded its total deadline."
                    ) from exc
                raise
        finally:
            self._active -= 1
            if self._active == 0:
                self._idle.set()

    def _signed(self, operation: str, parameters: tuple[tuple[str, str], ...]) -> bytes:
        return build_signed_request(
            operation,
            parameters,
            action=f"{ACTION_PREFIX}/{operation}",
            certificate=self._certificate,
            environment=self._environment,
            certificate_lock=self._crypto_lock,
        )

    async def _request(
        self, operation: str, parameters: tuple[tuple[str, str], ...]
    ) -> bytes:
        await self._transport.ready("soap")
        endpoint = self._environment.endpoint
        async with self._limiter._slot(endpoint):
            loop = self._affinity.bind()
            signed_at = loop.time()
            payload = await self._processor.run(self._signed, operation, parameters)
            await self._limiter._wait(endpoint)
            # Do not reuse an envelope that aged out while waiting for a rate slot.
            if loop.time() - signed_at >= 240:
                signed_at = loop.time()
                payload = await self._processor.run(self._signed, operation, parameters)
                if loop.time() - signed_at >= 240:
                    raise DianTransportError("Unable to prepare a fresh SOAP envelope.")
            return await self._transport.post(
                endpoint, payload, f"{ACTION_PREFIX}/{operation}"
            )

    async def _query[T](
        self,
        operation: str,
        parameters: tuple[tuple[str, str], ...],
        parser: Callable[[bytes], T],
    ) -> T:
        async with self._operation():
            data = await self._request(operation, parameters)
            return await self._processor.run(parser, data)

    async def get_invoice_events(self, cufe: str) -> InvoiceEventsResult:
        """Query invoice events, preserving numeric ReferenceID ordering."""
        return await self._query(
            "GetStatusEvent",
            (("trackId", text(cufe, "cufe")),),
            parse_invoice_events_response,
        )

    async def get_status(self, track_id: str) -> DocumentStatusResult | None:
        """Query validation status without interpreting business codes."""
        return await self._query(
            "GetStatus",
            (("trackId", text(track_id, "track_id")),),
            parse_document_status_response,
        )

    async def get_document_info(self, uuid: str) -> DocumentInfoResult | None:
        """Read structured documents without dropping ordered or nil entries."""
        return await self._query(
            "GetDocumentInfo",
            (("uuid", text(uuid, "uuid")),),
            parse_document_info_response,
        )

    async def get_reference_notes(self, track_id: str) -> ReferenceNotesResult | None:
        """Read ordered notes and independent original binary payloads."""
        return await self._query(
            "GetReferenceNotes",
            (("trackId", text(track_id, "track_id")),),
            parse_reference_notes_response,
        )

    async def get_xml_by_document_key(
        self, document_key: str
    ) -> XmlDocumentResult | None:
        """Decode the original bytes without reformatting their XML."""
        return await self._query(
            "GetXmlByDocumentKey",
            (("trackId", text(document_key, "document_key")),),
            parse_xml_document_response,
        )

    async def get_numbering_range(
        self, *, account_code: str, account_code_t: str, software_code: str
    ) -> NumberingRangeResult | None:
        """Read numbering ranges, preserving NIT and software validation."""
        return await self._query(
            "GetNumberingRange",
            numbering_parameters(account_code, account_code_t, software_code),
            parse_numbering_range_response,
        )

    async def get_acquirer(
        self,
        *,
        identification_type: IdentificationType,
        identification_number: str,
    ) -> AcquirerResult | None:
        """Read acquirer information; only this operation maps HTTP 404 to None."""
        parameters = acquirer_parameters(identification_type, identification_number)
        try:
            return await self._query("GetAcquirer", parameters, parse_acquirer_response)
        except DianTransportError as exc:
            if exc.status_code == 404:
                return None
            raise

    async def get_exchange_emails(self) -> ExchangeEmailsResult | None:
        """Read SOAP metadata, download its ZIP, and parse CSV within one deadline."""
        async with self._operation():
            data = await self._request("GetExchangeEmails", ())
            result = await self._processor.run(parse_exchange_emails_response, data)
            if result is None or result.download_url is None:
                return result
            url = result.download_url
            service = str(httpx.URL(url).copy_with(path="/", query=None, fragment=None))
            await self._transport.ready("download")
            async with self._limiter._slot(service):
                await self._limiter._wait(service)
                archive = await self._transport.get(url, service)
            rows = await self._processor.run(parse_exchange_emails_csv, archive)
            return replace(result, csv=rows)

    def _prepare(
        self, event: RadianEvent, software: RadianSoftware
    ) -> PreparedRadianEvent:
        with self._crypto_lock:
            return prepare_event(
                event,
                software,
                self._certificate,
                self._environment,
                datetime.now(UTC) if isinstance(event, InvoiceResponseEvent) else None,
            )

    async def prepare_radian_event(
        self, *, event: RadianEvent, software: RadianSoftware
    ) -> PreparedRadianEvent:
        """Prepare locally off-loop; never transmit or rebuild a signed artifact."""
        async with self._operation():
            return await self._processor.run(self._prepare, event, software)

    async def send_radian_event(
        self, prepared: PreparedRadianEvent
    ) -> SendEventResult | None:
        """Submit the original ZIP once. Cancellation or failure may be uncertain.

        Calling this method again can transmit again; reconcile before deciding
        to resend. None is not confirmed acceptance. No retries are performed.
        """
        async with self._operation():
            parameters = await self._processor.run(
                event_parameters, prepared, self._environment
            )
            data = await self._request("SendEventUpdateStatus", parameters)
            return await self._processor.run(parse_send_event_response, data)

    async def iter_queries[T, R](
        self,
        items: Iterable[T] | AsyncIterable[T],
        query: Callable[[T], Awaitable[R]],
        *,
        workers: int | None = None,
        buffer_size: int | None = None,
    ) -> AsyncGenerator[QueryResult[T, R]]:
        """Yield completion-order results with bounded tasks and two bounded queues.

        Use contextlib.aclosing when stopping early. None values are successes
        when error is None. Query exceptions become results; source failures and
        cancellation propagate. A synchronous source must not perform blocking I/O.
        """
        self._ensure_open()
        width = self._concurrency if workers is None else workers
        size = 2 * width if buffer_size is None else buffer_size
        stream = iter_queries(items, query, width, size, self._batches)
        try:
            async for result in stream:
                yield result
        finally:
            await stream.aclose()

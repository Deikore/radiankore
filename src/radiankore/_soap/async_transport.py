"""Owned asynchronous SOAP/download pools; no retries or shared cookies."""

import asyncio
from http.cookiejar import Cookie, CookieJar, DefaultCookiePolicy
from urllib.request import Request

import httpx

from radiankore._async_runtime import BoundedProcessor
from radiankore._soap.http import check_response, retry_after
from radiankore.async_limiter import AsyncDianLimiter
from radiankore.async_models import DianTimeouts
from radiankore.exceptions import DianTransportError


class _RejectCookies(DefaultCookiePolicy):
    def set_ok(self, cookie: Cookie, request: Request) -> bool:
        return False

    def return_ok(self, cookie: Cookie, request: Request) -> bool:
        return False


def create_async_http_client(
    timeouts: DianTimeouts, concurrency: int
) -> httpx.AsyncClient:
    """Build TLS contexts off-loop; connections open only in async operations."""
    return httpx.AsyncClient(
        timeout=httpx.Timeout(
            connect=timeouts.connect,
            read=timeouts.read,
            write=timeouts.write,
            pool=timeouts.pool,
        ),
        limits=httpx.Limits(
            max_connections=concurrency,
            max_keepalive_connections=concurrency,
            keepalive_expiry=30.0,
        ),
        follow_redirects=False,
        cookies=CookieJar(policy=_RejectCookies()),
    )


class AsyncSoapTransport:
    """Keep initializer tasks owned even if their first waiter is cancelled."""

    def __init__(
        self,
        processor: BoundedProcessor,
        timeouts: DianTimeouts,
        concurrency: int,
        limiter: AsyncDianLimiter,
    ) -> None:
        self._processor = processor
        self._timeouts = timeouts
        self._concurrency = concurrency
        self._limiter = limiter
        self._clients: dict[str, asyncio.Task[httpx.AsyncClient]] = {}

    async def ready(self, kind: str) -> httpx.AsyncClient:
        if kind not in self._clients:
            task = asyncio.create_task(
                self._processor.run(
                    create_async_http_client, self._timeouts, self._concurrency
                ),
                name=f"radiankore-{kind}-pool",
            )
            task.add_done_callback(self._initialized)
            self._clients[kind] = task
        task = self._clients[kind]
        try:
            return await asyncio.shield(task)
        except Exception:
            if self._clients.get(kind) is task:
                self._clients.pop(kind)
            raise

    @staticmethod
    def _initialized(task: asyncio.Task[httpx.AsyncClient]) -> None:
        if not task.cancelled():
            task.exception()

    async def post(self, endpoint: str, payload: bytes, action: str) -> bytes:
        client = await self.ready("soap")
        try:
            async with client.stream(
                "POST",
                endpoint,
                content=payload,
                headers={
                    "Content-Type": (
                        f'application/soap+xml; charset=utf-8; action="{action}"'
                    )
                },
                follow_redirects=False,
            ) as response:
                self._observe(response, endpoint)
                data = await response.aread()
                if response.is_success:
                    return data
                return await self._processor.run(check_response, response, data, True)
        except httpx.RequestError as exc:
            raise DianTransportError(
                "Unable to communicate with the DIAN service."
            ) from exc

    async def get(self, url: str, service: str) -> bytes:
        client = await self.ready("download")
        try:
            async with client.stream("GET", url, follow_redirects=False) as response:
                self._observe(response, service)
                if not response.is_success:
                    await self._processor.run(check_response, response, b"", False)
                return await response.aread()
        except httpx.RequestError as exc:
            raise DianTransportError("Unable to download the DIAN archive.") from exc

    def _observe(self, response: httpx.Response, service: str) -> None:
        if response.is_error:
            delay = retry_after(response.headers.get("Retry-After"))
            if delay is not None:
                self._limiter._defer(service, delay)

    async def aclose(self) -> None:
        # Drain every initializer, including abandoned ones, before processor shutdown.
        results = await asyncio.gather(
            *(asyncio.shield(task) for task in self._clients.values()),
            return_exceptions=True,
        )
        try:
            # Each close is attempted even if another pool fails to close.
            errors = await asyncio.gather(
                *(c.aclose() for c in results if isinstance(c, httpx.AsyncClient)),
                return_exceptions=True,
            )
            for error in errors:
                if isinstance(error, BaseException):
                    raise error
        finally:
            self._clients.clear()

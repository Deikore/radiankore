"""Intercept the networking boundary while exercising production async pools."""

from collections.abc import Callable, Coroutine
from typing import Any

import httpx
import pytest

Handler = Callable[[httpx.Request], Coroutine[None, None, httpx.Response]]


def install_http(
    monkeypatch: pytest.MonkeyPatch, handler: Handler
) -> list[httpx.AsyncClient]:
    """Keep factory options and cookie policy; replace only network transport."""
    original = httpx.AsyncClient.__init__
    clients: list[httpx.AsyncClient] = []

    def initialize(self: httpx.AsyncClient, **kwargs: Any) -> None:
        kwargs["transport"] = httpx.MockTransport(handler)
        kwargs["trust_env"] = False
        original(self, **kwargs)
        clients.append(self)

    monkeypatch.setattr(httpx.AsyncClient, "__init__", initialize)
    return clients


class RecordingAdmission:
    """Capture borrowed admission calls without any network or shared service."""

    def __init__(self) -> None:
        self.starts: list[str] = []
        self.cooldowns: list[tuple[str, float]] = []
        self.closed = False

    async def wait_for_start(self, *, service: str) -> None:
        self.starts.append(service)

    async def record_retry_after(self, *, service: str, seconds: float) -> None:
        self.cooldowns.append((service, seconds))

    async def aclose(self) -> None:
        self.closed = True

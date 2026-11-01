"""Bound decoded HTTP response bodies without trusting Content-Length."""

import httpx

from radiankore.exceptions import DianTransportError

_CHUNK_SIZE = 64 * 1024


def _append(body: bytearray, chunk: bytes, maximum: int | None, kind: str) -> None:
    if maximum is not None and len(body) + len(chunk) > maximum:
        raise DianTransportError(
            f"The {kind} response exceeded its {maximum}-byte limit."
        )
    body.extend(chunk)


def read_body(response: httpx.Response, maximum: int | None, kind: str) -> bytes:
    """Collect decoded bytes in bounded chunks; the caller owns the stream."""
    body = bytearray()
    for chunk in response.iter_bytes(chunk_size=_CHUNK_SIZE):
        _append(body, chunk, maximum, kind)
    return bytes(body)


async def read_async_body(
    response: httpx.Response, maximum: int | None, kind: str
) -> bytes:
    """Collect decoded bytes without retaining an oversized complete body."""
    body = bytearray()
    async for chunk in response.aiter_bytes(chunk_size=_CHUNK_SIZE):
        _append(body, chunk, maximum, kind)
    return bytes(body)

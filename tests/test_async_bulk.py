"""Streaming scale, backpressure, correlation and structured cancellation."""

import asyncio
from collections.abc import AsyncIterator, Iterator
from contextlib import aclosing

import pytest

from radiankore import AsyncDianClient, DigitalCertificate, QueryResult


@pytest.mark.parametrize("size", [0, 100, 1000, 10000, 100000])
def test_streaming_keeps_fixed_tasks(
    digital_certificate: DigitalCertificate, size: int
) -> None:
    async def exercise() -> None:
        count = 0
        max_tasks = 0

        async def query(item: int) -> int | None:
            nonlocal max_tasks
            max_tasks = max(max_tasks, len(asyncio.all_tasks()))
            if item % 17 == 0:
                await asyncio.sleep(0)
            return None if item % 3 == 0 else item

        async with AsyncDianClient(digital_certificate) as client:
            async for result in client.iter_queries(range(size), query):
                assert result.error is None
                assert result.value == (None if result.item % 3 == 0 else result.item)
                count += 1
        assert count == size
        assert max_tasks <= 8

    asyncio.run(exercise())


def test_duplicate_inputs_completion_order_and_item_errors(
    digital_certificate: DigitalCertificate,
) -> None:
    async def exercise() -> None:
        first = asyncio.Event()
        calls = 0

        async def query(item: str) -> str:
            nonlocal calls
            calls += 1
            if item == "slow":
                await first.wait()
            elif item == "bad":
                raise ValueError("synthetic")
            else:
                first.set()
            return item

        async with AsyncDianClient(digital_certificate) as client:
            results = [
                r
                async for r in client.iter_queries(
                    ["slow", "same", "same", "bad"], query
                )
            ]
        assert calls == 4
        assert results[0].index != 0
        assert {r.index for r in results} == {0, 1, 2, 3}
        assert sum(r.item == "same" for r in results) == 2
        assert isinstance(next(r for r in results if r.index == 3).error, ValueError)
        assert "private" not in repr(
            QueryResult(index=0, item="private", value="private")
        )

    asyncio.run(exercise())


def test_slow_consumer_bounds_source_and_closes_early(
    digital_certificate: DigitalCertificate,
) -> None:
    async def exercise() -> None:
        produced = 0
        completed = 0

        def source() -> Iterator[int]:
            nonlocal produced
            for i in range(100000):
                produced += 1
                yield i

        async def query(item: int) -> int:
            nonlocal completed
            completed += 1
            return item

        async with AsyncDianClient(digital_certificate) as client:
            async with aclosing(
                client.iter_queries(source(), query, workers=2, buffer_size=2)
            ) as stream:
                await anext(stream)
                for _ in range(10):
                    await asyncio.sleep(0)
                assert produced <= 10 and completed <= 7
            assert not client._batches
            assert not any(
                t.get_name().startswith("radiankore-") for t in asyncio.all_tasks()
            )

    asyncio.run(exercise())


def test_async_source_failure_propagates_and_cleans_workers(
    digital_certificate: DigitalCertificate,
) -> None:
    async def source() -> AsyncIterator[int]:
        yield 1
        raise ValueError("source failed")

    async def query(item: int) -> int:
        await asyncio.sleep(0)
        return item

    async def exercise() -> None:
        async with AsyncDianClient(digital_certificate) as client:
            with pytest.raises(ValueError, match="source failed"):
                async for _ in client.iter_queries(source(), query):
                    pass
            assert not client._batches

    asyncio.run(exercise())


@pytest.mark.parametrize("external", [False, True])
def test_cancelled_query_cancels_the_stream(
    digital_certificate: DigitalCertificate, external: bool
) -> None:
    async def exercise() -> None:
        async def query(item: int) -> int:
            if external:
                await asyncio.sleep(10)
            raise asyncio.CancelledError

        client = AsyncDianClient(digital_certificate)
        async with aclosing(client.iter_queries(range(100), query)) as stream:
            pending = asyncio.create_task(anext(stream))
            await asyncio.sleep(0)
            if external:
                await client.aclose()
            with pytest.raises(asyncio.CancelledError):
                await asyncio.wait_for(pending, 1)
        await client.aclose()

    asyncio.run(exercise())


@pytest.mark.parametrize("workers,buffer", [(0, 2), (True, 2), (2, 0), (2, True)])
def test_invalid_stream_limits(
    digital_certificate: DigitalCertificate, workers: int, buffer: int
) -> None:
    async def query(item: int) -> int:
        return item

    async def exercise() -> None:
        async with AsyncDianClient(digital_certificate) as client:
            with pytest.raises((TypeError, ValueError)):
                await anext(
                    client.iter_queries([1], query, workers=workers, buffer_size=buffer)
                )

    asyncio.run(exercise())


def test_cancelled_source_propagates(digital_certificate: DigitalCertificate) -> None:
    async def source() -> AsyncIterator[int]:
        yield 1
        raise asyncio.CancelledError

    async def query(item: int) -> int:
        return item

    async def exercise() -> None:
        async with AsyncDianClient(digital_certificate) as client:
            with pytest.raises(asyncio.CancelledError):
                async with asyncio.timeout(1):
                    async for _ in client.iter_queries(source(), query):
                        pass
            assert not client._batches

    asyncio.run(exercise())

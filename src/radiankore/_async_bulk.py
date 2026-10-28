"""Bounded streaming with one coordinator, one producer and fixed workers."""

import asyncio
from collections.abc import AsyncGenerator, AsyncIterable, Awaitable, Callable, Iterable
from dataclasses import dataclass

from radiankore.async_models import QueryResult, count


@dataclass(slots=True)
class _Finished:
    error: BaseException | None = None


class _QueryCancelled(Exception):
    """Make a cancelled worker cancel its TaskGroup siblings."""


async def iter_queries[T, R](
    items: Iterable[T] | AsyncIterable[T],
    query: Callable[[T], Awaitable[R]],
    workers: int,
    buffer_size: int,
    registry: set[asyncio.Task[None]],
) -> AsyncGenerator[QueryResult[T, R]]:
    count(workers, "workers")
    count(buffer_size, "buffer_size")
    inputs: asyncio.Queue[tuple[int, T] | None] = asyncio.Queue(buffer_size)
    outputs: asyncio.Queue[QueryResult[T, R] | _Finished] = asyncio.Queue(buffer_size)
    source_error: Exception | None = None
    query_cancelled = False

    async def produce() -> None:
        nonlocal source_error, query_cancelled
        index = 0
        try:
            if isinstance(items, AsyncIterable):
                async for item in items:
                    await inputs.put((index, item))
                    index += 1
            else:
                for item in items:
                    await inputs.put((index, item))
                    index += 1
            for _ in range(workers):
                await inputs.put(None)
        except asyncio.CancelledError as exc:
            query_cancelled = True
            raise _QueryCancelled from exc
        except Exception as exc:
            source_error = exc
            raise

    async def work() -> None:
        nonlocal query_cancelled
        while (entry := await inputs.get()) is not None:
            index, item = entry
            try:
                value = await query(item)
                result = QueryResult(index=index, item=item, value=value)
            except asyncio.CancelledError as exc:
                query_cancelled = True
                raise _QueryCancelled from exc
            except Exception as exc:
                result = QueryResult(index=index, item=item, error=exc)
            await outputs.put(result)

    async def coordinate() -> None:
        error: BaseException | None = None
        try:
            async with asyncio.TaskGroup() as group:
                group.create_task(produce(), name="radiankore-producer")
                for _ in range(workers):
                    group.create_task(work(), name="radiankore-query")
        except BaseException as exc:
            current = asyncio.current_task()
            if isinstance(exc, asyncio.CancelledError) or (
                current is not None and current.cancelling()
            ):
                # Wake a pending consumer without blocking shutdown on a full queue.
                if outputs.full():
                    outputs.get_nowait()
                outputs.put_nowait(_Finished(asyncio.CancelledError()))
                return
            error = source_error or (
                asyncio.CancelledError() if query_cancelled else exc
            )
        await outputs.put(_Finished(error))

    coordinator = asyncio.create_task(coordinate(), name="radiankore-bulk")
    registry.add(coordinator)

    def completed(task: asyncio.Task[None]) -> None:
        registry.discard(task)
        if task.cancelled():
            if outputs.full():
                outputs.get_nowait()
            outputs.put_nowait(_Finished(asyncio.CancelledError()))
        else:
            error = task.exception()
            if error is not None:
                if outputs.full():
                    outputs.get_nowait()
                outputs.put_nowait(_Finished(error))

    coordinator.add_done_callback(completed)
    try:
        while True:
            result = await outputs.get()
            if isinstance(result, _Finished):
                if result.error is not None:
                    raise result.error
                return
            yield result
    finally:
        coordinator.cancel()
        await asyncio.gather(coordinator, return_exceptions=True)
        registry.discard(coordinator)

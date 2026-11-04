"""Native admission and cleanup failures preserve capacity and task ownership."""

import asyncio

import httpx
import pytest

from radiankore._async_runtime import BoundedProcessor
from radiankore._soap.async_transport import AsyncSoapTransport
from radiankore.async_client import AsyncDianClient


def test_closed_processor_rejects_new_and_already_queued_work() -> None:
    async def exercise() -> None:
        processor = BoundedProcessor(1)
        await processor._slots.acquire()
        waiting = asyncio.create_task(
            processor.run(lambda: pytest.fail("closed job ran"))
        )
        await asyncio.sleep(0)  # Park the worker at admission.
        await processor.aclose()
        processor._slots.release()
        for operation in (waiting, processor.run(lambda: None)):
            with pytest.raises(RuntimeError, match="closed"):
                await operation
        assert not processor._pending
        assert processor._slots._value == 1

    asyncio.run(exercise())


def test_executor_submission_failure_releases_capacity(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def exercise() -> None:
        processor = BoundedProcessor(1)
        loop = asyncio.get_running_loop()
        error = RuntimeError("executor rejected submission")

        def reject(*args: object) -> None:
            raise error

        try:
            with monkeypatch.context() as patch:
                patch.setattr(loop, "run_in_executor", reject)
                with pytest.raises(RuntimeError) as caught:
                    await processor.run(lambda: None)
                assert caught.value is error
            async with asyncio.timeout(5):
                assert await processor.run(lambda: 42) == 42
        finally:
            await processor.aclose()
        assert not processor._pending and processor._slots._value == 1

    asyncio.run(exercise())


def test_completion_callbacks_tolerate_cancelled_tasks_and_futures() -> None:
    async def exercise() -> None:
        processor = BoundedProcessor(1)
        await processor._slots.acquire()
        future = asyncio.get_running_loop().create_future()
        processor._pending.add(future)
        future.cancel()
        processor._finished(future)
        processor._finished(future)  # A drain may revisit an already handled future.
        assert not processor._pending and processor._slots._value == 1
        task = asyncio.create_task(asyncio.sleep(0))
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        for callback in (
            processor._drained,
            AsyncDianClient._closed,
        ):
            callback(task)

        async def initialize() -> httpx.AsyncClient:
            raise AssertionError("Cancelled initializer must not run")

        initializer = asyncio.create_task(initialize())
        initializer.cancel()
        with pytest.raises(asyncio.CancelledError):
            await initializer
        AsyncSoapTransport._initialized(initializer)
        await processor.aclose()

    asyncio.run(exercise())

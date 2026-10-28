"""Loop affinity and bounded, cancellation-aware native processing."""

import asyncio
import functools
import os
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from contextvars import copy_context
from typing import cast


class LoopBound:
    """Bind lazily, while rejecting inherited resources after fork."""

    def __init__(self) -> None:
        self._pid = os.getpid()
        self._loop: asyncio.AbstractEventLoop | None = None

    def bind(self) -> asyncio.AbstractEventLoop:
        if self._pid != os.getpid():
            raise RuntimeError("Async resources cannot be shared across processes.")
        loop = asyncio.get_running_loop()
        if self._loop is None:
            self._loop = loop
        elif loop is not self._loop:
            raise RuntimeError("Async resources cannot be shared across event loops.")
        return loop


class BoundedProcessor(LoopBound):
    """Keep physical jobs bounded even after their coroutine is cancelled."""

    def __init__(self, workers: int) -> None:
        super().__init__()
        self._workers = workers
        self._slots = asyncio.Semaphore(workers)
        self._executor: ThreadPoolExecutor | None = None
        self._pending: set[asyncio.Future[object]] = set()
        self._closed = False
        self._close_task: asyncio.Task[None] | None = None

    async def run[T](self, function: Callable[..., T], *args: object) -> T:
        loop = self.bind()
        if self._closed:
            raise RuntimeError("Processing resources are closed.")
        await self._slots.acquire()
        try:
            if self._closed:
                raise RuntimeError("Processing resources are closed.")
            if self._executor is None:
                self._executor = ThreadPoolExecutor(
                    max_workers=self._workers, thread_name_prefix="radiankore"
                )
            future = loop.run_in_executor(
                self._executor, copy_context().run, functools.partial(function, *args)
            )
        except BaseException:
            self._slots.release()
            raise
        tracked = cast(asyncio.Future[object], future)
        self._pending.add(tracked)
        tracked.add_done_callback(self._finished)
        # Cancellation of this waiter must not cancel or release a physical job.
        return await asyncio.shield(future)

    def _finished(self, future: asyncio.Future[object]) -> None:
        if future not in self._pending:
            return
        self._pending.remove(future)
        self._slots.release()
        if not future.cancelled():
            future.exception()  # Retrieve errors from abandoned/cancelled waiters.

    async def aclose(self) -> None:
        loop = self.bind()
        self._closed = True
        if self._close_task is None:
            self._close_task = loop.create_task(
                self._drain(), name="radiankore-processing-close"
            )
            self._close_task.add_done_callback(self._drained)
        await asyncio.shield(self._close_task)

    @staticmethod
    def _drained(task: asyncio.Task[None]) -> None:
        if not task.cancelled():
            task.exception()

    async def _drain(self) -> None:
        while self._pending:
            pending = tuple(self._pending)
            await asyncio.gather(
                *(asyncio.shield(future) for future in pending),
                return_exceptions=True,
            )
            # gather(done futures) can complete without yielding to their callbacks.
            for future in pending:
                if future.done():
                    self._finished(future)
        if self._executor is not None:
            # All physical jobs have finished; never join worker threads on the loop.
            self._executor.shutdown(wait=False, cancel_futures=True)
            self._executor = None

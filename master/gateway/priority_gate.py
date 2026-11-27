"""A concurrency limit where interactive requests overtake background work that is still waiting.

A running call is never interrupted; when a slot frees up, the most urgent waiter gets it, first come first served
within the same urgency.
"""

from __future__ import annotations

import asyncio
import contextlib
import contextvars
import heapq
import itertools
from collections.abc import AsyncIterator, Iterator

import gpu_watch

INTERACTIVE, REPAIR, BACKGROUND = 0, 1, 2
_BACKGROUND_FEATURES = frozenset({"self_eval", "inbox", "optimizer", "training", "benchmark", "property_check"})
_REPAIR_FEATURES = frozenset({"debugger", "research", "doc_reader", "data_lab", "workspace_builder"})


_AS_BACKGROUND: contextvars.ContextVar[bool] = contextvars.ContextVar("as_background", default=False)


@contextlib.contextmanager
def background() -> Iterator[None]:
    """Everything called inside waits behind interactive requests, whatever feature name it uses."""
    token = _AS_BACKGROUND.set(True)
    try:
        yield
    finally:
        _AS_BACKGROUND.reset(token)


def priority_of(feature: str) -> int:
    if _AS_BACKGROUND.get():
        return BACKGROUND
    if feature in _BACKGROUND_FEATURES:
        return BACKGROUND
    return REPAIR if feature in _REPAIR_FEATURES else INTERACTIVE


async def _wait_until_safe() -> None:
    """Background work waits while the card is too hot or the battery is low; interactive requests never do."""
    for _ in range(120):
        if not await asyncio.to_thread(gpu_watch.hold_reason):
            return
        await asyncio.sleep(15)


class PriorityGate:
    def __init__(self, slots: int) -> None:
        self._free = slots
        self._waiting: list[tuple[int, int, asyncio.Future]] = []
        self._order = itertools.count()

    async def acquire(self, priority: int) -> None:
        if self._free > 0 and not self._waiting:
            self._free -= 1
            return
        future: asyncio.Future = asyncio.get_running_loop().create_future()
        heapq.heappush(self._waiting, (priority, next(self._order), future))
        try:
            await future
        except asyncio.CancelledError:
            if future.done() and not future.cancelled():
                self.release()  # the slot arrived just as the caller gave up
            raise

    def release(self) -> None:
        while self._waiting:
            _priority, _order, future = heapq.heappop(self._waiting)
            if not future.done():
                future.set_result(None)
                return
        self._free += 1

    @contextlib.asynccontextmanager
    async def slot(self, feature: str = "") -> AsyncIterator[None]:
        if priority_of(feature) == BACKGROUND:
            await _wait_until_safe()
        await self.acquire(priority_of(feature))
        try:
            yield
        finally:
            self.release()

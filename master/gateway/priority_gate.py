"""A concurrency limit where interactive requests overtake background work that is still waiting.

A running call is never interrupted; when a slot frees up, the most urgent waiter gets it, first come first served
within the same urgency.
"""

from __future__ import annotations

import asyncio
import contextlib
import heapq
import itertools
from collections.abc import AsyncIterator

INTERACTIVE, REPAIR, BACKGROUND = 0, 1, 2
_BACKGROUND_FEATURES = frozenset({"self_eval", "inbox", "optimizer", "training", "benchmark", "property_check"})
_REPAIR_FEATURES = frozenset({"debugger", "research", "doc_reader", "data_lab", "workspace_builder"})


def priority_of(feature: str) -> int:
    if feature in _BACKGROUND_FEATURES:
        return BACKGROUND
    return REPAIR if feature in _REPAIR_FEATURES else INTERACTIVE


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
        await self.acquire(priority_of(feature))
        try:
            yield
        finally:
            self.release()

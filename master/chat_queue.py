"""Tell the user when a chat request is waiting behind other model calls (one local model serves everyone)."""

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator

_state = {"active": 0}
_PATIENCE_S = 1.5


def _status(message: str) -> str:
    return "data: " + json.dumps({"type": "status", "message": message}, ensure_ascii=False) + "\n\n"


def waiting_message(ahead: int) -> str:
    return f"Sırada bekliyor: önünde {ahead} istek var, yerel model sırayla çalışıyor..." if ahead > 0 else "Model hazırlanıyor..."


async def with_queue_notice(source: AsyncIterator) -> AsyncIterator:
    """Pass `source` through; if its first chunk takes long and others are active, emit one status line."""
    ahead = _state["active"]
    _state["active"] += 1
    try:
        it = source.__aiter__()
        first = asyncio.ensure_future(it.__anext__())
        done, _ = await asyncio.wait({first}, timeout=_PATIENCE_S)
        if not done and ahead > 0:
            yield _status(waiting_message(ahead))
        try:
            yield await first
        except StopAsyncIteration:
            return
        async for chunk in it:
            yield chunk
    finally:
        _state["active"] -= 1

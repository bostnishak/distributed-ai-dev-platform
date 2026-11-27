"""One way to stream a chat command's answer: text pieces and events, with failures told to the user."""

from __future__ import annotations

import logging
import sqlite3
import subprocess
from collections.abc import AsyncIterator
from typing import Any

import httpx
from fastapi.responses import StreamingResponse

_log = logging.getLogger(__name__)
FAILURES = (httpx.HTTPError, subprocess.SubprocessError, sqlite3.Error, OSError, ValueError, TypeError, KeyError, RuntimeError)


async def _events(pieces: AsyncIterator[Any], model: str, task: str) -> AsyncIterator[str]:
    import assistant_stream_fastpaths as fp

    try:
        async for piece in pieces:
            yield fp.sse_event(piece if isinstance(piece, dict) else {"type": "token", "content": piece})
        yield fp.sse_event({"type": "done", "model": model, "task_type": task})
    except FAILURES as exc:
        _log.warning("%s command failed: %r", task, exc)
        yield fp.sse_event({"type": "error", "content": f"{type(exc).__name__}: {exc}"})


def reply(pieces: AsyncIterator[Any], model: str, task: str) -> StreamingResponse:
    return StreamingResponse(_events(pieces, model, task), media_type="text/event-stream")

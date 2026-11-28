"""Watches every token stream and cuts it the moment a local model starts to degenerate.

Quantised models sometimes loop on one line or block, pour out whitespace, or drop into prose in the middle of a code
answer. Waiting for the token limit wastes a minute; here the HTTP stream is closed within a few hundred characters and
the same request runs again with a higher repeat penalty, another seed and a slightly higher temperature. The last
attempt is left alone, so a legitimately repetitive answer is delayed but never lost.
"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextvars import ContextVar
from typing import Any

import budgets
import reasoning_mode

EXPECT_CODE: ContextVar[bool] = ContextVar("stream_expects_code", default=False)
RESTARTS = 2
_CHECK_EVERY = 120
_WHITESPACE_RUN = 400
_SAME_LINES = 12
_MAX_PERIOD = 300
_LOOP_SPAN = 800
_LOOP_REPEATS = 6
_PROSE_AFTER_CODE = 600
_log = logging.getLogger(__name__)


def _looping_tail(text: str) -> bool:
    """True when the end of the text is one unit of up to 300 characters written over and over."""
    for period in range(1, _MAX_PERIOD + 1):
        span = max(_LOOP_SPAN, _LOOP_REPEATS * period)
        if span > len(text):
            continue
        tail = text[-span:]
        if tail[period:] == tail[:-period]:
            return True
    return False


def _prose_after_code(text: str) -> bool:
    head = text.lstrip()
    if not head.startswith("```"):
        return False
    parts = head.split("```")
    return len(parts) == 3 and len(parts[2]) > _PROSE_AFTER_CODE


def find(text: str, expect_code: bool = False) -> str:
    """The reason this partial answer is degenerate, or "" when it looks healthy."""
    if len(text) - len(text.rstrip()) >= _WHITESPACE_RUN:
        return "boşluk taşması"
    lines = [line.strip() for line in text[-4000:].split("\n")[:-1] if line.strip()]
    if len(lines) >= _SAME_LINES and len(set(lines[-_SAME_LINES:])) == 1:
        return "aynı satır döngüsü"
    if _looping_tail(text[-_LOOP_REPEATS * _MAX_PERIOD:]):
        return "tekrar eden blok"
    if expect_code and _prose_after_code(text):
        return "kod bloğundan düz yazıya kayma"
    return ""


def nudged(options: dict[str, Any], attempt: int) -> dict[str, Any]:
    changed = dict(options)
    changed["repeat_penalty"] = round(float(options.get("repeat_penalty") or 1.08) + 0.1 * attempt, 2)
    changed["temperature"] = round(min(1.0, float(options.get("temperature") or 0.2) + 0.1 * attempt), 2)
    changed["seed"] = int(options.get("seed") or 0) + 7919 * attempt
    return changed


async def watched(provider: Any, model: str, messages: list[dict[str, Any]], options: dict[str, Any], timeout_s: float) -> AsyncIterator[dict[str, Any]]:
    """The provider's stream; a degenerate attempt ends with {"type": "restart"} and the request starts again."""
    expect_code = EXPECT_CODE.get()
    for attempt in range(RESTARTS + 1):
        text, checked, reason = "", 0, ""
        stream = provider.stream(model, messages, nudged(options, attempt) if attempt else options, timeout_s=timeout_s)
        try:
            async for event in stream:
                if event.get("type") == "token":
                    text += str(event.get("content") or "")
                    if attempt < RESTARTS and len(text) - checked >= _CHECK_EVERY:
                        checked, reason = len(text), find(text, expect_code)
                        if reason:
                            break
                yield event
        finally:
            close = getattr(stream, "aclose", None)
            if close:
                await close()  # closing the HTTP stream makes Ollama stop generating
        if not reason:
            return
        _log.warning("Akış kesildi (%s, %s karakter), yeniden deneniyor: %s", reason, len(text), model)
        yield {"type": "restart", "reason": reason, "chars": len(text), "attempt": attempt + 1}


async def collect(client: Any, messages: list[dict[str, Any]], expect_code: bool, **opts: Any) -> str:
    """A whole answer through the watched stream; used where the caller wants text, not tokens (file generation)."""
    budgets.spend(attempts=1)  # the run's circuit breaker: an exhausted budget stops here, before the card works for nothing
    token = EXPECT_CODE.set(expect_code)
    thinking = reasoning_mode.THINK.set(False)
    try:
        parts: list[str] = []
        async for event in client.stream(messages, **opts):
            if event.get("type") == "restart":
                parts.clear()
            elif event.get("type") == "token":
                parts.append(str(event.get("content") or ""))
        budgets.spend(tokens=(sum(len(m.get("content") or "") for m in messages) + sum(map(len, parts))) // 4)
        return "".join(parts)
    finally:
        EXPECT_CODE.reset(token)
        reasoning_mode.THINK.reset(thinking)

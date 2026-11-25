"""Queue notice: shown only when the answer is slow and other requests are active."""

from __future__ import annotations

import asyncio

import pytest

import chat_queue

pytestmark = pytest.mark.unit


async def _slow(delay: float):
    await asyncio.sleep(delay)
    yield "data: {}\n\n"


async def _collect(src):
    return [c async for c in chat_queue.with_queue_notice(src)]


def test_no_notice_for_fast_answer():
    assert asyncio.run(_collect(_slow(0))) == ["data: {}\n\n"]


def test_notice_when_waiting_behind_others(monkeypatch):
    monkeypatch.setattr(chat_queue, "_PATIENCE_S", 0.05)
    monkeypatch.setitem(chat_queue._state, "active", 2)
    out = asyncio.run(_collect(_slow(0.2)))
    assert len(out) == 2 and "önünde 2 istek" in out[0]


def test_no_notice_when_alone(monkeypatch):
    monkeypatch.setattr(chat_queue, "_PATIENCE_S", 0.05)
    assert len(asyncio.run(_collect(_slow(0.2)))) == 1

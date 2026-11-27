"""Exact cache for read-only model calls: identical instructions, input and schema give the stored answer.

Used only where the same text must give the same extraction (claims from a page or a document part). Entries expire
after a week and never cross to a different input, because the key is a hash of all of it.
"""

from __future__ import annotations

import hashlib
import json
import time
from collections.abc import Awaitable, Callable
from pathlib import Path

import diskcache

import config

_TTL_S = 7 * 86_400
_SIZE_LIMIT = 200 * 1024 * 1024
_OPEN: dict[str, diskcache.Cache] = {}

Chat = Callable[[str, str, dict], Awaitable[str]]


def _folder() -> Path:
    return config.data_dir() / "exact_cache"


def key(system: str, user: str, schema: dict, model: str) -> str:
    return hashlib.sha256(json.dumps([model, system, user, schema], sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def _store() -> diskcache.Cache:
    """One DiskCache (SQLite underneath) per data folder; the oldest entries go when it is full."""
    folder = str(_folder())
    if folder not in _OPEN:
        _OPEN[folder] = diskcache.Cache(folder, size_limit=_SIZE_LIMIT, eviction_policy="least-recently-stored")
    return _OPEN[folder]


def cached(chat: Chat, model: str, now: Callable[[], float] = time.time) -> Chat:
    """`chat` with its answers remembered."""

    async def ask(system: str, user: str, schema: dict) -> str:
        store, name = _store(), key(system, user, schema, model)
        entry = store.get(name)
        if entry and now() - entry["at"] < _TTL_S:
            return entry["answer"]
        answer = await chat(system, user, schema)
        try:
            json.loads(answer)  # only well-formed answers are worth repeating
        except ValueError:
            return answer
        store.set(name, {"at": now(), "answer": answer}, expire=_TTL_S)
        return answer

    return ask

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

import config

_TTL_S = 7 * 86_400
_MAX_ENTRIES = 2000

Chat = Callable[[str, str, dict], Awaitable[str]]


def _folder() -> Path:
    return config.data_dir() / "exact_cache"


def key(system: str, user: str, schema: dict, model: str) -> str:
    return hashlib.sha256(json.dumps([model, system, user, schema], sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def cached(chat: Chat, model: str, now: Callable[[], float] = time.time) -> Chat:
    """`chat` with its answers remembered."""

    async def ask(system: str, user: str, schema: dict) -> str:
        path = _folder() / f"{key(system, user, schema, model)}.json"
        try:
            entry = json.loads(path.read_text(encoding="utf-8"))
            if now() - entry["at"] < _TTL_S:
                return entry["answer"]
        except (OSError, ValueError, KeyError):
            entry = None
        answer = await chat(system, user, schema)
        try:
            json.loads(answer)  # only well-formed answers are worth repeating
        except ValueError:
            return answer
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"at": now(), "answer": answer}, ensure_ascii=False), encoding="utf-8")
        for old in sorted(path.parent.glob("*.json"), key=lambda p: p.stat().st_mtime)[:-_MAX_ENTRIES]:
            old.unlink(missing_ok=True)
        return answer

    return ask

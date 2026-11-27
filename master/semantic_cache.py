"""Meaning-level cache for questions about one unchanged document.

An answer is reused only when the document is byte-for-byte the same and the new question is nearly identical in
meaning (embedding similarity on the CPU) with the same numbers in it. A changed document never gets a stale answer.
"""

from __future__ import annotations

import hashlib
import json
import logging
import math
import re
import time
from collections.abc import Callable
from pathlib import Path

import httpx

import config
from gateway import local_gpu

_log = logging.getLogger(__name__)
_SIMILAR = 0.95
_KEEP = 40

Embed = Callable[[list[str]], list[list[float]]]


def _path(scope: str) -> Path:
    return config.data_dir() / "semantic_cache" / f"{hashlib.sha256(scope.encode()).hexdigest()}.json"


def _entries(scope: str) -> list[dict]:
    try:
        return json.loads(_path(scope).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []


def _cosine(first: list[float], second: list[float]) -> float:
    norm = math.sqrt(sum(a * a for a in first)) * math.sqrt(sum(b * b for b in second))
    return sum(a * b for a, b in zip(first, second, strict=False)) / norm if norm else 0.0


def _numbers(text: str) -> list[str]:
    return sorted(re.findall(r"\d+", text))


def lookup(scope: str, question: str, embed: Embed = local_gpu.embed) -> str:
    entries = _entries(scope)
    if not entries:
        return ""
    try:
        vector = embed([question])[0]
    except (httpx.HTTPError, ValueError, KeyError, IndexError) as exc:
        _log.warning("semantic cache lookup failed: %s", exc)
        return ""
    best = max(entries, key=lambda e: _cosine(vector, e["vector"]))
    return best["answer"] if _cosine(vector, best["vector"]) >= _SIMILAR and _numbers(question) == _numbers(best["question"]) else ""


def store(scope: str, question: str, answer: str, embed: Embed = local_gpu.embed) -> None:
    try:
        vector = embed([question])[0]
    except (httpx.HTTPError, ValueError, KeyError, IndexError) as exc:
        _log.warning("semantic cache store failed: %s", exc)
        return
    path = _path(scope)
    path.parent.mkdir(parents=True, exist_ok=True)
    entries = [*_entries(scope), {"question": question, "vector": vector, "answer": answer, "at": time.time()}]
    path.write_text(json.dumps(entries[-_KEEP:], ensure_ascii=False), encoding="utf-8")

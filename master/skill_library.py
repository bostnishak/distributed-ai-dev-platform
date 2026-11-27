"""Verified skill cards: projects that passed every check become references for similar later requests.

Only the structure (request summary and file list) is offered, never code, so a past project cannot overwrite what the
new request asks for.
"""

from __future__ import annotations

import json
import math
import re
from collections import Counter
from pathlib import Path
from typing import Any

import httpx

import config
from gateway import local_gpu

_WORD_RE = re.compile(r"\w{3,}")
_MIN_SCORE = 0.35
_MIN_SEMANTIC = 0.72
_KEEP = 200


def _path() -> Path:
    return Path(config.DB_PATH).resolve().parent / "skills.json"


def load() -> list[dict[str, Any]]:
    try:
        cards = json.loads(_path().read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    return cards if isinstance(cards, list) else []


def _vector(text: str) -> Counter:
    return Counter(w[:6] for w in _WORD_RE.findall(text.casefold()))


def _similarity(a: Counter, b: Counter) -> float:
    dot = sum(a[k] * b[k] for k in a.keys() & b.keys())
    norm = math.sqrt(sum(v * v for v in a.values())) * math.sqrt(sum(v * v for v in b.values()))
    return dot / norm if norm else 0.0


def _cosine(a: list[float], b: list[float]) -> float:
    norm = math.sqrt(sum(v * v for v in a)) * math.sqrt(sum(v * v for v in b))
    return sum(x * y for x, y in zip(a, b, strict=True)) / norm if norm else 0.0


def add(request: str, files: list[str]) -> None:
    summary = " ".join(request.split())[:600]
    if not summary or not files:
        return
    cards = [c for c in load() if c.get("request") != summary]
    cards.append({"request": summary, "files": files[:20]})
    path = _path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(cards[-_KEEP:], ensure_ascii=False, indent=1), encoding="utf-8")


def find(request: str) -> dict[str, Any] | None:
    cards = load()
    if not cards:
        return None
    try:
        vectors = local_gpu.embed([request[:600], *(c["request"] for c in cards[-50:])])
        query, floor, candidates = vectors[0], _MIN_SEMANTIC, cards[-50:]
        scored = [(_cosine(query, v), i, c) for i, (v, c) in enumerate(zip(vectors[1:], candidates, strict=True))]
    except (httpx.HTTPError, KeyError, ValueError):
        wanted, floor = _vector(request), _MIN_SCORE
        scored = [(_similarity(wanted, _vector(c["request"])), i, c) for i, c in enumerate(cards)]
    best = max(scored, default=None)
    return best[2] if best and best[0] >= floor else None


def reference(request: str) -> str:
    card = find(request)
    if card is None:
        return ""
    return ("\n\nDOĞRULANMIŞ BENZER PROJE (yalnızca yapı referansı; istek farklıysa isteğe uy):\n"
            f"- İstek: {card['request'][:200]}\n- Dosyalar: {', '.join(card['files'])}")

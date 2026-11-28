"""Learning without training: a failure becomes one general rule, a success becomes a verified snippet.

Both are written next to the data and offered to later requests that resemble where they came from. Nothing about a
test's expected values is kept in a rule, so a rule cannot simply repeat an answer.
"""

from __future__ import annotations

import json
import math
import re
from collections import Counter
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any

import config
import security_scan
from prompt_loader import load_prompt

_WORD_RE = re.compile(r"\w{3,}")
_MIN_SCORE = 0.18
_KEEP = 200

Generate = Callable[[str, str], Awaitable[str]]


def _path() -> Path:
    return Path(config.DB_PATH).resolve().parent / "learned.json"


def load() -> list[dict[str, Any]]:
    try:
        found = json.loads(_path().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    return found if isinstance(found, list) else []


def _save(entry: dict[str, Any]) -> None:
    entries = [e for e in load() if (e["kind"], e["text"]) != (entry["kind"], entry["text"])]
    path = _path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps([*entries, entry][-_KEEP:], ensure_ascii=False, indent=1), encoding="utf-8")


async def mine(request: str, failure: str, generate: Generate) -> str:
    """One general rule from a failure; "" when the model gives nothing usable."""
    answer = await generate(load_prompt("mine_rule.txt"), f"İSTEK:\n{request[:600]}\n\nHATA ÇIKTISI:\n{failure[-900:]}")
    rule = next((line.strip(" -*") for line in answer.splitlines() if len(line.strip()) > 15 and not line.startswith(("```", "#"))), "")
    literals = [v for v in re.findall(r"['\"]([^'\"\n]{3,})['\"]|\b(\d{3,})\b", failure) for v in v if v]
    if not rule or any(value in rule and value not in request for value in literals):
        return ""  # a rule that quotes the test's expected values would be the answer, not a lesson
    rule = security_scan.redact(rule)[:300]
    _save({"kind": "kural", "request": request[:600], "text": rule})
    return rule


def keep_snippet(request: str, code: str) -> None:
    """A function that passed its tests, kept for similar requests."""
    if 20 < len(code) < 2500:
        _save({"kind": "parça", "request": request[:600], "text": security_scan.redact(code)})


def _vector(text: str) -> Counter:
    return Counter(w[:5] for w in _WORD_RE.findall(text.casefold()))


def _similarity(first: Counter, second: Counter) -> float:
    dot = sum(first[k] * second[k] for k in first.keys() & second.keys())
    norm = math.sqrt(sum(v * v for v in first.values())) * math.sqrt(sum(v * v for v in second.values()))
    return dot / norm if norm else 0.0


def relevant(request: str, kind: str, limit: int) -> list[str]:
    wanted = _vector(request)
    scored = sorted(((_similarity(wanted, _vector(e["request"])), e["text"]) for e in load() if e["kind"] == kind), reverse=True)
    return [text for score, text in scored[:limit] if score >= _MIN_SCORE]


def hint(request: str) -> str:
    """What earlier work teaches about this request; "" when nothing resembles it."""
    parts = []
    if rules := relevant(request, "kural", 3):
        parts.append("DAHA ÖNCEKİ HATALARDAN ÇIKAN KURALLAR (uygula):\n" + "\n".join(f"- {r}" for r in rules))
    if snippets := relevant(request, "parça", 1):
        parts.append("DOĞRULANMIŞ BENZER KOD (testlerden geçti; uygunsa aynı yöntemi kullan):\n```python\n" + snippets[0] + "\n```")
    return "\n\n" + "\n\n".join(parts) if parts else ""

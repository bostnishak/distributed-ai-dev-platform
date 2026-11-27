"""Values the user marks as confidential never reach a produced document, a log or exported training data.

  <gizli>değer</gizli> anywhere in a message, or "gizli işaretle: değer"; "gizli verileri unut" clears the list.

The list is kept encrypted. The local model may read the value to do the work; every place that writes it out replaces
it. Matching ignores letter case and differences in spacing.
"""

from __future__ import annotations

import dataclasses
import json
import logging
import re
from typing import Any

import secret_store

_log = logging.getLogger(__name__)
_NAME = "confidential_values"
MASK = "[GİZLİ VERİ]"
_TAG_RE = re.compile(r"<gizli>(?P<value>.{3,300}?)</gizli>", re.IGNORECASE | re.DOTALL)
_MARK_RE = re.compile(r"^\s*gizli\s+(?:olarak\s+)?işaretle\s*:\s*(?P<value>.{3,300}?)\s*$", re.IGNORECASE | re.DOTALL)
_CLEAR_RE = re.compile(r"^\s*gizli\s+(?:verileri|işaretleri)\s+(?:unut|temizle|sil)\s*[.!]?\s*$", re.IGNORECASE)
_MAX = 100
_cache: dict[str, list[re.Pattern[str]]] = {}


def values() -> list[str]:
    try:
        stored = json.loads(secret_store.get_secret(_NAME) or "[]")
    except (ValueError, OSError, RuntimeError, KeyError) as exc:
        _log.warning("gizli değer listesi okunamadı: %r", type(exc).__name__)
        return []
    return [str(v) for v in stored if str(v).strip()]


def _save(items: list[str]) -> None:
    secret_store.set_secret(_NAME, json.dumps(items[-_MAX:], ensure_ascii=False))
    _cache.clear()


def mark(value: str) -> bool:
    value = " ".join(value.split())
    known = values()
    if len(value) < 3 or value.casefold() in (v.casefold() for v in known):
        return False
    _save([*known, value])
    return True


def forget_all() -> None:
    secret_store.delete_secret(_NAME)
    _cache.clear()


def _patterns() -> list[re.Pattern[str]]:
    if "values" not in _cache:
        longest_first = sorted(values(), key=len, reverse=True)
        _cache["values"] = [re.compile(r"\s+".join(re.escape(word) for word in value.split()), re.IGNORECASE) for value in longest_first]
    return _cache["values"]


def redact(text: str) -> str:
    if not text:
        return text
    text = _TAG_RE.sub(MASK, text)
    for pattern in _patterns():
        text = pattern.sub(MASK, text)
    return text


def scrub(data: Any) -> Any:
    """The same structure (dataclass, dict, list, tuple or text) with every confidential value replaced."""
    if isinstance(data, str):
        return redact(data)
    if isinstance(data, dict):
        return {scrub(key): scrub(value) for key, value in data.items()}
    if isinstance(data, list | tuple):
        return type(data)(scrub(item) for item in data)
    if dataclasses.is_dataclass(data) and not isinstance(data, type):
        return dataclasses.replace(data, **{f.name: scrub(getattr(data, f.name)) for f in dataclasses.fields(data) if f.init})
    return data


def observe(prompt: str) -> str:
    """Register tagged values; returns the reply for the two commands, "" otherwise."""
    for match in _TAG_RE.finditer(prompt):
        mark(match["value"])
    if command := _MARK_RE.match(prompt):
        mark(command["value"])
        return "Gizli olarak işaretlendi: bundan sonra belgelere, günlüklere ve eğitim verisine yazılmayacak."
    if _CLEAR_RE.match(prompt):
        forget_all()
        return "Gizli işaretlerin hepsi silindi."
    return ""

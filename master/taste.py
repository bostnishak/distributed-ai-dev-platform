"""What the user's own corrections say about their taste: the values they put in by hand.

When a style file is edited by hand, the corner radius, font, colours and spacing the user *added* are counted. A
value chosen in two or more edits is offered to the next design as a preference the request may overrule.
"""

from __future__ import annotations

import json
import re
from collections.abc import Iterator
from pathlib import Path

import atomic_io
import config

_PROPERTIES = {
    "köşe yuvarlaklığı": re.compile(r"border-radius\s*:\s*([^;{}\n]{1,30})", re.IGNORECASE),
    "yazı tipi": re.compile(r"font-family\s*:\s*([^;{}\n]{1,80})", re.IGNORECASE),
    "gövde yazı boyutu": re.compile(r"(?:body|html)\s*\{[^}]*?font-size\s*:\s*([\d.]+(?:px|rem))", re.IGNORECASE),
    "ana renk": re.compile(r"--(?:primary|accent|ana|vurgu)[\w-]*\s*:\s*(#[0-9a-f]{3,8})", re.IGNORECASE),
    "arka plan rengi": re.compile(r"(?:body|html)\s*\{[^}]*?background(?:-color)?\s*:\s*(#[0-9a-f]{3,8})", re.IGNORECASE),
}
_STYLE_SUFFIXES = {".css", ".html", ".htm", ".scss", ".vue", ".jsx", ".tsx", ".svelte"}
_MIN_TIMES = 2


def _file() -> Path:
    return config.data_dir() / "taste.json"


def _load() -> dict[str, dict[str, int]]:
    try:
        return json.loads(_file().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def added(old: str, new: str) -> Iterator[tuple[str, str]]:
    """(property, value) pairs the new text has and the old one did not."""
    for name, pattern in _PROPERTIES.items():
        before = {" ".join(v.split()).lower() for v in pattern.findall(old)}
        for value in dict.fromkeys(" ".join(v.split()).lower() for v in pattern.findall(new)):
            if value not in before:
                yield name, value.replace("!important", "").strip()


def learn(old: str, new: str, suffix: str) -> int:
    """Count what a hand edit introduced; returns how many values were noted."""
    if suffix.lower() not in _STYLE_SUFFIXES:
        return 0
    found = list(added(old, new))
    if found:
        counts = _load()
        for name, value in found:
            counts.setdefault(name, {})[value] = counts.get(name, {}).get(value, 0) + 1
        _file().parent.mkdir(parents=True, exist_ok=True)
        atomic_io.write_text(_file(), json.dumps(counts, ensure_ascii=False, indent=1))
    return len(found)


def brief() -> str:
    """Notes for the next design; "" until a choice has been repeated."""
    lines = []
    for name, values in _load().items():
        value, times = max(values.items(), key=lambda item: item[1])
        if times >= _MIN_TIMES:
            lines.append(f"- {name}: {value} (elle {times} kez seçildi)")
    return "\n\nKULLANICININ ELLE DÜZELTMELERİNDEN ÖĞRENİLEN ZEVKİ (bu istek aksini söylemiyorsa uygula):\n" + "\n".join(lines) if lines else ""

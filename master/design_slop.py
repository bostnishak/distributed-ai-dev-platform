"""Deterministic markers of generic 'AI template' design. They are hints for the user, never a failure."""

from __future__ import annotations

import re
from pathlib import Path

_PURPLE_GRADIENT_RE = re.compile(r"gradient\([^;]*(?:#(?:667eea|764ba2|8b5cf6|a855f7|7c3aed|6366f1)|\bpurple\b|\bviolet\b)", re.IGNORECASE)
_STOCK_COPY_RE = re.compile(r"unleash the power|elevate your|revolutionize your|seamlessly integrate|take your \w+ to the next level|gücünü ortaya çıkar|bir üst seviyeye taşı", re.IGNORECASE)
_EMOJI_RE = re.compile("[\U0001f300-\U0001faff]")
_RADIUS_RE = re.compile(r"border-radius\s*:\s*([^;}]+)", re.IGNORECASE)


def findings(ws_dir: Path, request: str) -> list[str]:
    sources = [p for p in ws_dir.rglob("*") if p.suffix in (".html", ".css") and "vendor" not in p.parts and not any(x.startswith(".") for x in p.relative_to(ws_dir).parts) and p.name != "theme.css"]
    text = "\n".join(p.read_text(encoding="utf-8", errors="replace") for p in sources)
    found = []
    if _PURPLE_GRADIENT_RE.search(text) and not re.search(r"mor|purple|violet|gradient|degrade", request, re.IGNORECASE):
        found.append("istenmemiş mor gradyan")
    if m := _STOCK_COPY_RE.search(text):
        found.append(f"kalıp reklam metni: '{m.group(0)}'")
    if len(_EMOJI_RE.findall(text)) > 6 and not _EMOJI_RE.search(request):
        found.append("fazla emoji")
    radii = {v.strip() for v in _RADIUS_RE.findall(text) if "%" not in v and v.strip() not in ("0", "999px", "9999px")}
    if len(radii) > 4:
        found.append(f"tutarsız köşe yuvarlaklığı ({len(radii)} farklı değer)")
    return found


def report(ws_dir: Path, request: str) -> str:
    found = findings(ws_dir, request)
    return "Tasarım notu: " + "; ".join(found) if found else ""

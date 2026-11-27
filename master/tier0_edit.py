"""Tier 0: edits that need no model, applied in milliseconds and exactly.

Only unambiguous requests are handled ("replace colour #A with #B", 'change the text "X" to "Y"'); anything else goes to
the model.
"""

from __future__ import annotations

import re
from pathlib import Path

_EXTS = (".html", ".css", ".js", ".py")
_HEX = r"(#[0-9a-fA-F]{6})"
_COLOR_RES = (
    re.compile(_HEX + r"(?:\s*rengini|\s*renk)?\s*(?:yerine|->|→)\s*" + _HEX, re.IGNORECASE),
    re.compile(r"(?:replace|change)\s+(?:colou?r\s+)?" + _HEX + r"\s+(?:with|to)\s+" + _HEX, re.IGNORECASE),
)
_TEXT_RE = re.compile(r"[\"“]([^\"“”\n]{2,60})[\"”]\s*(?:yazısını|metnini|yazısı|->|→)\s*[\"“]([^\"“”\n]{1,60})[\"”]", re.IGNORECASE)
_MAX_CHARS = 200
_PRIMARY_RE = re.compile(r"(?:ana|birincil|primary)\s+(?:buton|düğme|button)?\s*(?:rengi\w*|colou?r)", re.IGNORECASE)
_PRIMARY_VAR_RE = re.compile(r"(--(?:(?:btn|button)-?primary|primary(?:-?(?:color|btn|button|bg))?|color-primary|accent(?:-color)?|(?:btn|button)-(?:color|bg))\s*:\s*)(#[0-9a-fA-F]{3,8})", re.IGNORECASE)


def parse(instruction: str) -> tuple[str, str] | None:
    """(old, new) of an exact replacement, or None when the request needs a model."""
    if len(instruction) > _MAX_CHARS:
        return None
    for rx in (*_COLOR_RES, _TEXT_RE):
        if m := rx.search(instruction):
            return m.group(1), m.group(2)
    return None


def primary_colour(instruction: str) -> str:
    """The new colour of a 'make the primary button colour #X' request, else an empty string."""
    colours = re.findall(_HEX, instruction)
    return colours[0] if len(instruction) <= _MAX_CHARS and len(colours) == 1 and _PRIMARY_RE.search(instruction) else ""


def apply(ws_dir: Path, instruction: str) -> list[str]:
    """Files changed by the replacement (empty when not applicable or the old value is nowhere)."""
    pair = parse(instruction)
    if pair is not None:
        old, new = pair
        rx = re.compile(re.escape(old), re.IGNORECASE if old.startswith("#") else 0)
        replace = lambda _m: new  # noqa: E731
    elif colour := primary_colour(instruction):
        rx, replace = _PRIMARY_VAR_RE, lambda m: m.group(1) + colour
    else:
        return []
    changed = []
    for path in ws_dir.rglob("*"):
        if not path.is_file() or path.suffix not in _EXTS or any(p.startswith(".") for p in path.relative_to(ws_dir).parts):
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        updated = rx.sub(replace, text)
        if updated != text:
            path.write_text(updated, encoding="utf-8")
            changed.append(path.relative_to(ws_dir).as_posix())
    return changed

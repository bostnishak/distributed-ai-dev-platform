"""The exact things a request names (colour codes, quoted labels) must be in the generated project.

They are extracted without a model into `.spec.json` and checked against the written files; what is missing goes back to
the repair loop, so a different palette or renamed button cannot be reported as finished.
"""

from __future__ import annotations

import html
import json
import re
from pathlib import Path

_HEX_RE = re.compile(r"#[0-9a-fA-F]{6}\b")
_SIZE_RE = re.compile(r"\b\d{2,4}px\b")
_QUOTED_RE = re.compile(r"[\"“]([^\"“”\n]{2,40})[\"”]")
_VARIABLE_TAIL_RE = re.compile(r"\s*(?::.*|\.\.\.|…)$")  # "Active tasks: X" -> the fixed part only
_SOURCE_EXTS = (".html", ".css", ".js", ".py", ".json")
SPEC_FILE = ".spec.json"


def extract(request: str) -> dict[str, list[str]]:
    colors = list(dict.fromkeys(c.upper() for c in _HEX_RE.findall(request)))
    labels = (_VARIABLE_TAIL_RE.sub("", m).strip() for m in _QUOTED_RE.findall(request))
    named = list(dict.fromkeys(t for t in labels if len(t) >= 2 and not _HEX_RE.fullmatch(t)))
    return {"colors": colors, "labels": named, "sizes": list(dict.fromkeys(_SIZE_RE.findall(request)))}


def missing(ws_dir: Path, spec: dict[str, list[str]]) -> list[str]:
    """Colour codes and labels of the spec that no source file contains."""
    files = (p for p in ws_dir.rglob("*") if p.suffix in _SOURCE_EXTS and p.is_file() and not any(part.startswith(".") for part in p.relative_to(ws_dir).parts))
    source = html.unescape("\n".join(p.read_text(encoding="utf-8", errors="replace") for p in files)).casefold()
    return [item for item in [*spec["colors"], *spec["labels"], *spec["sizes"]] if item.casefold() not in source]


def problem(ws_dir: Path, request: str) -> tuple[Path, str] | None:
    """(file to repair, repair text) when the page does not carry what the request spelled out."""
    spec = extract(request)
    page = ws_dir / "index.html"
    if not page.is_file() or not any(spec.values()):
        return None
    if not (ws_dir / SPEC_FILE).is_file():
        (ws_dir / SPEC_FILE).write_text(json.dumps(spec, ensure_ascii=False, indent=2), encoding="utf-8")
    absent = missing(ws_dir, spec)
    if not absent:
        return None
    listed = ", ".join(f"'{a}'" for a in absent[:12])
    return page, f"Kullanıcının tarifinde birebir istenen şu renk kodları / yazılar / ölçüler sayfada YOK; aynen ekle, çevirme ve değiştirme: {listed}"

"""Ship a ready-made design kit with every generated web project and link it from each page.

A small local model writes plain, flat CSS. The kit (workspace_kit/theme.css) gives every project the same polished base
(tokens, dark mode, cards, buttons, forms, tables, navigation) and loads after the model's own stylesheet.
"""

from __future__ import annotations

import os
import re
from pathlib import Path

_KIT = Path(__file__).parent / "workspace_kit" / "theme.css"
_LINK_RE = re.compile(r"<link\b[^>]*rel=[\"']stylesheet[\"'][^>]*>", re.IGNORECASE)
KIT_CLASSES = (
    "container (.narrow), section, stack, row (.between), grid, center, muted, navbar (.brand, .nav-links), hero, footer, "
    "card (.hoverable), btn / btn-primary / btn-danger / btn-ghost / btn-sm / btn-lg, field, label, badge (.success/.danger), alert, "
    "list (li çocukları), tabs, stat, empty, modal-backdrop (.open) + modal, keypad, display"
)


def _pages(ws_dir: Path) -> list[Path]:
    return [p for p in ws_dir.rglob("*.html") if ".history" not in p.parts and "node_modules" not in p.parts and "dist" not in p.parts]


def inject_theme(ws_dir: Path) -> bool:
    """Copy theme.css next to each page group and add a <link> after the page's last stylesheet. True if anything changed."""
    if not _KIT.is_file():
        return False
    css, changed = _KIT.read_text(encoding="utf-8"), False
    for page in _pages(ws_dir):
        text = page.read_text(encoding="utf-8", errors="replace")
        if "theme.css" in text or "</head>" not in text.lower():
            continue
        if "<style" in text.lower() and not _LINK_RE.search(text):  # a self-contained page keeps its own design (and stays one file)
            continue
        flask_tpl = page.parent.name == "templates"
        target = (page.parent.parent / "static" / "css" / "theme.css") if flask_tpl else (page.parent / "css" / "theme.css")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(css, encoding="utf-8")
        href = "/static/css/theme.css" if flask_tpl else os.path.relpath(target, page.parent).replace("\\", "/")
        tag = f'<link rel="stylesheet" href="{href}">'
        links = list(_LINK_RE.finditer(text))
        pos = links[-1].end() if links else text.lower().index("</head>")
        page.write_text(text[:pos] + ("\n    " if links else "    ") + tag + ("\n" if not links else "") + text[pos:], encoding="utf-8")
        changed = True
    return changed

_TOGGLE_ASK_RE = re.compile(r"(gece\s*/?\s*gündüz|gündüz\s*/?\s*gece|karanlık\s+mod|koyu\s+tema|tema\s+düğme|dark\s*mode|dark\s*/\s*light|night\s+mode)", re.IGNORECASE)
_TOGGLE_HAVE_RE = re.compile(r"<(?:button|input|a|label)\b[^>]*(?:theme|tema|dark|gece|mode)[^>]*>|>\s*(?:gece|gündüz|karanlık|koyu|dark|light)[^<]{0,20}<", re.IGNORECASE)
_TOGGLE_HTML = "\n" + (Path(__file__).parent / "workspace_kit" / "theme_toggle.html").read_text(encoding="utf-8")


def ensure_theme_toggle(ws_dir: Path, request: str) -> bool:
    """The user asked for a day/night switch but the generated page has none: a small fixed toggle (theme.css understands data-theme) is added."""
    if not _TOGGLE_ASK_RE.search(request or ""):
        return False
    changed = False
    for page in _pages(ws_dir):
        text = page.read_text(encoding="utf-8", errors="replace")
        if page.parent.name == "templates" or "</body>" not in text.lower() or _TOGGLE_HAVE_RE.search(text) or "theme-toggle" in text:
            continue
        pos = text.lower().rindex("</body>")
        page.write_text(text[:pos] + _TOGGLE_HTML + text[pos:], encoding="utf-8")
        changed = True
    return changed

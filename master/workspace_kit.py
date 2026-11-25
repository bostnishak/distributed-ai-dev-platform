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

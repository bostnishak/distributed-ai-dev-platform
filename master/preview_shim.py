"""Preview-only helper for generated pages; the files in the workspace and the ZIP are never changed.

The preview frame has no same-origin right (generated code must not reach the app), so localStorage throws there and any
page that saves data would die on its first click. An in-memory stand-in keeps it working until the preview is reloaded.
"""

from __future__ import annotations

import re
from pathlib import Path

from prompt_loader import load_prompt

_HEAD_RE = re.compile(r"<head\b[^>]*>", re.IGNORECASE)


def with_storage(page: Path) -> str:
    """The page's HTML with the stand-in as its first script."""
    html = page.read_text(encoding="utf-8", errors="replace")
    tag = f"<script>{load_prompt('preview_storage.js.txt')}</script>"
    head = _HEAD_RE.search(html)
    return html[: head.end()] + tag + html[head.end() :] if head else tag + html

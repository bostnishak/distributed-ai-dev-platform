"""Surgical edits: the model returns SEARCH/REPLACE blocks, applied exactly, so untouched code cannot be lost.

If any block does not match, nothing is changed and the caller falls back to rewriting the whole file.
"""

from __future__ import annotations

import re
from collections.abc import Awaitable, Callable

from prompt_loader import load_prompt

_BLOCK_RE = re.compile(r"<{5,} *SEARCH *\n(.*?)\n?={5,} *\n(.*?)\n?>{5,} *REPLACE", re.DOTALL)
_MIN_CHARS = 1500  # tiny files are cheaper and safer to rewrite
_MAX_SHARE = 0.6  # a "patch" that replaces more than this share of the file is a rewrite and is done as one
_WHOLE_FILE = "Bu dosyanın güncel ve EKSİKSİZ tüm içeriğini yaz."
_BLOCKS_ONLY = "\n\nÖNEMLİ: Dosyanın tamamını YAZMA. Yalnızca <<<<<<< SEARCH / ======= / >>>>>>> REPLACE bloklarını döndür."


def parse(answer: str) -> list[tuple[str, str]]:
    return [(m.group(1), m.group(2)) for m in _BLOCK_RE.finditer(answer.replace("\r\n", "\n"))]


def _locate(text: str, search: str) -> tuple[int, int] | None:
    """Span of the only occurrence: exact first, then line by line ignoring indentation."""
    if search and text.count(search) == 1:
        start = text.index(search)
        return start, start + len(search)
    wanted = [line.strip() for line in search.split("\n")]
    lines = text.split("\n")
    hits = [i for i in range(len(lines) - len(wanted) + 1) if [ln.strip() for ln in lines[i : i + len(wanted)]] == wanted]
    if len(hits) != 1 or not any(wanted):
        return None
    start = sum(len(ln) + 1 for ln in lines[: hits[0]])
    return start, start + len("\n".join(lines[hits[0] : hits[0] + len(wanted)]))


def apply(text: str, blocks: list[tuple[str, str]]) -> str | None:
    """The patched text, or None when there is nothing to apply or a block is missing or ambiguous."""
    if not blocks:
        return None
    for search, replace in blocks:
        span = _locate(text, search)
        if span is None:
            return None
        text = text[: span[0]] + replace + text[span[1] :]
    return text


async def try_patch(generate: Callable[[str, str], Awaitable[str]], ask: str, current: str) -> str | None:
    """Ask for blocks and apply them; None means the caller should rewrite the file instead."""
    if len(current) < _MIN_CHARS:
        return None
    text = current.replace("\r\n", "\n")
    # the same request is used for a full rewrite, whose closing sentence would contradict the patch format
    blocks = parse(await generate(load_prompt("agent_frontend_patch.md"), ask.replace(_WHOLE_FILE, "").rstrip() + _BLOCKS_ONLY))
    if sum(len(search) for search, _replace in blocks) > _MAX_SHARE * len(text):
        return None
    patched = apply(text, blocks)
    if patched is None or patched == text or ("</html>" in text.lower() and "</html>" not in patched.lower()):
        return None
    return patched

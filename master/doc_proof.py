"""Paragraph-level proofreading of a parsed document: small, focused edits are far more reliable on a local model than one big rewrite.

Texts go to the model in small batches; a corrected text is accepted only if it keeps every number, every fill-in blank and
roughly the same length. Anything else keeps the original wording.
"""

from __future__ import annotations

import re
from typing import Any

import json_repair
from prompt_loader import load_prompt

_NUM_RE = re.compile(r"\d[\d.,]*")
_BLANK = "[................]"
_BATCH_CHARS = 2200
_MIN_LEN = 25


def _slots(blocks: list[dict[str, Any]]) -> list[tuple[dict[str, Any], str, int | None]]:
    """(block, key, index) for every proofreadable text: paragraphs, headings and list items."""
    out: list[tuple[dict[str, Any], str, int | None]] = []
    for b in blocks:
        if (b["type"] == "para" and len(b["text"]) >= _MIN_LEN) or (b["type"] == "heading" and len(b["text"]) >= 8):
            out.append((b, "text", None))
        elif b["type"] in ("numbered", "bullets"):
            out += [(b, "items", i) for i, t in enumerate(b["items"]) if len(t) >= _MIN_LEN]
    return out


def _get(slot: tuple[dict[str, Any], str, int | None]) -> str:
    block, key, idx = slot
    return block[key] if idx is None else block[key][idx]


def _put(slot: tuple[dict[str, Any], str, int | None], text: str) -> None:
    block, key, idx = slot
    if idx is None:
        block[key] = text
    else:
        block[key][idx] = text


def acceptable(old: str, new: str) -> bool:
    """Same numbers, same blanks, similar length: a proofreading edit must not change facts."""
    if not new.strip() or sorted(_NUM_RE.findall(old)) != sorted(_NUM_RE.findall(new)) or old.count(_BLANK) != new.count(_BLANK):
        return False
    return 0.6 <= len(new) / max(1, len(old)) <= 1.4


def _batches(texts: list[str]) -> list[list[int]]:
    groups: list[list[int]] = [[]]
    size = 0
    for i, t in enumerate(texts):
        if groups[-1] and size + len(t) > _BATCH_CHARS:
            groups.append([])
            size = 0
        groups[-1].append(i)
        size += len(t)
    return groups


async def proofread(blocks: list[dict[str, Any]], model: str) -> int:
    """Correct the language of the document in place; returns how many texts were changed."""
    import gateway

    slots = _slots(blocks)
    texts = [_get(s) for s in slots]
    changed = 0
    for group in _batches(texts):
        payload = {"texts": [texts[i] for i in group]}
        try:
            res = await gateway.default_client.chat(
                [{"role": "system", "content": load_prompt("b3_doc_proof.txt")}, {"role": "user", "content": __import__("json").dumps(payload, ensure_ascii=False)}],
                model=model, profile="factual", num_predict=2600, timeout_s=240.0, feature="document_factory", max_retries=0,
            )
        except (OSError, RuntimeError, ValueError, TypeError):
            continue
        fixed = (json_repair.loads_top(res.content) or {}).get("texts")
        if not isinstance(fixed, list) or len(fixed) != len(group):
            continue
        for i, new in zip(group, fixed, strict=True):
            if isinstance(new, str) and new.strip() != texts[i].strip() and acceptable(texts[i], new.strip()):
                _put(slots[i], new.strip())
                changed += 1
    return changed

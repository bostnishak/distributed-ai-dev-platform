"""What must never fall out of a long conversation: the user's own constraints.

When old turns are compacted, sentences that fix a colour, a size, a quoted label, a rule or a name are lifted out
verbatim from every earlier user message, however long ago it was said.
"""

from __future__ import annotations

import re

_PIN_RE = re.compile(
    r"#[0-9a-fA-F]{6}\b|\b\d+\s*px\b|[\"“][^\"“”\n]{2,40}[\"”]|\b(?:asla|hiçbir|her zaman|bundan sonra|mutlaka|zorunlu|olmalı|olmasın|kullanma|never|always|must)\b"
    r"|\b(?:adı|ismi|kodu|numarası)\b",
    re.IGNORECASE,
)
_SPLIT_RE = re.compile(r"(?<=[.!?])\s+|\n+")


def pinned(messages: list[dict[str, str]], budget: int = 3000) -> str:
    """Constraint sentences of the user's messages, newest wording first when the budget is short."""
    found: list[str] = []
    seen: set[str] = set()
    used = 0
    for message in reversed(messages):
        if message.get("role") != "user":
            continue
        for sentence in _SPLIT_RE.split(message.get("content", "")):
            sentence = sentence.strip()
            key = sentence.casefold()
            if not 6 <= len(sentence) <= 300 or key in seen or not _PIN_RE.search(sentence):
                continue
            if used + len(sentence) > budget:
                continue
            seen.add(key)
            found.append(sentence)
            used += len(sentence)
    return "\n".join(f"- {s}" for s in reversed(found))

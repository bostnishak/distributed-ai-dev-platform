"""A follow-up ("fix it", "build this as an app") is meaningless alone: generators must also get the request it refers to.

The general chat model already receives the history; the document, project and G-code generators only receive one text, so the
original request and the later changes are merged into that text here.
"""

from __future__ import annotations

import json
import re

_MAX_FOLLOW_UP_CHARS = 300
_MAX_BASE_CHARS = 8000
_MARK = "\n\nEK İSTEK: "
_FOLLOW_RE = re.compile(
    r"\b(?:bunu|şunu|sunu|onu|bunun|yukarıdaki|yukaridaki|önceki|onceki|aynısını|aynisini|"
    r"düzelt\w*|duzelt\w*|düzgün|duzgun|daha (?:iyi|güzel|guzel|detaylı|detayli|uzun|kısa|kisa|profesyonel)|"
    r"beğenmedim|begenmedim|olmamış|olmamis|olmadı|olmadi|bidaha|değiştir|degistir|ekle|"
    r"(?:bir daha|tekrar|yeniden) (?:yap\w*|oluştur\w*|olustur\w*|üret\w*|uret\w*|dene\w*|yaz\w*))\b|"
    r"\b(?:fix|improve|redo|rebuild|change|update|make|build|run|turn|convert) (?:it|this|that)\b|\bthe above\b|\btry again\b",
    re.IGNORECASE,
)


def is_follow_up(prompt: str) -> bool:
    return len(prompt) <= _MAX_FOLLOW_UP_CHARS and bool(_FOLLOW_RE.search(prompt))


def _items(history: str) -> list[dict]:
    try:
        items = json.loads(history or "[]")
    except (json.JSONDecodeError, TypeError):
        return []
    return [i for i in items if isinstance(i, dict)] if isinstance(items, list) else []


def merged_request(prompt: str, history: str) -> str:
    """The original request plus every change asked since, or the prompt itself when it is not a follow-up."""
    if not is_follow_up(prompt):
        return prompt
    changes: list[str] = []
    for item in reversed(_items(history)):
        said = str(item.get("text") or "").strip()
        if item.get("role") != "user" or not said or said == prompt.strip():
            continue
        if is_follow_up(said):
            changes.insert(0, said)
            continue
        return said[:_MAX_BASE_CHARS] + _MARK + " | ".join([*changes[-4:], prompt])
    return prompt


def last_answer(prompt: str, history: str) -> str:
    """The reply a follow-up points at ("turn this into a PDF"); empty for a new request."""
    if not is_follow_up(prompt):
        return ""
    return next((str(i.get("text") or "")[:6000] for i in reversed(_items(history)) if i.get("role") == "assistant" and not i.get("isError")), "")

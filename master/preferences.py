"""Standing wishes the user states in chat ("bundan sonra ... kullanma"), kept and applied to later builds.

Only explicit standing statements are stored, in the user's own words; a newer one about the same thing replaces the
older one. The list can be shown and cleared from the chat.
"""

from __future__ import annotations

import json
import re
import time
from pathlib import Path

import config
import security_scan

_STANDING_RE = re.compile(r"\b(?:bundan\s+sonra|bundan\s+böyle|her\s+zaman|hiçbir\s+zaman|asla|from\s+now\s+on|always|never)\b", re.IGNORECASE)
_WISH_RE = re.compile(r"\b(?:kullan\w*|olsun|olmasın|yap(?:ma)?\b|ekle\w*|koy\w*|yaz\w*|tercih\w*|istiyorum|istemiyorum|use|avoid|prefer)\b", re.IGNORECASE)
_LIST_RE = re.compile(r"^\s*(?:tercihlerimi|kayıtlı\s+tercihlerimi?)\s+(?:göster|listele)\W*$", re.IGNORECASE)
_CLEAR_RE = re.compile(r"^\s*tercihlerimi\s+(?:sil|temizle|unut)\W*$", re.IGNORECASE)
_NEGATION_RE = re.compile(r"\b(?:bundan|sonra|böyle|her|zaman|hiçbir|asla|artık|lütfen|kullan\w*|olsun|olmasın|yapma|yap|istemiyorum|istiyorum)\b", re.IGNORECASE)
_MAX = 20


def _path(user: str) -> Path:
    return config.data_dir() / "preferences" / f"{re.sub(r'[^A-Za-z0-9_-]', '_', user)[:60] or 'default'}.json"


def load(user: str = "default") -> list[dict]:
    try:
        return json.loads(_path(user).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []


def _subject(text: str) -> set[str]:
    return {w[:5] for w in re.findall(r"\w{3,}", _NEGATION_RE.sub(" ", text.casefold()))}


def standing_wish(prompt: str) -> str:
    """The sentence that states a lasting preference, or ''."""
    for sentence in re.split(r"(?<=[.!?])\s+|\n", prompt.strip()):
        if 8 <= len(sentence) <= 200 and not sentence.endswith("?") and _STANDING_RE.search(sentence) and _WISH_RE.search(sentence):
            return security_scan.redact(sentence.strip())
    return ""


def remember(prompt: str, user: str = "default") -> str:
    wish = standing_wish(prompt)
    if not wish:
        return ""
    subject = _subject(wish)
    kept = [item for item in load(user) if not subject or len(subject & _subject(item["text"])) < max(1, len(subject) // 2 + 1)]
    path = _path(user)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps([*kept, {"text": wish, "at": time.strftime("%Y-%m-%d")}][-_MAX:], ensure_ascii=False, indent=1), encoding="utf-8")
    return wish


def brief(user: str = "default") -> str:
    items = load(user)
    if not items:
        return ""
    lines = "\n".join(f"- {item['text']}" for item in items)
    return f"\n\nKULLANICININ KALICI TERCİHLERİ (bu istekle çelişirse bu istek geçerlidir):\n{lines}"


def command(prompt: str, user: str = "default") -> str:
    """Reply for "show / clear my preferences", else ''."""
    if _CLEAR_RE.match(prompt):
        _path(user).unlink(missing_ok=True)
        return "Kayıtlı tercihlerin silindi."
    if _LIST_RE.match(prompt):
        items = load(user)
        return "Kayıtlı tercihlerin:\n" + "\n".join(f"- {i['text']} ({i['at']})" for i in items) if items else "Kayıtlı tercihin yok."
    return ""

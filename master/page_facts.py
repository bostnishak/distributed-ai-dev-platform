"""Richer facts for web answers: read the top result pages and keep the sentences that talk about the question.

Search snippets are 2 lines; the figures a question needs (counts, dates, names) are usually in the page body. Pages are fetched
in parallel with a hard deadline, only from public hosts (rag.web.is_safe_public_url), and only the best-matching sentences are kept.
"""

from __future__ import annotations

import html
import re
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FutureTimeout

from rag.web import is_safe_public_url

_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36"
_DROP_RE = re.compile(r"<(script|style|nav|footer|header|aside|noscript|svg|form)\b.*?</\1>", re.IGNORECASE | re.DOTALL)
_SENT_RE = re.compile(r"(?<=[.!?])\s+(?=[A-ZÇĞİÖŞÜ0-9])")
_MAX_BYTES = 600_000
_DEADLINE_S = 11.0


def _text(raw: bytes, charset: str) -> str:
    page = raw.decode(charset or "utf-8", "replace")
    page = _DROP_RE.sub(" ", page)
    page = re.sub(r"</(p|div|li|h\d|tr|br)>|<br\s*/?>", ". ", page, flags=re.IGNORECASE)
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", page))).strip()


def fetch_text(url: str) -> str:
    """Visible text of one page ('' when it cannot be read or the host is not public)."""
    if not is_safe_public_url(url)[0]:
        return ""
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": _UA, "Accept-Language": "tr,en;q=0.8"}), timeout=8) as resp:
            if "html" not in resp.headers.get("Content-Type", "html"):
                return ""
            return _text(resp.read(_MAX_BYTES), resp.headers.get_content_charset() or "utf-8")
    except (urllib.error.URLError, OSError, ValueError):
        return ""


def best_sentences(text: str, terms: set[str], limit_chars: int = 650) -> str:
    """The sentences that mention most question words (and carry figures), in page order, up to `limit_chars`."""
    scored = []
    for i, sent in enumerate(_SENT_RE.split(text)):
        if not 40 <= len(sent) <= 320:
            continue
        low = sent.lower()
        hits = sum(1 for t in terms if t in low)
        if hits:
            scored.append((hits * 2 + (1 if re.search(r"\d", sent) else 0), i, sent.strip()))
    picked: list[tuple[int, str]] = []
    total = 0
    for _, i, sent in sorted(scored, key=lambda x: (-x[0], x[1])):
        if total + len(sent) > limit_chars:
            continue
        picked.append((i, sent))
        total += len(sent)
    return " ".join(s for _, s in sorted(picked))


def enrich(sources: list[dict[str, str]], query: str, top: int = 3) -> list[dict[str, str]]:
    """Add a `facts` entry (best sentences from the page body) to the first `top` sources; failures keep the snippet only."""
    terms = {w[:6] for w in re.findall(r"[\wçğıöşü]{4,}", query.lower())}
    targets = sources[:top]
    pool = ThreadPoolExecutor(max_workers=top)
    futures = [pool.submit(fetch_text, s["url"]) for s in targets]
    try:
        for s, fut in zip(targets, futures, strict=True):
            try:
                facts = best_sentences(fut.result(timeout=_DEADLINE_S), terms)
            except (FutureTimeout, OSError, ValueError):
                facts = ""
            if facts:
                s["facts"] = facts
    finally:
        pool.shutdown(wait=False, cancel_futures=True)
    return sources

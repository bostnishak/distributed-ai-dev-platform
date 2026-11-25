"""Ground plain factual questions ("X kimdir", "Y'nin başkenti") in Wikipedia instead of the model's memory.

Only the search words leave the machine, only for short factual questions, and the answer is told to rely on the quoted
extract: a small local model invents names, numbers and dates, a quoted source does not.
"""

from __future__ import annotations

import json
import logging
import re
import urllib.error
import urllib.parse
import urllib.request

log = logging.getLogger(__name__)

_FACT_RE = re.compile(
    r"\b(kimdir|kimdi|nedir|neresi\w*|nerede|nerededir|kaç\s+yıl\w*|hangi\s+yıl\w*|ne\s+zaman|başkenti|nüfus\w*|kurucu\w*|yazar\w*|"
    r"kaç\s+(?:kişi|km|metre|derece|yaşında)|who\s+(?:is|was)|what\s+is|when\s+(?:did|was)|where\s+is|capital\s+of|how\s+many)\b",
    re.IGNORECASE,
)
_NOT_FACT_RE = re.compile(
    r"\b(kod\w*|yaz\b|yazar mısın|çiz\w*|hazırla\w*|oluştur\w*|tasarla\w*|function|script|program\w*|çevir\w*|özetle\w*|şiir|hikaye|masal)\b",
    re.IGNORECASE,
)
_STOP = frozenset(
    "kaynak kaynakları bulamazsan bulursan belirt belirtir özetle anlat açıkla hakkında bilgi ver araştırma araştır yap yapar mısın hakkında kısa bir rapor hazırla olasılığı yapıldı yapıldığı kuruldu doğdu öldü nedir kimdir kimdi neresi neresidir nerede nerededir ne zaman hangi yıl yılında kaç kaçtır nüfusu başkenti is was the of when where who what how many mı mi mu mü bir bu şu o ve ile".split()
)
_TURKISH_RE = re.compile(r"[çğıöşüÇĞİÖŞÜ]|\b(nedir|kimdir|nerede|hangi|kaç|ne zaman|başkenti)\b", re.IGNORECASE)
_API = "https://{lang}.wikipedia.org/w/api.php"
_EXTRACT_CHARS = 900


def looks_factual(prompt: str) -> bool:
    text = (prompt or "").strip()
    return 0 < len(text) <= 200 and "\n" not in text and bool(_FACT_RE.search(text)) and not _NOT_FACT_RE.search(text)


def _search_terms(prompt: str) -> str:
    words = re.findall(r"[\wçğıöşüÇĞİÖŞÜ.-]+", prompt)
    keep = [w for w in words if w.lower() not in _STOP and (len(w) > 3 or w[:1].isupper() or any(c.isdigit() for c in w))]
    return " ".join(keep)[:120]


def _title_matches(terms: str, title: str) -> bool:
    """A wrong page is worse than none: at least half of the search words must show up in the page title."""
    words = [w.lower().strip(".") for w in terms.split() if w.strip(".")]
    low = title.lower()
    return bool(words) and sum(1 for w in words if w[:5] in low) * 2 >= len(words)


_CACHE: dict[tuple[str, str], tuple[str, str, str]] = {}


def _fetch(lang: str, terms: str) -> tuple[str, str, str] | None:
    """One Wikipedia search; only successes are remembered, so a rate-limit or outage is retried next time."""
    if (lang, terms) in _CACHE:
        return _CACHE[(lang, terms)]
    params = {
        "action": "query", "generator": "search", "gsrsearch": terms, "gsrlimit": "1", "prop": "extracts|info", "inprop": "url",
        "exintro": "1", "explaintext": "1", "exchars": str(_EXTRACT_CHARS), "redirects": "1", "format": "json",
    }
    req = urllib.request.Request(
        f"{_API.format(lang=lang)}?{urllib.parse.urlencode(params)}", headers={"User-Agent": "DADP-FactCheck/1.0 (local project; low volume)"}
    )
    try:
        with urllib.request.urlopen(req, timeout=3.0) as resp:
            pages = (json.loads(resp.read().decode("utf-8")).get("query") or {}).get("pages") or {}
    except (urllib.error.URLError, ValueError, OSError) as exc:
        log.debug("Wikipedia lookup skipped: %s", exc)
        return None
    page = next(iter(pages.values()), None)
    if not page or not str(page.get("extract") or "").strip():
        return None
    hit = (str(page.get("title", "")), str(page["extract"]).strip(), str(page.get("fullurl", "")))
    if len(_CACHE) < 256:
        _CACHE[(lang, terms)] = hit
    return hit


def lookup(prompt: str, *, force: bool = False) -> tuple[list[dict[str, str]], str]:
    """(sources, system note) for a factual question, or ([], "") when not applicable or nothing was found."""
    if not force and not looks_factual(prompt):
        return [], ""
    terms = _search_terms(prompt)
    langs = ("tr", "en") if _TURKISH_RE.search(prompt) else ("en", "tr")
    hit = next((h for h in (_fetch(lang, terms) for lang in langs) if h and _title_matches(terms, h[0])), None)
    if hit is None:
        return [], ""
    title, extract, url = hit
    source = {"id": "S1", "title": f"Vikipedi: {title}", "url": url, "snippet": extract[:400]}
    rule = (
        "Kural: Yanıtı yalnızca bu kaynağa dayandır. Kaynak soruyu karşılamıyorsa bunu açıkça söyle; ad, sayı veya tarih uydurma. "
        "Yanıtın sonunda kaynağın adını belirt."
        if not force
        else "Kural: Bir araştırma istendi. Önce kaynaktaki bilgileri [S1] atfıyla düzenli başlıklar altında özetle (tanım, nasıl çalışır, türler, kullanım). "
        "Kullanıcının sorduğu ülke/dönem/sayıya ait veri kaynakta yoksa bunu ayrı bir 'Kaynakta bulunmayanlar' bölümünde açıkça belirt ve hangi resmi kurumlardan "
        "(ör. ilgili bakanlık, düzenleyici kurum, istatistik kurumu) doğrulanabileceğini söyle; sayı, tarih ya da kurum raporu uydurma."
    )
    note = f"KAYNAK [S1] (Vikipedi, \"{title}\"): {extract}\n{rule}"
    return [source], note

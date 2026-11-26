"""Sources for a chat answer: live web results and Wikipedia for research and factual questions, never the model's memory alone.

Order for an explicit research request: web search (DuckDuckGo HTML, current data) -> Wikipedia -> an honest "no source" note
that forbids invented figures. Plain factual or time-sensitive questions use Wikipedia first and the web when that has nothing.
Only the search words leave the machine; set WEB_GROUNDING=0 to turn the web part off.
"""

from __future__ import annotations

import html
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request

import page_facts
import wiki_ground

_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36"
_RESULT_RE = re.compile(r'class="result__a" href="([^"]+)">(.*?)</a>.*?class="result__snippet"[^>]*>(.*?)</a>', re.DOTALL)
_FRESH_RE = re.compile(r"\b(güncel|bugün|şu\s+an|son\s+(?:durum|veri|rakam)\w*|20\d\d|kaç\s+(?:tane|adet|kişi|lira|dolar|euro)|ne\s+kadar|fiyat\w*|kur\w*|oran\w*|sayısı|istatistik\w*)\b", re.IGNORECASE)
_HOWTO_RE = re.compile(r"(nasıl\s+(?:yapılır|kurulur|yapabilirim|kullanılır|çalışır|oluşturulur|ayarlanır)|how\s+(?:do|can|to|should)\b)", re.IGNORECASE)
_SUPER_RE = re.compile(r"\ben\s+(uzun|büyük|küçük|yüksek|alçak|kalabalık|eski|yeni|derin|geniş|hızlı|pahalı|ucuz|çok|fazla|az)\b", re.IGNORECASE)
_NOT_SUPER_RE = re.compile(r"\b(kod|yaz|program|script|function|fonksiyon|şiir|hikaye|çiz|tasarla|hazırla)\w*", re.IGNORECASE)
_ARITH_RE = re.compile(r"\d\s*[x×*/+\-:÷^]\s*\d")
_NOISE = frozenset("araştırma araştır yap yapar kısa bir hakkında kaynak kaynağı kaynak bulamazsan bulursan belirt özetle anlat açıkla bilgi ver mısın misin lütfen".split())
_CACHE: dict[str, list[dict[str, str]]] = {}
NO_SOURCE_NOTE = (
    "ARAŞTIRMA NOTU: Canlı web araması kapalı ve alıntılanabilir kaynak bulunamadı. Yanıt YALNIZCA iki bölümden oluşsun: "
    "'Genel çerçeve' (konunun kavramsal özeti; hiçbir rakam, yüzde, tarih, istasyon/kişi sayısı, şirket ya da kurum raporu yazma) ve "
    "'Doğrulanması gerekenler' (kullanıcının sorduğu güncel/ülkeye özgü veriler ve hangi resmi kurumdan öğrenilebileceği). "
    "Kaynak numarası ([S1] gibi) ve 'Kaynaklar' listesi YAZMA."
)


def web_enabled() -> bool:
    return os.environ.get("WEB_GROUNDING", "1") != "0"


def _query(prompt: str) -> str:
    words = [w for w in re.findall(r"[\wçğıöşüÇĞİÖŞÜ.-]+", prompt) if w.lower() not in _NOISE]
    return " ".join(words)[:140]


def _clean(fragment: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<.*?>", "", fragment))).strip()


def _real_url(href: str) -> str:
    """DuckDuckGo wraps result links in a redirect; the real address is in the `uddg` parameter."""
    href = html.unescape(href)
    qs = urllib.parse.parse_qs(urllib.parse.urlparse(href).query)
    return urllib.parse.unquote(qs["uddg"][0]) if "uddg" in qs else href


def web_search(query: str, limit: int = 5) -> list[dict[str, str]]:
    """[{id, title, url, snippet}] from a live web search; [] when the web is off or unreachable."""
    if not web_enabled() or not query.strip():
        return []
    if query in _CACHE:
        return _CACHE[query]
    url = "https://html.duckduckgo.com/html/?" + urllib.parse.urlencode({"q": query, "kl": "tr-tr"})
    out: list[dict[str, str]] = []
    for attempt in range(3):  # the search page sometimes comes back empty (rate limit); a short pause and one more try usually fixes it
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": _UA}), timeout=12) as resp:
                page = resp.read().decode("utf-8", "replace")
        except (urllib.error.URLError, OSError, ValueError):
            page = ""
        out = [
            {"id": f"S{i}", "title": _clean(t)[:120], "url": _real_url(u), "snippet": _clean(s)[:380]}
            for i, (u, t, s) in enumerate(_RESULT_RE.findall(page)[:limit], 1)
        ]
        if out:
            break
        time.sleep(1.5 * (attempt + 1))
    if out:
        _CACHE[query] = out
    return out


def _web_note(sources: list[dict[str, str]], research: bool = True) -> str:
    lines = "\n".join(
        f"[{s['id']}] {s['title']} ({s['url']}): {s['snippet']}" + (f"\n    SAYFADAN: {s['facts']}" if s.get("facts") else "") for s in sources
    )
    form = (
        "Yanıt biçimi: '## Özet' (4-6 madde; her madde kaynaklardaki somut bir rakam/olgu/tarih ve sonunda [S#]), '## Ayrıntılar' (kaynakları karşılaştıran "
        "kısa paragraflar; farklı rakamlar varsa hepsini ve nedenini ver), '## Dikkat' (kaynaklarda bulunmayan ya da güncelliği belirsiz kısımlar). "
        "Giriş cümlesi, özür ve 'kaynaklardan derledim' gibi boş cümleler yazma; Kaynaklar listesini yazma (sistem ekler)."
        if research
        else "Kısa ve doğrudan cevap ver; her olgunun yanına [S#] koy."
    )
    return (
        "WEB ARAMA SONUÇLARI (güncel; yalnızca bu kaynaklara dayanarak yanıtla ve her olgunun yanına [S1], [S2] gibi atıf koy; "
        "kaynaklarda olmayan sayı/tarih yazma, kaynaklar çelişiyorsa bunu söyle). " + form + "\n" + lines
    )


def build(prompt: str, research: bool) -> tuple[list[dict[str, str]], str]:
    """(sources, system note) for this prompt, or ([], "") when no grounding applies."""
    if research:
        sources = page_facts.enrich(web_search(_query(prompt)), _query(prompt))
        if sources:
            return sources, _web_note(sources)
        wiki_sources, wiki_note = wiki_ground.lookup(prompt, force=True)
        return wiki_sources, wiki_note or NO_SOURCE_NOTE
    if (_HOWTO_RE.search(prompt) or _SUPER_RE.search(prompt)) and len(prompt) <= 300 and not _NOT_SUPER_RE.search(prompt) and not _ARITH_RE.search(prompt):
        how = page_facts.enrich(web_search(_query(prompt)), _query(prompt), top=3)
        if how:
            extra = (
                "\nBu bir NASIL YAPILIR sorusu: numaralı, uygulanabilir adımlarla anlat (komutları yaz); kaynaklardaki adımlara sadık kal."
                if _HOWTO_RE.search(prompt)
                else "\nOlgu sorusu: cevabı kaynaklardaki bilgiye dayandır; kendi hafızandan farklı bir şey söyleme."
            )
            return how, _web_note(how, research=False) + extra
    sources, note = wiki_ground.lookup(prompt)
    if sources or not (wiki_ground.looks_factual(prompt) and _FRESH_RE.search(prompt)):
        return sources, note
    web = page_facts.enrich(web_search(_query(prompt)), _query(prompt), top=2)
    return web, _web_note(web, research=False) if web else ""

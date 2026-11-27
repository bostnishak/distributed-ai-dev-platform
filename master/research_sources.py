"""Sources besides the web search: arXiv, GitHub, PyPI, npm, MDN and the documentation downloaded for offline use.

Every source is free and needs no key. A connector is asked only when the question names its field, and each page it
returns carries the publication date in its title when the source states one. The offline documentation answers
without any network at all.
"""

from __future__ import annotations

import functools
import html
import json
import logging
import re
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from xml.etree import ElementTree

import config

_log = logging.getLogger(__name__)
_AGENT = {"User-Agent": "research-reader/1.0", "Accept": "application/json, application/atom+xml"}
_PER_SOURCE = 2
_ATOM = "{http://www.w3.org/2005/Atom}"
_WANTS = {
    "arxiv": re.compile(r"arxiv|makale|akademik|paper|bilimsel|algoritma\w*\s+çalışma", re.IGNORECASE),
    "github": re.compile(r"github|depo\w*|repository|\brepo\b|açık kaynak|open[- ]source|kütüphane|library", re.IGNORECASE),
    "pypi": re.compile(r"pypi|\bpip\b|python\s+(?:paket|package|kütüphane|library)\w*", re.IGNORECASE),
    "npm": re.compile(r"\bnpm\b|node(?:\.js)?\s+(?:paket|package|kütüphane|library)\w*|javascript\s+(?:paket|package|kütüphane|library)\w*", re.IGNORECASE),
    "mdn": re.compile(r"\bmdn\b|\bhtml\b|\bcss\b|javascript|\bdom\b|web\s*api|tarayıcı", re.IGNORECASE),
}
_DOCSETS = {"python": "python~3.12", "fastapi": "fastapi", "sqlite": "sqlite", "playwright": "playwright", "html": "html", "css": "css", "javascript": "javascript", "dom": "dom"}
_STOP = frozenset("the and for with how what use using deep research docs documentation python fastapi sqlite playwright html css javascript dom package library arxiv github pypi pip npm mdn node repo repository paper".split())
_TURKISH_STEMS = ("makale", "depo", "paket", "belge", "hakk", "nedir", "nas", "icin", "ile", "bir", "arast", "olan", "son", "yeni", "ayarla", "kullan", "anlat", "bul", "ara")


@dataclass(frozen=True)
class Page:
    url: str
    title: str
    text: str
    published: str = ""

    def dated_title(self) -> str:
        return f"{self.title} (yayın/güncelleme: {self.published})" if self.published else self.title


def _get(url: str) -> bytes:
    if not url.startswith("https://"):
        raise ValueError(f"yalnız https: {url}")
    with urllib.request.urlopen(urllib.request.Request(url, headers=_AGENT), timeout=12) as resp:
        return resp.read(4_000_000)


def terms(query: str) -> list[str]:
    """The English-looking words of the question that say what is asked about."""
    words = [w.strip(".,:;!?()[]\"'") for w in query.split()]
    english = [w for w in words if re.fullmatch(r"[A-Za-z][A-Za-z0-9_.+-]{2,}", w) and w.lower() not in _STOP and not w.lower().startswith(_TURKISH_STEMS)]
    return list(dict.fromkeys(english))[:6]


def _plain(markup: str) -> str:
    markup = re.sub(r"<(script|style)\b.*?</\1>", " ", markup, flags=re.DOTALL | re.IGNORECASE)
    return re.sub(r"[ \t]+", " ", html.unescape(re.sub(r"<[^>]+>", " ", markup))).strip()


def arxiv(words: list[str]) -> list[Page]:
    search = " AND ".join(f"all:{w}" for w in words[:4])
    raw = _get("https://export.arxiv.org/api/query?" + urllib.parse.urlencode({"search_query": search, "max_results": _PER_SOURCE, "sortBy": "relevance"}))
    if b"<!DOCTYPE" in raw or b"<!ENTITY" in raw:
        raise ValueError("beklenmeyen XML")
    pages = []
    for entry in ElementTree.fromstring(raw).findall(f"{_ATOM}entry"):
        title, link = " ".join(entry.findtext(f"{_ATOM}title", "").split()), entry.findtext(f"{_ATOM}id", "").replace("http://", "https://")
        summary = " ".join(entry.findtext(f"{_ATOM}summary", "").split())
        authors = ", ".join(a.findtext(f"{_ATOM}name", "") for a in entry.findall(f"{_ATOM}author")[:4])
        pages.append(Page(link, f"arXiv: {title}", f"{title}\nAuthors: {authors}\n{summary}", entry.findtext(f"{_ATOM}published", "")[:10]))
    return pages


def github(words: list[str]) -> list[Page]:
    data = json.loads(_get("https://api.github.com/search/repositories?" + urllib.parse.urlencode({"q": " ".join(words[:3]), "per_page": _PER_SOURCE})))
    return [Page(item["html_url"], f"GitHub: {item['full_name']}",
                 f"{item['full_name']}: {item.get('description') or ''}\nStars: {item['stargazers_count']}. Language: {item.get('language')}. "
                 f"License: {(item.get('license') or {}).get('spdx_id')}. Open issues: {item['open_issues_count']}. Last push: {item['pushed_at'][:10]}.",
                 item["pushed_at"][:10]) for item in data.get("items", [])[:_PER_SOURCE]]


def pypi(words: list[str]) -> list[Page]:
    pages = []
    for word in words[:4]:
        try:
            data = json.loads(_get(f"https://pypi.org/pypi/{urllib.parse.quote(word.lower())}/json"))
        except urllib.error.HTTPError:
            continue  # not a package name
        info = data["info"]
        uploaded = max((f["upload_time"][:10] for f in data.get("urls", [])), default="")
        pages.append(Page(f"https://pypi.org/project/{info['name']}/", f"PyPI: {info['name']} {info['version']}",
                          f"{info['name']} {info['version']}: {info.get('summary') or ''}\nRequires Python: {info.get('requires_python') or '-'}\n{(info.get('description') or '')[:5000]}", uploaded))
        if len(pages) == _PER_SOURCE:
            break
    return pages


def npm(words: list[str]) -> list[Page]:
    found = json.loads(_get("https://registry.npmjs.org/-/v1/search?" + urllib.parse.urlencode({"text": " ".join(words[:3]), "size": _PER_SOURCE})))
    pages = []
    for item in found.get("objects", [])[:_PER_SOURCE]:
        package = item["package"]
        pages.append(Page(f"https://www.npmjs.com/package/{package['name']}", f"npm: {package['name']} {package['version']}",
                          f"{package['name']} {package['version']}: {package.get('description') or ''}\nKeywords: {', '.join(package.get('keywords') or [])}\n"
                          f"Published: {package.get('date', '')[:10]}. License: {package.get('license') or '-'}.", package.get("date", "")[:10]))
    return pages


def mdn(words: list[str]) -> list[Page]:
    found = json.loads(_get("https://developer.mozilla.org/api/v1/search?" + urllib.parse.urlencode({"q": " ".join(words[:4]), "locale": "en-US"})))
    pages = []
    for item in found.get("documents", [])[:_PER_SOURCE]:
        url = "https://developer.mozilla.org" + item["mdn_url"]
        document = json.loads(_get(url + "/index.json"))["doc"]
        body = "\n".join(_plain(str(part.get("value", {}).get("content") or "")) for part in document.get("body", []))
        pages.append(Page(url, f"MDN: {item['title']}", f"{item.get('summary') or ''}\n{body}"[:9000], str(document.get("modified", ""))[:10]))
    return pages


@functools.lru_cache(maxsize=3)
def _docset(slug: str) -> tuple[list[dict], dict[str, str]]:
    folder = config.data_dir() / "vendor" / "docs" / slug
    return json.loads((folder / "index.json").read_text(encoding="utf-8"))["entries"], json.loads((folder / "db.json").read_text(encoding="utf-8"))


def offline_docs(query: str, limit: int = 3) -> list[Page]:
    """Entries of the downloaded documentation whose names match the question; [] when none was downloaded."""
    lowered = query.casefold()
    slugs = [slug for name, slug in _DOCSETS.items() if re.search(rf"\b{name}\b", lowered)]
    words = [part for w in terms(query) for part in re.split(r"[._\-]+", w.lower()) if len(part) > 2]
    scored: list[tuple[float, str, str, str]] = []
    for slug in slugs[:3]:
        try:
            entries, _pages = _docset(slug)
        except (OSError, ValueError, KeyError):
            continue
        for entry in entries:
            parts = re.split(r"[\s._()\-:/]+", entry["name"].lower())
            hits = sum(1 for w in words if w in parts or any(w == p.rstrip("s") for p in parts))
            if hits:
                scored.append((hits * 10 - len(parts) * 0.2, slug, entry["path"], entry["name"]))
    pages: dict[str, Page] = {}
    for _score, slug, path, name in sorted(scored, key=lambda s: -s[0]):
        key = path.split("#")[0]
        text = _plain(_docset(slug)[1].get(key, ""))
        url = f"https://devdocs.io/{slug}/{key}"
        if len(text) > 200:
            pages.setdefault(url, Page(url, f"Çevrimdışı belge ({slug}): {name}", text[:12000]))
        if len(pages) == limit:
            break
    return list(pages.values())


def online(query: str) -> list[Page]:
    """What the connectors that fit this question found; a connector that fails is skipped and logged."""
    words = terms(query)
    if not words:
        return []
    found: list[Page] = []
    for name, wanted in _WANTS.items():
        if not wanted.search(query):
            continue
        try:
            found += globals()[name](words)
        except (urllib.error.URLError, OSError, ValueError, KeyError, TypeError, ElementTree.ParseError) as exc:
            _log.warning("bağlayıcı %s yanıt vermedi: %r", name, exc)
    return found

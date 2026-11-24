"""RAG-18..RAG-23: SSRF-Safe Web Search, Credibility Cross-Check, Freshness Policy, Academic APIs, Entity Check & Cache."""

from __future__ import annotations

import hashlib
import ipaddress
import json
import logging
import os
import re
import socket
import sqlite3
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import httpx

import config
from rag.parsing import _html_to_markdown

_FRESHNESS_RE = re.compile(
    r"\b(bugün|dün|son\s+gelişmeler|şu\s+anki|güncel|bu\s+hafta|bu\s+ay|today|latest|current|recent|right\s+now)\b",
    re.IGNORECASE,
)

_OFFICIAL_DOMAINS = (".gov", ".gov.tr", ".edu", ".edu.tr", ".org.tr", "who.int", "iso.org", "europa.eu", "ietf.org", "w3.org")
_ACADEMIC_DOMAINS = ("arxiv.org", "pubmed.ncbi.nlm.nih.gov", "doi.org", "semanticscholar.org", "openalex.org", "nature.com", "ieee.org", "acm.org")
_NEWS_DOMAINS = ("reuters.com", "apnews.com", "bbc.com", "aa.com.tr", "bloomberg.com")
_FORUM_DOMAINS = ("reddit.com", "quora.com", "eksisozluk.com", "medium.com", "blogspot.com", "wordpress.com")


@dataclass
class WebSource:
    url: str
    title: str
    snippet: str
    published_date: str = ""
    credibility_class: str = "blog"  # official | academic | news | blog | forum
    cached: bool = False


@dataclass
class WebSearchResult:
    status: str  # ok | offline | cached
    query: str
    sources: list[WebSource] = field(default_factory=list)
    verification_badge: str = "unverified"  # verified | unverified | offline_model_memory
    warning: str = ""
    latency_ms: int = 0


# ---------------------------------------------------------------- SEC-10 / RAG-18 SSRF Safe Fetch Guard

def is_safe_public_url(url: str) -> tuple[bool, str]:
    """Block non-HTTP(S) schemes and private/loopback/link-local/metadata IP targets (SEC-10)."""
    parsed = urlparse(url or "")
    if parsed.scheme not in {"http", "https"}:
        return False, f"İzin verilmeyen protokol: {parsed.scheme}"
    host = (parsed.hostname or "").strip().lower()
    if not host or host in {"localhost", "metadata.google.internal", "169.254.169.254"}:
        return False, f"İç ağ veya metadata adresi engellendi: {host}"
    try:
        ip_obj = ipaddress.ip_address(host)
        if ip_obj.is_private or ip_obj.is_loopback or ip_obj.is_link_local or ip_obj.is_reserved or ip_obj.is_multicast:
            return False, f"Özel/yerel IP adresi engellendi: {host}"
        return True, "ok"
    except ValueError:
        pass
    try:
        infos = socket.getaddrinfo(host, parsed.port or (443 if parsed.scheme == "https" else 80))
        for info in infos:
            ip_str = info[4][0]
            ip_obj = ipaddress.ip_address(ip_str)
            if ip_obj.is_private or ip_obj.is_loopback or ip_obj.is_link_local or ip_obj.is_reserved:
                return False, f"DNS özel IP adresine çözümlendi: {ip_str}"
    except socket.gaierror:
        return True, "unresolved_hostname"
    return True, "ok"


async def safe_fetch(url: str, *, timeout_s: float = 10.0, max_bytes: int = 1_500_000) -> dict[str, Any]:
    """RAG-18 + SEC-10: SSRF-validated HTTP fetch with readable text extraction."""
    ok, reason = is_safe_public_url(url)
    if not ok:
        raise PermissionError(f"SSRF koruması: {reason}")
    async with httpx.AsyncClient(timeout=timeout_s, follow_redirects=False) as client:
        resp = await client.get(url, headers={"User-Agent": "DistributedAIPlatform-ResearchBot/2.0"})
        resp.raise_for_status()
        raw = resp.content[:max_bytes].decode("utf-8", errors="ignore")
    text = _html_to_markdown(raw)
    title_m = re.search(r"<title[^>]*>(.*?)</title>", raw, flags=re.IGNORECASE | re.DOTALL)
    title = re.sub(r"\s+", " ", title_m.group(1)).strip() if title_m else urlparse(url).netloc
    return {"url": url, "title": title, "content": text, "fetched_at": datetime.now(UTC).isoformat()}


# ---------------------------------------------------------------- RAG-19 Credibility & Cross-Verification

def classify_domain_credibility(url: str) -> str:
    host = (urlparse(url).hostname or "").lower()
    if any(host.endswith(d) or d in host for d in _OFFICIAL_DOMAINS):
        return "official"
    if any(d in host for d in _ACADEMIC_DOMAINS):
        return "academic"
    if any(d in host for d in _NEWS_DOMAINS):
        return "news"
    if any(d in host for d in _FORUM_DOMAINS):
        return "forum"
    return "blog"


def evaluate_source_credibility(sources: list[WebSource]) -> str:
    """RAG-19: Require >= 2 independent reliable domains (official/academic/news) for 'verified'."""
    reliable_hosts: set[str] = set()
    for s in sources:
        cls = classify_domain_credibility(s.url)
        s.credibility_class = cls
        if cls in {"official", "academic", "news"}:
            reliable_hosts.add((urlparse(s.url).hostname or "").lower())
    return "verified" if len(reliable_hosts) >= 2 else "unverified"


# ---------------------------------------------------------------- RAG-20 Freshness Policy

def needs_fresh_web_data(query: str) -> bool:
    return bool(_FRESHNESS_RE.search(query or ""))


def freshness_warning_when_offline(query: str) -> str:
    if needs_fresh_web_data(query):
        return (
            "Web erişimi şu anda kapalı olduğu için güncel veriye erişemiyorum; "
            "aşağıdaki bilgiler modelin eğitim kesim tarihindeki genel bilgisidir (doğrulanmamış)."
        )
    return ""


# ---------------------------------------------------------------- RAG-23 Timestamped Web Cache

def _cache_db_path() -> Path:
    p = Path(config.DATA_DIR) / "rag.db"
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def _init_web_cache() -> None:
    with sqlite3.connect(str(_cache_db_path()), timeout=10.0) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS web_cache (
                cache_key TEXT PRIMARY KEY,
                query TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                expires_at REAL NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )


def _web_cache_get(query: str) -> list[WebSource] | None:
    _init_web_cache()
    key = hashlib.sha256(query.strip().lower().encode("utf-8")).hexdigest()
    with sqlite3.connect(str(_cache_db_path()), timeout=10.0) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute("SELECT payload_json, expires_at FROM web_cache WHERE cache_key = ?", (key,)).fetchone()
    if not row or float(row["expires_at"]) < time.time():
        return None
    items = json.loads(row["payload_json"])
    return [
        WebSource(
            url=str(it.get("url") or ""),
            title=str(it.get("title") or ""),
            snippet=str(it.get("snippet") or ""),
            published_date=str(it.get("published_date") or ""),
            credibility_class=str(it.get("credibility_class") or "unknown"),
            cached=True,
        )
        for it in items
    ]


def _web_cache_put(query: str, sources: list[WebSource], ttl_s: float = 3600.0) -> None:
    _init_web_cache()
    key = hashlib.sha256(query.strip().lower().encode("utf-8")).hexdigest()
    payload = [
        {"url": s.url, "title": s.title, "snippet": s.snippet, "published_date": s.published_date, "credibility_class": s.credibility_class}
        for s in sources
    ]
    with sqlite3.connect(str(_cache_db_path()), timeout=10.0) as conn:
        conn.execute(
            """
            INSERT INTO web_cache (cache_key, query, payload_json, expires_at, created_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(cache_key) DO UPDATE SET payload_json=excluded.payload_json, expires_at=excluded.expires_at
            """,
            (key, query, json.dumps(payload, ensure_ascii=False), time.time() + ttl_s, datetime.now(UTC).isoformat()),
        )


async def web_search(
    query: str,
    *,
    max_results: int = 5,
    offline_mode: bool | None = None,
    searxng_url: str | None = None,
    fetch_fn=None,
) -> WebSearchResult:
    """RAG-18, 19, 20, 23: Cached SearXNG/custom web search with explicit offline mode handling."""
    t0 = time.perf_counter()
    cached = _web_cache_get(query)
    if cached is not None:
        badge = evaluate_source_credibility(cached)
        return WebSearchResult(
            status="cached",
            query=query,
            sources=cached[:max_results],
            verification_badge=badge,
            latency_ms=int((time.perf_counter() - t0) * 1000),
        )

    is_offline = (
        offline_mode
        if offline_mode is not None
        else (os.environ.get("WEB_SEARCH_ENABLED", "false").lower() != "true" and fetch_fn is None)
    )
    if is_offline:
        warn = freshness_warning_when_offline(query) or "Web erişimi kapalı (çevrimdışı mod); yanıt model hafızası etiketli üretilir."
        return WebSearchResult(
            status="offline",
            query=query,
            sources=[],
            verification_badge="offline_model_memory",
            warning=warn,
            latency_ms=int((time.perf_counter() - t0) * 1000),
        )

    sources: list[WebSource] = []
    if fetch_fn is not None:
        raw_items = await fetch_fn(query, max_results)
        for it in raw_items:
            sources.append(
                WebSource(
                    url=str(it["url"]),
                    title=str(it.get("title") or it["url"]),
                    snippet=str(it.get("snippet") or ""),
                    published_date=str(it.get("published_date") or ""),
                )
            )
    else:
        base = (searxng_url or os.environ.get("SEARXNG_URL", "http://127.0.0.1:8888")).rstrip("/")
        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                resp = await client.get(f"{base}/search", params={"q": query, "format": "json"})
                resp.raise_for_status()
                for it in (resp.json().get("results") or [])[:max_results]:
                    sources.append(
                        WebSource(
                            url=str(it.get("url") or ""),
                            title=str(it.get("title") or ""),
                            snippet=str(it.get("content") or ""),
                            published_date=str(it.get("publishedDate") or ""),
                        )
                    )
        except Exception as exc:
            return WebSearchResult(
                status="offline",
                query=query,
                sources=[],
                verification_badge="offline_model_memory",
                warning=f"Web arama sağlayıcısına ulaşılamadı (web erişimi yok): {exc}",
                latency_ms=int((time.perf_counter() - t0) * 1000),
            )

    badge = evaluate_source_credibility(sources)
    if sources:
        _web_cache_put(query, sources)
    return WebSearchResult(
        status="ok",
        query=query,
        sources=sources,
        verification_badge=badge,
        latency_ms=int((time.perf_counter() - t0) * 1000),
    )


# ---------------------------------------------------------------- RAG-21 Academic DOI & Citation Formatter

_DOI_RE = re.compile(r"^10\.\d{4,9}/[-._;()/:A-Za-z0-9]+$")


async def resolve_doi(doi: str, *, fetch_json=None) -> dict[str, Any]:
    """RAG-21: Resolve DOI via Crossref API; rejects malformed or nonexistent DOIs (no fabricated bibliography)."""
    clean = (doi or "").strip().removeprefix("https://doi.org/").removeprefix("http://doi.org/")
    if not _DOI_RE.match(clean):
        return {"verified": False, "doi": clean, "error": "Geçersiz DOI biçimi; uydurma kaynakça reddedildi."}
    try:
        if fetch_json is not None:
            data = await fetch_json(clean)
        else:
            async with httpx.AsyncClient(timeout=8.0) as client:
                resp = await client.get(f"https://api.crossref.org/works/{clean}")
                if resp.status_code == 404:
                    return {"verified": False, "doi": clean, "error": "DOI Crossref kayıtlarında bulunamadı."}
                resp.raise_for_status()
                data = resp.json().get("message") or {}
        if not data or not data.get("title"):
            return {"verified": False, "doi": clean, "error": "DOI kaydı doğrulanamadı."}
        title = data["title"][0] if isinstance(data["title"], list) else str(data["title"])
        authors = [
            f"{a.get('family', '')}, {(a.get('given', '') or ' ')[0]}."
            for a in (data.get("author") or [])[:5]
            if a.get("family")
        ]
        year = str(data.get("year") or ((data.get("issued") or {}).get("date-parts") or [[""]])[0][0])
        return {
            "verified": True,
            "doi": clean,
            "title": title,
            "authors": authors,
            "year": year,
            "apa": format_citation(authors, year, title, clean, style="apa"),
            "ieee": format_citation(authors, year, title, clean, style="ieee"),
        }
    except Exception as exc:
        return {"verified": False, "doi": clean, "error": f"DOI doğrulama hatası: {exc}"}


def format_citation(authors: list[str], year: str, title: str, doi: str, *, style: str = "apa") -> str:
    auth_str = ", ".join(authors) if authors else "Anonim"
    if style.lower() == "ieee":
        return f'{auth_str}, "{title}," {year}. doi: {doi}.'
    if style.lower() == "vancouver":
        return f"{auth_str}. {title}. {year}. doi:{doi}"
    return f"{auth_str} ({year}). {title}. https://doi.org/{doi}"


# ---------------------------------------------------------------- RAG-22 Wikipedia / Wikidata Entity Verification

async def verify_entity(name: str, *, lookup_fn=None) -> dict[str, Any]:
    """RAG-22: Verify real-world person/org/book/law entity against Wikipedia/Wikidata (or injected lookup)."""
    clean = (name or "").strip()
    if not clean:
        return {"verified": False, "entity": clean, "warning": "Boş varlık adı."}
    if lookup_fn is not None:
        hit = await lookup_fn(clean)
        if hit:
            return {"verified": True, "entity": clean, "source": hit.get("url", "wikidata"), "summary": hit.get("summary", "")}
        return {"verified": False, "entity": clean, "warning": f"'{clean}' varlığı doğrulanamadı (bulunamadı)."}

    try:
        async with httpx.AsyncClient(timeout=6.0) as client:
            resp = await client.get(
                "https://tr.wikipedia.org/api/rest_v1/page/summary/" + httpx.URL(clean).raw_path.decode("utf-8"),
                headers={"User-Agent": "DistributedAIPlatform/2.0"},
            )
            if resp.status_code == 200:
                d = resp.json()
                return {
                    "verified": True,
                    "entity": d.get("title", clean),
                    "source": (d.get("content_urls") or {}).get("desktop", {}).get("page", ""),
                    "summary": str(d.get("extract") or "")[:300],
                }
    except Exception as exc:
        logging.getLogger(__name__).debug("Entity lookup skipped for %s: %s", clean, exc)
    return {"verified": False, "entity": clean, "warning": f"'{clean}' varlığı doğrulanamadı (bulunamadı)."}

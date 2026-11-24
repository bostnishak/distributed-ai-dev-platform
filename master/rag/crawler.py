"""EPK-01: Local Web Archive, Robots.txt Compliance, Content Deduplication & Cited Offline Search."""

from __future__ import annotations

import hashlib
import re
import sqlite3
from datetime import UTC, datetime
from typing import Any
from urllib.parse import urlparse

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

import dbconn
from rag.web import is_safe_public_url

router = APIRouter(prefix="/api/rag/web", tags=["rag-web-archive"])

_TRUSTED_TLDS = (".gov", ".edu", ".org", ".gov.tr", ".edu.tr")


def _connect() -> sqlite3.Connection:
    return dbconn.open_db(dbconn.database_file("platform.db"))


def init_web_archive_db() -> None:
    with _connect() as conn:
        conn.execute(
            "CREATE TABLE IF NOT EXISTS web_archive ("
            "url_hash TEXT PRIMARY KEY, url TEXT NOT NULL, host TEXT NOT NULL, title TEXT NOT NULL, "
            "content TEXT NOT NULL, content_hash TEXT NOT NULL, credibility_score REAL NOT NULL DEFAULT 0.7, "
            "fetched_at TEXT NOT NULL)"
        )


def is_url_allowed_by_robots(robots_txt: str, path: str, user_agent: str = "dadpbot") -> bool:
    """Evaluate robots.txt Disallow/Allow rules for a given path and user-agent."""
    target_path = path if path.startswith("/") else f"/{path}"
    active = False
    disallows: list[str] = []
    allows: list[str] = []
    ua_low = user_agent.lower()
    for raw_line in (robots_txt or "").splitlines():
        line = raw_line.split("#", 1)[0].strip()
        if not line or ":" not in line:
            continue
        key, val = (p.strip() for p in line.split(":", 1))
        klow = key.lower()
        if klow == "user-agent":
            active = val.lower() in ("*", ua_low)
        elif active and klow == "disallow" and val:
            disallows.append(val)
        elif active and klow == "allow" and val:
            allows.append(val)
    best_allow = max((len(a) for a in allows if target_path.startswith(a)), default=0)
    best_disallow = max((len(d) for d in disallows if target_path.startswith(d)), default=0)
    return best_allow >= best_disallow


def score_source_credibility(url: str, content: str) -> float:
    host = (urlparse(url).hostname or "").lower()
    score = 0.65
    if any(host.endswith(tld) for tld in _TRUSTED_TLDS):
        score += 0.2
    if url.startswith("https://"):
        score += 0.05
    if len(content.strip()) >= 200:
        score += 0.05
    return round(min(0.98, score), 2)


def archive_web_page(url: str, title: str, content: str) -> dict[str, Any]:
    """Validate URL safety, deduplicate by content hash, and store in local web_archive."""
    ok, reason = is_safe_public_url(url)
    if not ok:
        raise ValueError(f"Güvensiz URL engellendi (SSRF): {reason}")
    init_web_archive_db()
    clean_text = re.sub(r"\s+", " ", content).strip()
    if not clean_text:
        raise ValueError("Arşivlenecek içerik boş olamaz.")
    url_hash = hashlib.sha256(url.strip().encode("utf-8")).hexdigest()[:24]
    content_hash = hashlib.sha256(clean_text.encode("utf-8")).hexdigest()[:24]
    host = (urlparse(url).hostname or "").lower()
    cred = score_source_credibility(url, clean_text)
    now = datetime.now(UTC).isoformat()
    with _connect() as conn:
        dup = conn.execute("SELECT url_hash FROM web_archive WHERE content_hash = ?", (content_hash,)).fetchone()
        deduped = dup is not None and str(dup["url_hash"]) != url_hash
        conn.execute(
            "INSERT OR REPLACE INTO web_archive "
            "(url_hash, url, host, title, content, content_hash, credibility_score, fetched_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (url_hash, url.strip(), host, title.strip() or host, clean_text[:50000], content_hash, cred, now),
        )
    return {
        "ok": True,
        "url_hash": url_hash,
        "host": host,
        "credibility_score": cred,
        "deduplicated": deduped,
        "fetched_at": now,
    }


def count_archived_pages() -> int:
    """Return total number of locally archived web pages in SQLite."""
    init_web_archive_db()
    with _connect() as conn:
        row = conn.execute("SELECT COUNT(*) AS cnt FROM web_archive").fetchone()
    return int(row["cnt"]) if row else 0


async def fetch_and_index_source(url: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    """ARS-01: SSRF-safe source/PDF download or ingest -> archive in SQLite -> index into RAG store."""
    import base64

    import httpx

    from extract import extract_pdf_text
    from rag.store import EmbeddingUnavailableError, default_rag_store

    opts = payload or {}
    title = str(opts.get("title") or "")
    content_base64 = str(opts.get("content_base64") or "")
    content_text = str(opts.get("content_text") or "")
    is_pdf = bool(opts.get("is_pdf", False))
    collection_id = str(opts.get("collection_id") or "research_sources")

    ok, reason = is_safe_public_url(url)
    if not ok:
        raise ValueError(f"Güvensiz URL engellendi (SSRF): {reason}")
    extracted = content_text.strip()
    if content_base64.strip():
        raw = base64.b64decode(content_base64.strip())
        extracted = extract_pdf_text(raw) if (is_pdf or url.lower().endswith(".pdf")) else raw.decode("utf-8", errors="replace")
    elif not extracted:
        async with httpx.AsyncClient(timeout=12.0, follow_redirects=False) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            ctype = (resp.headers.get("content-type") or "").lower()
            extracted = extract_pdf_text(resp.content) if (is_pdf or "pdf" in ctype or url.lower().endswith(".pdf")) else re.sub(r"<[^>]+>", " ", resp.text)
    clean_text = re.sub(r"\s+", " ", extracted).strip()
    if not clean_text:
        raise ValueError("Kaynaktan metin çıkarılamadı.")
    arch = archive_web_page(url, title or url, clean_text)
    rag_status = "indexed"
    indexed_doc_id = str(arch["url_hash"])
    try:
        ing = await default_rag_store.ingest_document(collection_id=collection_id, raw_text=clean_text[:50000], title=title or url)
        indexed_doc_id = str(ing.get("doc_id") or indexed_doc_id)
    except EmbeddingUnavailableError:
        rag_status = "archived_fts_only"
    return {
        "ok": True,
        "url": url,
        "archive": arch,
        "indexed_doc_id": indexed_doc_id,
        "rag_status": rag_status,
        "chars_indexed": len(clean_text[:50000]),
    }


def search_web_archive(query: str, limit: int = 5) -> dict[str, Any]:
    """Search local archived pages with deterministic lexical relevance and [S1] citations."""
    init_web_archive_db()
    tokens = [t for t in re.findall(r"[a-zA-Z0-9çğıöşüÇĞİÖŞÜ]+", query.lower()) if len(t) >= 2]
    with _connect() as conn:
        rows = conn.execute(
            "SELECT url, host, title, content, credibility_score, fetched_at FROM web_archive ORDER BY fetched_at DESC LIMIT 500"
        ).fetchall()
    scored: list[tuple[float, dict[str, Any]]] = []
    for r in rows:
        hay = f"{r['title']} {r['content']}".lower()
        hits = sum(1 for t in tokens if t in hay)
        if not tokens or hits > 0:
            rel = (hits / max(1, len(tokens))) * 0.75 + float(r["credibility_score"]) * 0.25
            scored.append((round(rel, 3), dict(r)))
    scored.sort(key=lambda x: x[0], reverse=True)
    results = [
        {
            "citation": f"S{i + 1}",
            "score": sc,
            "url": item["url"],
            "title": item["title"],
            "snippet": item["content"][:280],
            "credibility_score": item["credibility_score"],
            "fetched_at": item["fetched_at"],
        }
        for i, (sc, item) in enumerate(scored[: max(1, min(limit, 20))])
    ]
    return {"ok": True, "offline_mode": True, "query": query, "count": len(results), "results": results}


class ArchivePageRequest(BaseModel):
    url: str = Field(..., min_length=8, max_length=1024)
    title: str = Field(default="", max_length=256)
    content: str = Field(..., min_length=5, max_length=64000)


class ArchiveSearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=500)
    limit: int = Field(default=5, ge=1, le=20)


class RobotsCheckRequest(BaseModel):
    robots_txt: str = Field(default="")
    path: str = Field(..., min_length=1, max_length=512)
    user_agent: str = Field(default="dadpbot", max_length=64)


@router.post("/archive")
async def api_archive_page(body: ArchivePageRequest):
    """Store and deduplicate a public web page in the local citation archive."""
    try:
        return archive_web_page(body.url, body.title, body.content)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/archive/search")
async def api_search_archive(body: ArchiveSearchRequest):
    """Search the local offline web archive and return cited [S1] results."""
    return search_web_archive(body.query, limit=body.limit)


@router.post("/robots-check")
async def api_robots_check(body: RobotsCheckRequest):
    """Evaluate robots.txt crawl permission for a path and user-agent."""
    allowed = is_url_allowed_by_robots(body.robots_txt, body.path, body.user_agent)
    return {"ok": True, "path": body.path, "user_agent": body.user_agent, "allowed": allowed}

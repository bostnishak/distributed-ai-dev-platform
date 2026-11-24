"""RAG-13: Externalized Sample Company Knowledge Base (zero hardcoded docs in code, explicit 'örnek' source tag)."""

from __future__ import annotations

import json
import math
import re
from typing import Any

import httpx

from rag.store import SAMPLE_KB_PATH, tr_lower


def _load_sample_docs() -> list[dict[str, Any]]:
    if not SAMPLE_KB_PATH.is_file():
        return []
    raw = json.loads(SAMPLE_KB_PATH.read_text(encoding="utf-8"))
    for doc in raw:
        doc.setdefault("source_label", "örnek")
        doc.setdefault("is_sample", True)
    return list(raw)


COMPANY_KNOWLEDGE_DOCS: list[dict[str, Any]] = _load_sample_docs()

_EMBED_CACHE: dict[str, list[float]] = {}


def _cosine(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b, strict=False))
    na = math.sqrt(sum(x * x for x in a)) or 1.0
    nb = math.sqrt(sum(y * y for y in b)) or 1.0
    return dot / (na * nb)


async def _embed_text(text: str) -> list[float] | None:
    import gateway

    try:
        emb = await gateway.default_client.embed(text, model="bge-m3:latest")
        if isinstance(emb, list) and emb:
            return emb
    except (httpx.HTTPError, OSError, RuntimeError, ValueError, TypeError, KeyError, ImportError) as _exc:
        import logging

        logging.getLogger(__name__).debug("Recoverable error suppressed: %s", _exc)
    return None


def search_company_kb_sync(query: str, top_k: int = 2) -> list[dict[str, Any]]:
    """Fast lexical/keyword retrieval over externalized sample knowledge docs."""
    lower = tr_lower(query)
    tokens = set(re.findall(r"[a-z0-9çğıöşü]+", lower))
    scored: list[tuple[float, dict[str, Any]]] = []
    for doc in COMPANY_KNOWLEDGE_DOCS:
        score = 0.0
        for kw in doc.get("keywords") or ():
            if tr_lower(str(kw)) in lower:
                score += 3.0
        doc_tokens = set(re.findall(r"[a-z0-9çğıöşü]+", tr_lower(doc["title"] + " " + doc["content"])))
        score += len(tokens & doc_tokens) * 0.4
        if score >= 1.5:
            scored.append((score, doc))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [d for _, d in scored[:top_k]]


async def retrieve_company_context(query: str, top_k: int = 2) -> str:
    """Retrieve externalized sample engineering context tagged explicitly as 'örnek'."""
    lexical = search_company_kb_sync(query, top_k=top_k)
    if not lexical:
        return ""
    q_emb = await _embed_text(query)
    if q_emb:
        reranked: list[tuple[float, dict[str, Any]]] = []
        for doc in COMPANY_KNOWLEDGE_DOCS:
            if doc["id"] not in _EMBED_CACHE:
                d_emb = await _embed_text(doc["title"] + ": " + doc["content"])
                if d_emb:
                    _EMBED_CACHE[doc["id"]] = d_emb
            sim = _cosine(q_emb, _EMBED_CACHE.get(doc["id"], []))
            if sim > 0.35:
                reranked.append((sim, doc))
        if reranked:
            reranked.sort(key=lambda x: x[0], reverse=True)
            lexical = [d for _, d in reranked[:top_k]]

    parts = [f"- [{d['title']} (kaynak: {d.get('source_label', 'örnek')})]: {d['content']}" for d in lexical]
    return "\n".join(parts)

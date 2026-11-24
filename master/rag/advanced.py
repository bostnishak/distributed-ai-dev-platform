"""EPK-14: Advanced RAG Parent-Child Chunking, Query Rewrite, Cross-Reranking & nDCG@k Evaluation."""

from __future__ import annotations

import math
import re
from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/rag/advanced", tags=["rag-advanced"])

_TR_FOLD = str.maketrans("çğıöşüÇĞİÖŞÜ", "cgiosuCGIOSU")
_SYNONYMS: dict[str, tuple[str, ...]] = {
    "hata": ("error", "bug", "istisna"),
    "yetki": ("rbac", "izin", "rol"),
    "güvenlik": ("security", "şifreleme", "koruma"),
    "hafıza": ("memory", "bellek", "bağlam"),
    "arama": ("search", "sorgu", "indeks"),
}


def build_parent_child_chunks(
    text: str, *, parent_size: int = 800, child_size: int = 220, overlap: int = 40
) -> dict[str, Any]:
    """Split text into hierarchical parent passages linked to smaller overlapping child retrieval chunks."""
    clean = (text or "").strip()
    if not clean:
        return {"parents": [], "children": []}
    p_step = max(100, parent_size)
    c_step = max(40, min(child_size, p_step))
    c_ov = max(0, min(overlap, c_step // 2))
    parents: list[dict[str, Any]] = []
    children: list[dict[str, Any]] = []
    p_idx = 0
    for p_start in range(0, len(clean), p_step):
        p_text = clean[p_start : p_start + p_step]
        pid = f"P{p_idx}"
        parents.append({"parent_id": pid, "offset": p_start, "length": len(p_text), "content": p_text})
        c_pos = 0
        c_idx = 0
        while c_pos < len(p_text):
            c_text = p_text[c_pos : c_pos + c_step]
            children.append({
                "child_id": f"{pid}-C{c_idx}",
                "parent_id": pid,
                "offset": p_start + c_pos,
                "content": c_text,
            })
            if c_pos + c_step >= len(p_text):
                break
            c_pos += c_step - c_ov
            c_idx += 1
        p_idx += 1
    return {"parents": parents, "children": children}


def rewrite_query_variants(query: str) -> list[str]:
    """Generate folded + bilingual synonym query variants to improve Turkish/English RAG recall."""
    base = " ".join((query or "").strip().split())
    if not base:
        return []
    variants = [base]
    folded = base.translate(_TR_FOLD)
    if folded.lower() != base.lower():
        variants.append(folded)
    low = base.lower()
    expansions = [syn for key, syns in _SYNONYMS.items() if key in low for syn in syns]
    if expansions:
        variants.append(f"{base} {' '.join(expansions[:4])}")
    return variants


def _tokenize(text: str) -> list[str]:
    return [t for t in re.findall(r"[a-zA-Z0-9]+", (text or "").translate(_TR_FOLD).lower()) if len(t) >= 2]


def rerank_passages(query: str, passages: list[dict[str, Any]], top_k: int = 5) -> list[dict[str, Any]]:
    """Cross-rerank candidate passages using lexical coverage, exact phrase match, and density."""
    variants = rewrite_query_variants(query)
    q_tokens = set(_tokenize(" ".join(variants)))
    q_phrase = (query or "").translate(_TR_FOLD).lower().strip()
    scored: list[dict[str, Any]] = []
    for i, p in enumerate(passages):
        text = str(p.get("content") or p.get("text") or "")
        p_toks = _tokenize(text)
        p_set = set(p_toks)
        cov = len(q_tokens & p_set) / max(1, len(q_tokens))
        tf_boost = sum(p_toks.count(t) for t in q_tokens) / max(10, len(p_toks))
        phrase_bonus = 0.25 if (q_phrase and q_phrase in text.translate(_TR_FOLD).lower()) else 0.0
        prior = float(p.get("score", 0.0)) * 0.15
        final_score = round(min(1.0, cov * 0.65 + min(0.2, tf_boost) + phrase_bonus + prior), 4)
        scored.append({**p, "id": p.get("id", f"doc-{i}"), "rerank_score": final_score})
    scored.sort(key=lambda x: x["rerank_score"], reverse=True)
    return scored[: max(1, min(top_k, 50))]


def compute_ndcg_at_k(relevances: list[float], k: int = 5) -> float:
    """Compute Normalized Discounted Cumulative Gain (nDCG@k) for retrieval quality evaluation."""
    rels = relevances[:k]
    if not rels:
        return 0.0
    dcg = sum((2.0**r - 1.0) / math.log2(i + 2) for i, r in enumerate(rels))
    ideal = sorted(relevances, reverse=True)[:k]
    idcg = sum((2.0**r - 1.0) / math.log2(i + 2) for i, r in enumerate(ideal))
    return round(dcg / idcg, 4) if idcg > 0 else 0.0


class ParentChildRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=120000)
    parent_size: int = Field(default=800, ge=100, le=8000)
    child_size: int = Field(default=220, ge=40, le=2000)


class RerankRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=500)
    passages: list[dict[str, Any]] = Field(default_factory=list)
    top_k: int = Field(default=5, ge=1, le=50)


@router.post("/parent-child")
async def api_parent_child_chunk(body: ParentChildRequest):
    """Chunk text into parent passages and linked child chunks."""
    res = build_parent_child_chunks(body.text, parent_size=body.parent_size, child_size=body.child_size)
    return {"ok": True, "parent_count": len(res["parents"]), "child_count": len(res["children"]), **res}


@router.post("/rerank")
async def api_rerank_passages(body: RerankRequest):
    """Expand query variants and cross-rerank candidate RAG passages."""
    variants = rewrite_query_variants(body.query)
    ranked = rerank_passages(body.query, body.passages, top_k=body.top_k)
    return {"ok": True, "query_variants": variants, "results": ranked}

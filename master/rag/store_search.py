"""RAG-06..09: Hybrid FTS5 BM25 + NumPy ANN scoring helpers extracted from `rag/store.py`."""

from __future__ import annotations

import sqlite3
from typing import Any

import numpy as np


def fetch_bm25_and_chunks(
    conn: sqlite3.Connection,
    target_cols: list[str],
    fts_terms: list[str],
    q_dim: int,
) -> tuple[dict[str, float], list[Any]]:
    """Fetch FTS5 BM25 scores and candidate chunk rows matching target collections and vector dimension."""
    import sql_safe

    placeholders = sql_safe.placeholders_for(len(target_cols))
    bm25_scores: dict[str, float] = {}
    if fts_terms:
        fts_query = " OR ".join(f'"{t}"' for t in fts_terms)
        try:
            fts_sql = sql_safe.build_select(
                "rag_chunks_fts",
                "chunk_id, bm25(rag_chunks_fts) AS rank",
                where=f"rag_chunks_fts MATCH ? AND collection_id IN ({placeholders})",
                order_by="rank",
                limit=30,
            )
            for r in conn.execute(fts_sql, (fts_query, *target_cols)).fetchall():
                bm25_scores[r["chunk_id"]] = min(1.0, max(0.0, -float(r["rank"]) / 8.0))
        except sqlite3.OperationalError:
            bm25_scores = {}

    join_sql = (
        "SELECT c.*, d.title AS doc_title, d.is_sample AS doc_is_sample "
        "FROM rag_chunks c JOIN rag_documents d ON c.doc_id = d.doc_id "
        "WHERE c.collection_id IN (" + placeholders + ") AND c.embedding_dim = ?"
    )
    chunk_rows = conn.execute(join_sql, (*target_cols, q_dim)).fetchall()
    return bm25_scores, chunk_rows


def rank_hybrid_candidates(
    chunk_rows: list[Any],
    q_vec: np.ndarray,
    bm25_scores: dict[str, float],
    fts_terms: list[str],
    cfg: dict[str, Any],
) -> list[dict[str, Any]]:
    """Compute vectorized cosine similarity, RRF rank fusion, and threshold-filtered candidate dicts."""
    mat = np.vstack([np.frombuffer(r["embedding_blob"], dtype=np.float32) for r in chunk_rows])
    cos_scores = mat @ q_vec
    bm25_rank = {cid: i + 1 for i, (cid, _) in enumerate(sorted(bm25_scores.items(), key=lambda x: x[1], reverse=True))}
    vec_rank = {chunk_rows[int(idx)]["chunk_id"]: i + 1 for i, idx in enumerate(np.argsort(-cos_scores)[:30])}

    q_set = set(fts_terms)
    min_thresh = float(cfg.get("min_combined_threshold", 0.22))
    rerank = bool(cfg.get("rerank", True))
    out: list[dict[str, Any]] = []
    for idx, row in enumerate(chunk_rows):
        cid = row["chunk_id"]
        if cid not in bm25_rank and cid not in vec_rank:
            continue
        b_sc = bm25_scores.get(cid, 0.0)
        c_sc = float(cos_scores[idx])
        rrf = (1.0 / (60 + bm25_rank.get(cid, 1000))) + (1.0 / (60 + vec_rank.get(cid, 1000)))
        overlap = len(q_set & set(str(row["norm_content"]).split())) / max(1, len(q_set))
        combined = 0.45 * max(0.0, c_sc) + 0.35 * b_sc + 0.20 * overlap + (0.05 * rrf if rerank else 0.0)
        if combined < min_thresh:
            continue
        out.append({
            "chunk_id": cid, "doc_id": row["doc_id"], "doc_title": row["doc_title"],
            "collection_id": row["collection_id"], "page": int(row["page"]),
            "section": str(row["section"]), "content": str(row["content"]),
            "bm25_score": round(b_sc, 4), "cosine_score": round(c_sc, 4),
            "combined_score": round(combined, 4), "is_ocr": bool(row["is_ocr"]),
            "is_sample": bool(row["doc_is_sample"]), "quarantine": bool(row["quarantine"]),
        })
    return out

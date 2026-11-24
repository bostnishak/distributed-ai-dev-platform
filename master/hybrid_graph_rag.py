"""Cluster C ([M39]..[M42]): Hybrid Vector + BM25 Reciprocal Rank Fusion (RRF),
2-Hop Technical Knowledge Graph (GraphRAG), Vision-RAG Perceptual Drawing Similarity,
and Mandatory Numerical Citation Guardrail.

100% local, zero cloud dependencies, zero emojis. Persists data in
``config.DATA_DIR / "graph_rag.db"``.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx

import config
import dbconn
import vector_meta
from hybrid_graph_rag_ops import (
    FALLBACK_EMBED_DIM,
    IMAGE_FINGERPRINT_DIM,
    _extract_numbers,
    _pack_vector,
    _relation_for_pair,
    _tokenize,
    _unpack_vector,
    compute_image_fingerprint,
    cosine_similarity,
    deterministic_ngram_embedding,
    extract_entities_and_triples,
    fuse_hybrid_search,
    traverse_knowledge_subgraph,
    verify_citations,
)
from prompt_loader import load_prompt

__all__ = [
    "FALLBACK_EMBED_DIM",
    "IMAGE_FINGERPRINT_DIM",
    "HybridGraphRAG",
    "_extract_numbers",
    "_pack_vector",
    "_relation_for_pair",
    "_tokenize",
    "_unpack_vector",
    "compute_image_fingerprint",
    "cosine_similarity",
    "deterministic_ngram_embedding",
    "extract_and_store_triples",
    "find_similar_drawings",
    "query_knowledge_subgraph",
    "verify_citations",
]


def _data_dir() -> Path:
    base = Path(getattr(config, "DATA_DIR", Path(config.DB_PATH).parent))
    base.mkdir(parents=True, exist_ok=True)
    return base


class HybridGraphRAG:
    """SQLite-backed Hybrid Vector + BM25 Reciprocal Rank Fusion, 2-hop Knowledge Graph,
    Vision-RAG Drawing Similarity Index, and Citation Guardrail.
    """

    def __init__(self, db_path: Path | None = None, use_ollama_embeddings: bool = False) -> None:
        self._explicit_db_path = db_path
        self.use_ollama_embeddings = use_ollama_embeddings
        self._init_db()

    @property
    def db_path(self) -> Path:
        if self._explicit_db_path is not None:
            self._explicit_db_path.parent.mkdir(parents=True, exist_ok=True)
            return self._explicit_db_path
        return dbconn.database_file("graph_rag.db")

    def _connect(self) -> sqlite3.Connection:
        return dbconn.open_db(self.db_path)

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.executescript(load_prompt("b3_hybrid_graph_rag_schema.txt"))
        with self._connect() as conn:
            vector_meta.ensure_columns(conn)

    def _embed(self, text: str) -> list[float]:
        if self.use_ollama_embeddings:
            import gateway

            try:
                prov = gateway.OllamaProvider(base_url=getattr(config, "OLLAMA_URL", "http://127.0.0.1:11434"))
                emb = prov.embed_sync("bge-m3:latest", text, timeout_s=1.2)
                if len(emb) >= 64:
                    return emb
            except (httpx.HTTPError, OSError, RuntimeError, ValueError, TypeError, KeyError, ImportError) as _exc:
                import logging

                logging.getLogger(__name__).debug("Recoverable error suppressed: %s", _exc)
        return deterministic_ngram_embedding(text, dim=FALLBACK_EMBED_DIM)

    def add_document(
        self,
        doc_id: str,
        title: str,
        content: str,
        metadata: dict[str, Any] | None = None,
        extract_graph: bool = True,
    ) -> dict[str, Any]:
        """Index a document for BM25 + Vector RRF search and optionally extract KG triples."""
        clean_id = (doc_id or "").strip()
        if not clean_id:
            raise ValueError("doc_id must not be empty")
        full_text = f"{title.strip()}\n{content.strip()}"
        tokens = _tokenize(full_text)
        emb = self._embed(full_text)
        now = datetime.now(UTC).isoformat()

        with self._connect() as conn:
            conn.execute(
                load_prompt("b3_hybrid_graph_rag_upsert_doc.txt"),
                (
                    clean_id,
                    title.strip(),
                    content.strip(),
                    json.dumps(metadata or {}, ensure_ascii=False),
                    len(tokens),
                    _pack_vector(emb),
                    now,
                ),
            )

        triples: list[dict[str, str]] = []
        if extract_graph:
            triples = self.extract_and_store_triples(clean_id, full_text)

        return {
            "doc_id": clean_id,
            "title": title.strip(),
            "token_count": len(tokens),
            "embedding_dim": len(emb),
            "triples_extracted": len(triples),
        }

    def search(self, query: str, top_k: int = 5, rrf_k: int = 60) -> list[dict[str, Any]]:
        """Execute Hybrid BM25 + Vector Cosine search combined with Reciprocal Rank Fusion (RRF)."""
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT doc_id, title, content, metadata_json, token_count, embedding_blob FROM rag_documents"
            ).fetchall()
        if not rows:
            return []
        q_emb = self._embed(query)
        return fuse_hybrid_search(rows, query, q_emb, top_k=top_k, rrf_k=rrf_k)

    def extract_and_store_triples(self, doc_id: str, text: str) -> list[dict[str, str]]:
        """Extract technical engineering entities and relationship edges from document text."""
        clean_doc_id = (doc_id or "default").strip()
        all_entities, extracted_triples = extract_entities_and_triples(clean_doc_id, text)

        with self._connect() as conn:
            for norm_key, (raw_val, ent_type) in all_entities.items():
                entity_id = f"{clean_doc_id}::{norm_key}"
                conn.execute(
                    "INSERT OR REPLACE INTO kg_entities (entity_id, name, entity_type, doc_id) VALUES (?, ?, ?, ?)",
                    (entity_id, raw_val, ent_type, clean_doc_id),
                )
            for tr in extracted_triples:
                conn.execute(
                    "INSERT OR IGNORE INTO kg_edges "
                    "(source_name, source_type, relation, target_name, target_type, doc_id, evidence) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (
                        tr["source"],
                        tr["source_type"],
                        tr["relation"],
                        tr["target"],
                        tr["target_type"],
                        tr["doc_id"],
                        tr["evidence"],
                    ),
                )

        return extracted_triples

    def query_knowledge_subgraph(self, query: str, hops: int = 2) -> list[dict[str, Any]]:
        """Perform up to ``hops`` breadth-first traversal over extracted technical knowledge triples."""
        max_hops = max(1, hops)
        with self._connect() as conn:
            edges = conn.execute(
                "SELECT source_name, source_type, relation, target_name, target_type, doc_id, evidence FROM kg_edges"
            ).fetchall()
        if not edges:
            return []
        return traverse_knowledge_subgraph(edges, query, max_hops)

    def index_drawing(
        self,
        drawing_id: str,
        title: str,
        raw_bytes: bytes,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Compute 64-dim perceptual/edge fingerprint and store in ``vision_drawings``."""
        clean_id = (drawing_id or "").strip()
        if not clean_id:
            raise ValueError("drawing_id must not be empty")
        fp = compute_image_fingerprint(raw_bytes)
        now = datetime.now(UTC).isoformat()
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO vision_drawings (drawing_id, title, metadata_json, fingerprint_blob, created_at) "
                "VALUES (?, ?, ?, ?, ?) "
                "ON CONFLICT(drawing_id) DO UPDATE SET "
                "title = excluded.title, metadata_json = excluded.metadata_json, "
                "fingerprint_blob = excluded.fingerprint_blob, created_at = excluded.created_at",
                (
                    clean_id,
                    title.strip(),
                    json.dumps(metadata or {}, ensure_ascii=False),
                    _pack_vector(fp),
                    now,
                ),
            )
        return {"drawing_id": clean_id, "title": title.strip(), "fingerprint_dim": len(fp)}

    def find_similar_drawings(self, raw_bytes: bytes, top_k: int = 3) -> list[dict[str, Any]]:
        """Rank indexed technical drawings by cosine similarity to the query image fingerprint."""
        query_fp = compute_image_fingerprint(raw_bytes)
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT drawing_id, title, metadata_json, fingerprint_blob FROM vision_drawings"
            ).fetchall()

        results: list[dict[str, Any]] = []
        for r in rows:
            stored_fp = _unpack_vector(r["fingerprint_blob"])
            sim = cosine_similarity(query_fp, stored_fp)
            results.append({
                "drawing_id": r["drawing_id"],
                "title": r["title"],
                "metadata": json.loads(r["metadata_json"] or "{}"),
                "similarity": round(sim, 6),
            })

        results.sort(key=lambda item: item["similarity"], reverse=True)
        return results[: max(1, top_k)]


_DEFAULT_RAG_STATE: dict[str, HybridGraphRAG | None] = {"instance": None}


def _get_default_rag() -> HybridGraphRAG:
    target_db = dbconn.database_file("graph_rag.db")
    current = _DEFAULT_RAG_STATE["instance"]
    if current is None or current.db_path != target_db:
        current = HybridGraphRAG(db_path=target_db)
        _DEFAULT_RAG_STATE["instance"] = current
    return current


def extract_and_store_triples(doc_id: str, text: str) -> list[dict[str, str]]:
    """Module-level convenience wrapper for extracting and persisting KG triples."""
    return _get_default_rag().extract_and_store_triples(doc_id=doc_id, text=text)


def query_knowledge_subgraph(query: str, hops: int = 2) -> list[dict[str, Any]]:
    """Module-level convenience wrapper for 2-hop BFS Knowledge Graph retrieval."""
    return _get_default_rag().query_knowledge_subgraph(query=query, hops=hops)


def find_similar_drawings(raw_bytes: bytes, top_k: int = 3) -> list[dict[str, Any]]:
    """Module-level convenience wrapper for Vision-RAG drawing similarity search."""
    return _get_default_rag().find_similar_drawings(raw_bytes=raw_bytes, top_k=top_k)

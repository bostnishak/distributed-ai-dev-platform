"""Cluster C ([M39]..[M42]): Hybrid Vector + BM25 Reciprocal Rank Fusion (RRF),
2-Hop Technical Knowledge Graph (GraphRAG), Vision-RAG Perceptual Drawing Similarity,
and Mandatory Numerical Citation Guardrail.

100% local, zero cloud dependencies, zero emojis. Persists data in
``config.DATA_DIR / "graph_rag.db"``.
"""

from __future__ import annotations

import hashlib
import io
import json
import math
import re
import sqlite3
import struct
from collections import deque
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image

import config
import dbconn
import vector_meta

FALLBACK_EMBED_DIM = 256
IMAGE_FINGERPRINT_DIM = 64


def _data_dir() -> Path:
    base = Path(getattr(config, "DATA_DIR", Path(config.DB_PATH).parent))
    base.mkdir(parents=True, exist_ok=True)
    return base


def _tokenize(text: str) -> list[str]:
    return re.findall(r"[a-z0-9çğıöşü]+(?:[.\-/][a-z0-9çğıöşü]+)*", (text or "").lower())


def deterministic_ngram_embedding(text: str, dim: int = FALLBACK_EMBED_DIM) -> list[float]:
    """Compute a fast (<1ms) deterministic L2-normalized character/word n-gram embedding vector."""
    vec = [0.0] * dim
    norm_text = (text or "").lower().strip()
    if not norm_text:
        return vec

    tokens = _tokenize(norm_text)
    features: list[tuple[str, float]] = []
    for tok in tokens:
        features.append((f"w:{tok}", 2.0))
        padded = f"<{tok}>"
        for n in (3, 4):
            for i in range(max(0, len(padded) - n + 1)):
                features.append((f"c{n}:{padded[i : i + n]}", 1.0))

    for idx in range(len(tokens) - 1):
        features.append((f"b:{tokens[idx]}_{tokens[idx + 1]}", 1.5))

    for feat, weight in features:
        digest = hashlib.blake2b(feat.encode("utf-8"), digest_size=8).digest()
        h_val = int.from_bytes(digest, "little")
        bucket = h_val % dim
        sign = 1.0 if ((h_val >> 63) & 1) == 0 else -1.0
        vec[bucket] += sign * weight

    norm = math.sqrt(sum(v * v for v in vec))
    if norm > 1e-12:
        vec = [round(v / norm, 6) for v in vec]
    return vec


def _pack_vector(vec: list[float]) -> bytes:
    return struct.pack(f"<{len(vec)}f", *vec)


def _unpack_vector(blob: bytes) -> list[float]:
    if not blob:
        return []
    count = len(blob) // 4
    return list(struct.unpack(f"<{count}f", blob[: count * 4]))


def cosine_similarity(a: list[float], b: list[float]) -> float:
    if not a or not b:
        return 0.0
    if len(a) != len(b):
        # Project or align onto FALLBACK_EMBED_DIM if one vector came from external dim
        min_len = min(len(a), len(b))
        a = a[:min_len]
        b = b[:min_len]
    dot = sum(x * y for x, y in zip(a, b, strict=False))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na <= 1e-12 or nb <= 1e-12:
        return 0.0
    return float(dot / (na * nb))


# Domain entity patterns for technical engineering / software knowledge extraction
_ENTITY_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    (
        "Material",
        re.compile(
            r"\b(?:AISI\s*\d{3,4}[A-Z]*|SAE\s*\d{4}|Al(?:üminyum|uminum)?\s*\d{4}(?:-T\d+)?|"
            r"Ti-6Al-4V|Inconel\s*\d{3}|CK45|C45|42CrMo4|St\s*\d{2}(?:-\d)?|1\.\d{4})\b",
            re.IGNORECASE,
        ),
    ),
    (
        "Standard",
        re.compile(
            r"\b(?:ISO\s*\d{3,5}(?:-[a-zA-Z0-9]+)?|AS\s*910[02]|DIN\s*\d{3,5}|"
            r"ASME\s*Y14\.\d+|ASTM\s*[A-Z]\d+|KVKK|GDPR)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "Tolerance",
        re.compile(
            r"(?:±\s*\d+(?:\.\d+)?\s*mm|\b[HhGgKkFfMmJj]\d{1,2}\b|"
            r"\bRa\s*\d+(?:\.\d+)?|\bCp[k]?\s*(?:>=|≥|=)\s*\d+(?:\.\d+)?|\b6[HGhg]\b)",
        ),
    ),
    (
        "Tool",
        re.compile(
            r"\b(?:TiAlN|karbür\s+rayba|karbür\s+uç|HSS-E|parmak\s+freze|mikrometrik\s+bara|"
            r"CMM|tampon\s+mastar|kılavuz)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "Operation",
        re.compile(
            r"\b(?:OP\d{2}|tornalama|frezeleme|delik\s+delme|raybalama|kılavuz\s+çekme|"
            r"taşlama|balonlama|FAI)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "Module",
        re.compile(
            r"\b(?:FastAPI|SQLite|PyMuPDF|Thompson\s+Sampling|GraphRAG|Vision-RAG|QLoRA|DPO|"
            r"Fanuc|Siemens\s+Sinumerik|Heidenhain)\b",
            re.IGNORECASE,
        ),
    ),
]


def _relation_for_pair(src_type: str, dst_type: str) -> str:
    pair = (src_type, dst_type)
    mapping = {
        ("Material", "Tolerance"): "REQUIRES_TOLERANCE",
        ("Tolerance", "Material"): "APPLIES_TO_MATERIAL",
        ("Material", "Tool"): "MACHINED_WITH_TOOL",
        ("Tool", "Material"): "CUTS_MATERIAL",
        ("Material", "Operation"): "PROCESSED_BY_OPERATION",
        ("Operation", "Tool"): "USES_TOOL",
        ("Tool", "Operation"): "SUPPORTS_OPERATION",
        ("Operation", "Tolerance"): "ACHIEVES_TOLERANCE",
        ("Tolerance", "Tool"): "VERIFIED_OR_CUT_BY",
        ("Standard", "Tolerance"): "DEFINES_TOLERANCE",
        ("Tolerance", "Standard"): "GOVERNED_BY_STANDARD",
        ("Standard", "Operation"): "GOVERNS_OPERATION",
        ("Material", "Standard"): "COMPLIES_WITH_STANDARD",
    }
    return mapping.get(pair, "RELATED_TO")


def compute_image_fingerprint(raw_bytes: bytes) -> list[float]:
    """Compute a L2-normalized 64-dimensional perceptual + edge-orientation fingerprint.

    Dimensions 0..31: 8x4 grayscale perceptual average-hash deviation block vector.
    Dimensions 32..47: 16-bin Sobel-like gradient magnitude & orientation histogram.
    Dimensions 48..63: 4x4 spatial edge-density grid for technical drawing layout matching.
    """
    if not raw_bytes:
        raise ValueError("raw_bytes cannot be empty")
    try:
        with Image.open(io.BytesIO(raw_bytes)) as img:
            gray = img.convert("L").resize((64, 64), Image.Resampling.BILINEAR)
            arr = np.asarray(gray, dtype=np.float32) / 255.0
    except Exception:
        # Deterministic byte-distribution fallback if caller passes raw synthetic bytes
        digest = hashlib.sha512(raw_bytes).digest()
        fallback = [((b / 127.5) - 1.0) for b in digest[:IMAGE_FINGERPRINT_DIM]]
        norm = math.sqrt(sum(v * v for v in fallback)) or 1.0
        return [round(v / norm, 6) for v in fallback]

    # 1) 8x4 perceptual luminance blocks (32 dims)
    blocks_8x4 = arr.reshape(4, 16, 8, 8).mean(axis=(1, 3)).flatten()
    mean_lum = float(blocks_8x4.mean())
    ahash_vec = (blocks_8x4 - mean_lum).tolist()

    # 2) Gradient orientation + intensity histogram (16 dims)
    gx = arr[:, 2:] - arr[:, :-2]
    gy = arr[2:, :] - arr[:-2, :]
    gx_c = gx[1:-1, :]
    gy_c = gy[:, 1:-1]
    mag = np.hypot(gx_c, gy_c)
    ang = (np.arctan2(gy_c, gx_c) + np.pi) % (2.0 * np.pi)
    bins = np.linspace(0.0, 2.0 * np.pi, 17)
    hist, _ = np.histogram(ang, bins=bins, weights=mag)
    hist_vec = hist.astype(np.float32).tolist()

    # 3) 4x4 spatial edge density grid (16 dims)
    pad_mag = np.zeros((64, 64), dtype=np.float32)
    pad_mag[1:-1, 1:-1] = mag
    spatial_grid = pad_mag.reshape(4, 16, 4, 16).mean(axis=(1, 3)).flatten().tolist()

    combined = ahash_vec + hist_vec + spatial_grid
    assert len(combined) == IMAGE_FINGERPRINT_DIM
    norm = math.sqrt(sum(x * x for x in combined))
    if norm <= 1e-12:
        return [0.0] * IMAGE_FINGERPRINT_DIM
    return [round(float(x) / norm, 6) for x in combined]


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
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS rag_documents (
                    doc_id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    content TEXT NOT NULL,
                    metadata_json TEXT NOT NULL DEFAULT '{}',
                    token_count INTEGER NOT NULL DEFAULT 0,
                    embedding_blob BLOB NOT NULL,
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS kg_entities (
                    entity_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    entity_type TEXT NOT NULL,
                    doc_id TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS kg_edges (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source_name TEXT NOT NULL,
                    source_type TEXT NOT NULL,
                    relation TEXT NOT NULL,
                    target_name TEXT NOT NULL,
                    target_type TEXT NOT NULL,
                    doc_id TEXT NOT NULL,
                    evidence TEXT NOT NULL,
                    UNIQUE(source_name, relation, target_name, doc_id)
                );

                CREATE TABLE IF NOT EXISTS vision_drawings (
                    drawing_id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    metadata_json TEXT NOT NULL DEFAULT '{}',
                    fingerprint_blob BLOB NOT NULL,
                    created_at TEXT NOT NULL
                );
                """
            )
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
            except Exception as _exc:
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
                """
                INSERT INTO rag_documents (doc_id, title, content, metadata_json, token_count, embedding_blob, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(doc_id) DO UPDATE SET
                    title = excluded.title,
                    content = excluded.content,
                    metadata_json = excluded.metadata_json,
                    token_count = excluded.token_count,
                    embedding_blob = excluded.embedding_blob,
                    created_at = excluded.created_at
                """,
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

        q_tokens = _tokenize(query)
        q_emb = self._embed(query)

        # Compute BM25 parameters across corpus
        n_docs = len(rows)
        avgdl = max(1.0, sum(int(r["token_count"]) for r in rows) / n_docs)
        k1 = 1.5
        b = 0.75

        doc_token_Maps: list[dict[str, int]] = []
        df_counts: dict[str, int] = {t: 0 for t in set(q_tokens)}

        for r in rows:
            toks = _tokenize(f"{r['title']} {r['content']}")
            tf_map: dict[str, int] = {}
            for t in toks:
                tf_map[t] = tf_map.get(t, 0) + 1
            doc_token_Maps.append(tf_map)
            for qt in df_counts:
                if qt in tf_map:
                    df_counts[qt] += 1

        bm25_scores: list[tuple[int, float]] = []
        vec_scores: list[tuple[int, float]] = []

        for idx, r in enumerate(rows):
            tf_map = doc_token_Maps[idx]
            dl = max(1, int(r["token_count"]))
            bm25 = 0.0
            for qt in q_tokens:
                tf = tf_map.get(qt, 0)
                if tf == 0:
                    continue
                df = df_counts.get(qt, 0)
                idf = math.log(1.0 + (n_docs - df + 0.5) / (df + 0.5))
                denom = tf + k1 * (1.0 - b + b * (dl / avgdl))
                bm25 += idf * ((tf * (k1 + 1.0)) / denom)
            bm25_scores.append((idx, bm25))

            doc_vec = _unpack_vector(r["embedding_blob"])
            if len(doc_vec) != len(q_emb):
                doc_vec = deterministic_ngram_embedding(f"{r['title']} {r['content']}", dim=len(q_emb))
            sim = cosine_similarity(q_emb, doc_vec)
            vec_scores.append((idx, sim))

        # Rank 1..N for lexical and vector
        bm25_sorted = sorted(bm25_scores, key=lambda x: x[1], reverse=True)
        vec_sorted = sorted(vec_scores, key=lambda x: x[1], reverse=True)

        lex_rank = {doc_idx: rank for rank, (doc_idx, _) in enumerate(bm25_sorted, start=1)}
        vec_rank = {doc_idx: rank for rank, (doc_idx, _) in enumerate(vec_sorted, start=1)}
        bm25_val = dict(bm25_scores)
        vec_val = dict(vec_scores)

        fused: list[dict[str, Any]] = []
        for idx, r in enumerate(rows):
            r_lex = lex_rank[idx]
            r_vec = vec_rank[idx]
            rrf_score = (1.0 / (rrf_k + r_lex)) + (1.0 / (rrf_k + r_vec))
            fused.append(
                {
                    "doc_id": r["doc_id"],
                    "title": r["title"],
                    "content": r["content"],
                    "metadata": json.loads(r["metadata_json"] or "{}"),
                    "rrf_score": round(rrf_score, 6),
                    "lexical_rank": r_lex,
                    "vector_rank": r_vec,
                    "bm25_score": round(bm25_val[idx], 5),
                    "vector_score": round(vec_val[idx], 5),
                }
            )

        fused.sort(
            key=lambda item: (item["rrf_score"], item["bm25_score"], item["vector_score"]),
            reverse=True,
        )
        return fused[: max(1, int(top_k))]

    def extract_and_store_triples(self, doc_id: str, text: str) -> list[dict[str, str]]:
        """Extract technical engineering entities and relationship edges from document text."""
        clean_doc_id = (doc_id or "default").strip()
        sentences = [s.strip() for s in re.split(r"[\n.;]+", text or "") if s.strip()]
        extracted_triples: list[dict[str, str]] = []
        all_entities: dict[str, tuple[str, str]] = {}

        for sent in sentences:
            sent_entities: list[tuple[str, str]] = []
            seen_in_sent: set[str] = set()
            for ent_type, pattern in _ENTITY_PATTERNS:
                for match in pattern.finditer(sent):
                    raw_val = re.sub(r"\s+", " ", match.group(0).strip())
                    norm_key = raw_val.lower()
                    if norm_key not in seen_in_sent:
                        seen_in_sent.add(norm_key)
                        sent_entities.append((raw_val, ent_type))
                        all_entities[norm_key] = (raw_val, ent_type)

            # Build pairwise directed relations within the sentence clause
            for i in range(len(sent_entities)):
                for j in range(i + 1, len(sent_entities)):
                    src_name, src_type = sent_entities[i]
                    dst_name, dst_type = sent_entities[j]
                    rel = _relation_for_pair(src_type, dst_type)
                    extracted_triples.append(
                        {
                            "source": src_name,
                            "source_type": src_type,
                            "relation": rel,
                            "target": dst_name,
                            "target_type": dst_type,
                            "doc_id": clean_doc_id,
                            "evidence": sent[:240],
                        }
                    )

        # If entities exist across sentences in the same doc, connect sequential sentence anchors
        ent_list = list(all_entities.values())
        if not extracted_triples and len(ent_list) >= 2:
            for i in range(len(ent_list) - 1):
                src_name, src_type = ent_list[i]
                dst_name, dst_type = ent_list[i + 1]
                extracted_triples.append(
                    {
                        "source": src_name,
                        "source_type": src_type,
                        "relation": _relation_for_pair(src_type, dst_type),
                        "target": dst_name,
                        "target_type": dst_type,
                        "doc_id": clean_doc_id,
                        "evidence": (text or "")[:240],
                    }
                )

        with self._connect() as conn:
            for norm_key, (raw_val, ent_type) in all_entities.items():
                entity_id = f"{clean_doc_id}::{norm_key}"
                conn.execute(
                    """
                    INSERT OR REPLACE INTO kg_entities (entity_id, name, entity_type, doc_id)
                    VALUES (?, ?, ?, ?)
                    """,
                    (entity_id, raw_val, ent_type, clean_doc_id),
                )
            for tr in extracted_triples:
                conn.execute(
                    """
                    INSERT OR IGNORE INTO kg_edges
                    (source_name, source_type, relation, target_name, target_type, doc_id, evidence)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
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
        max_hops = max(1, int(hops))
        with self._connect() as conn:
            edges = conn.execute(
                """
                SELECT source_name, source_type, relation, target_name, target_type, doc_id, evidence
                FROM kg_edges
                """
            ).fetchall()

        if not edges:
            return []

        q_lower = (query or "").lower()
        q_tokens = set(_tokenize(q_lower))

        # Find seed nodes matching query tokens or substring
        all_nodes: set[str] = set()
        for e in edges:
            all_nodes.add(str(e["source_name"]))
            all_nodes.add(str(e["target_name"]))

        seed_nodes: set[str] = set()
        for node in all_nodes:
            n_low = node.lower()
            n_toks = set(_tokenize(n_low))
            if n_low in q_lower or (q_tokens & n_toks):
                seed_nodes.add(node.lower())

        if not seed_nodes:
            return []

        visited_nodes: set[str] = set(seed_nodes)
        queue: deque[tuple[str, int]] = deque((n, 0) for n in seed_nodes)
        visited_edge_keys: set[tuple[str, str, str, str]] = set()
        subgraph: list[dict[str, Any]] = []

        while queue:
            curr_node_low, depth = queue.popleft()
            if depth >= max_hops:
                continue
            for e in edges:
                src = str(e["source_name"])
                dst = str(e["target_name"])
                src_low = src.lower()
                dst_low = dst.lower()
                if curr_node_low not in (src_low, dst_low):
                    continue

                edge_key = (src_low, str(e["relation"]), dst_low, str(e["doc_id"]))
                if edge_key not in visited_edge_keys:
                    visited_edge_keys.add(edge_key)
                    subgraph.append(
                        {
                            "source": src,
                            "source_type": str(e["source_type"]),
                            "relation": str(e["relation"]),
                            "target": dst,
                            "target_type": str(e["target_type"]),
                            "doc_id": str(e["doc_id"]),
                            "evidence": str(e["evidence"]),
                            "hop": depth + 1,
                        }
                    )

                neighbor_low = dst_low if curr_node_low == src_low else src_low
                if neighbor_low not in visited_nodes:
                    visited_nodes.add(neighbor_low)
                    queue.append((neighbor_low, depth + 1))

        return subgraph

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
                """
                INSERT INTO vision_drawings (drawing_id, title, metadata_json, fingerprint_blob, created_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(drawing_id) DO UPDATE SET
                    title = excluded.title,
                    metadata_json = excluded.metadata_json,
                    fingerprint_blob = excluded.fingerprint_blob,
                    created_at = excluded.created_at
                """,
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
            results.append(
                {
                    "drawing_id": r["drawing_id"],
                    "title": r["title"],
                    "metadata": json.loads(r["metadata_json"] or "{}"),
                    "similarity": round(sim, 6),
                }
            )

        results.sort(key=lambda item: item["similarity"], reverse=True)
        return results[: max(1, int(top_k))]


_DEFAULT_RAG: HybridGraphRAG | None = None


def _get_default_rag() -> HybridGraphRAG:
    global _DEFAULT_RAG
    target_db = dbconn.database_file("graph_rag.db")
    if _DEFAULT_RAG is None or _DEFAULT_RAG.db_path != target_db:
        _DEFAULT_RAG = HybridGraphRAG(db_path=target_db)
    return _DEFAULT_RAG


def extract_and_store_triples(doc_id: str, text: str) -> list[dict[str, str]]:
    """Module-level convenience wrapper for extracting and persisting KG triples."""
    return _get_default_rag().extract_and_store_triples(doc_id=doc_id, text=text)


def query_knowledge_subgraph(query: str, hops: int = 2) -> list[dict[str, Any]]:
    """Module-level convenience wrapper for 2-hop BFS Knowledge Graph retrieval."""
    return _get_default_rag().query_knowledge_subgraph(query=query, hops=hops)


def find_similar_drawings(raw_bytes: bytes, top_k: int = 3) -> list[dict[str, Any]]:
    """Module-level convenience wrapper for Vision-RAG drawing similarity search."""
    return _get_default_rag().find_similar_drawings(raw_bytes=raw_bytes, top_k=top_k)


_NUM_CLAIM_RE = re.compile(r"(?:±\s*)?\d+(?:[.,]\d+)?(?:\s*-\s*\d+(?:[.,]\d+)?)?")


def _extract_numbers(text: str) -> list[str]:
    nums: list[str] = []
    for match in _NUM_CLAIM_RE.finditer(text or ""):
        token = match.group(0).replace(",", ".").replace(" ", "")
        if token and token not in nums:
            nums.append(token)
    return nums


def verify_citations(answer: str, retrieved_docs: list[dict[str, Any]]) -> dict[str, Any]:
    """Verify numerical claims in ``answer`` against ``retrieved_docs`` and attach ``[Kaynak: <doc_title>]``."""
    raw_answer = (answer or "").strip()
    if not raw_answer:
        return {
            "annotated_answer": "",
            "verified_claims": [],
            "unverified_claims": [],
            "grounding_ratio": 1.0,
            "citations_attached": 0,
        }

    doc_entries: list[tuple[str, str, set[str]]] = []
    for doc in retrieved_docs or []:
        title = str(doc.get("title") or doc.get("doc_id") or "Bilgi Bankası").strip()
        content = str(doc.get("content") or "")
        nums = set(_extract_numbers(f"{title} {content}"))
        # Also include sub-parts of range tokens like "160-210" -> "160", "210"
        expanded = set(nums)
        for n in list(nums):
            if "-" in n:
                for part in n.split("-"):
                    if part:
                        expanded.add(part)
            if n.startswith("±"):
                expanded.add(n[1:])
        doc_entries.append((title, content, expanded))

    verified_claims: list[dict[str, str]] = []
    unverified_claims: list[str] = []
    citations_attached = 0

    clauses = re.split(r"(?<=[.!?])\s+|\n+", raw_answer)
    annotated_clauses: list[str] = []

    for clause in clauses:
        if not clause.strip():
            continue
        clause_nums = _extract_numbers(clause)
        matched_titles: list[str] = []

        for num in clause_nums:
            clean_num = num.lstrip("±")
            supporting_title: str | None = None
            for title, content, doc_num_set in doc_entries:
                if num in doc_num_set or clean_num in doc_num_set or num in content:
                    supporting_title = title
                    break
            if supporting_title is not None:
                verified_claims.append({"claim": num, "source": supporting_title})
                if supporting_title not in matched_titles:
                    matched_titles.append(supporting_title)
            else:
                if num not in unverified_claims:
                    unverified_claims.append(num)

        updated_clause = clause
        for title in matched_titles:
            tag = f"[Kaynak: {title}]"
            if tag not in updated_clause:
                if updated_clause.endswith((".", "!", "?")):
                    updated_clause = f"{updated_clause[:-1]} {tag}{updated_clause[-1]}"
                else:
                    updated_clause = f"{updated_clause} {tag}"
                citations_attached += 1

        annotated_clauses.append(updated_clause)

    total_claims = len(verified_claims) + len(unverified_claims)
    grounding_ratio = 1.0 if total_claims == 0 else round(len(verified_claims) / total_claims, 4)

    return {
        "annotated_answer": " ".join(annotated_clauses),
        "verified_claims": verified_claims,
        "unverified_claims": unverified_claims,
        "grounding_ratio": grounding_ratio,
        "citations_attached": citations_attached,
    }

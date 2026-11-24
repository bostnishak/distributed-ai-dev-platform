"""RAG-01, 05..15, 17, 25, 28..30: FTS5 Turkish BM25, Vector ANN, Strict Embeddings, Citations & Knowledge Store."""

from __future__ import annotations

import ast
import difflib
import hashlib
import json
import logging
import os
import re
import sqlite3
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np

import config
from rag.parsing import ParsedDocument, chunk_document, parse_document

SAMPLE_KB_PATH = Path(__file__).resolve().parent / "data" / "sample_company_kb.json"

# Turkish suffix stemmer (lightweight Snowball-style inflection stripper for RAG-07)
_TR_SUFFIXES: tuple[str, ...] = (
    "lerindeki", "larındaki", "lerinden", "larından", "lerimiz", "larımız",
    "lerinde", "larında", "lerine", "larına", "lerin", "ların", "leri", "ları",
    "lerden", "lardan", "lerde", "larda", "lere", "lara", "ler", "lar",
    "sinin", "sının", "sunun", "sünün", "nden", "ndan", "inde", "ında",
    "ünde", "unda", "inin", "ının", "ünün", "unun", "deki", "daki",
    "teki", "taki", "den", "dan", "ten", "tan", "nin", "nın", "nun", "nün",
    "miz", "mız", "muz", "müz", "niz", "nız", "nuz", "nüz",
    "de", "da", "te", "ta", "in", "ın", "un", "ün", "si", "sı", "su", "sü",
)

_SYNONYMS: dict[str, tuple[str, ...]] = {
    "sözleşme": ("mukavele", "kontrat", "contract"),
    "tolerans": ("sapma", "pay"),
    "fiyat": ("ücret", "maliyet", "bedel"),
    "belge": ("doküman", "dosya", "rapor"),
}


def tr_lower(text: str) -> str:
    return (text or "").replace("İ", "i").replace("I", "ı").lower()


def stem_turkish_token(token: str) -> str:
    t = tr_lower(token)
    if len(t) <= 4:
        return t
    for suf in _TR_SUFFIXES:
        if t.endswith(suf) and len(t) - len(suf) >= 3:
            return t[: -len(suf)]
    return t


def normalize_turkish_text(text: str, *, expand_synonyms: bool = False) -> str:
    """RAG-07: Turkish-aware lowercase + inflection stemming for SQLite FTS5 indexing & queries."""
    words = re.findall(r"[a-zA-Z0-9çğıöşüÇĞİÖŞÜ]+", tr_lower(text))
    stems: list[str] = []
    for w in words:
        st = stem_turkish_token(w)
        stems.append(st)
        if expand_synonyms and st in _SYNONYMS:
            stems.extend(_SYNONYMS[st])
    return " ".join(stems)


class EmbeddingUnavailableError(RuntimeError):
    """RAG-05: Raised in production when bge-m3 is unavailable (no silent hash fallback)."""


def _test_fallback_embedding(text: str, dim: int = 128) -> np.ndarray:
    """Strictly test-only deterministic vector (forbidden in production by RAG-05)."""
    vec = np.zeros(dim, dtype=np.float32)
    for tok in normalize_turkish_text(text).split():
        h = int(hashlib.blake2b(tok.encode("utf-8"), digest_size=4).hexdigest(), 16)
        vec[h % dim] += 1.0
    norm = float(np.linalg.norm(vec))
    return vec / norm if norm > 0 else vec


@dataclass
class RetrievalHit:
    chunk_id: str
    doc_id: str
    doc_title: str
    collection_id: str
    page: int
    section: str
    content: str
    bm25_score: float
    cosine_score: float
    combined_score: float
    is_ocr: bool = False
    is_sample: bool = False
    quarantine: bool = False


@dataclass
class RetrievalResult:
    status: str  # ok | empty | disabled
    policy_state: str  # grounded | unverified_general | abstain | disabled
    hits: list[RetrievalHit] = field(default_factory=list)
    citations: list[dict[str, Any]] = field(default_factory=list)
    context_block: str = ""
    warning: str = ""
    rewritten_query: str = ""


def _rag_db_path() -> Path:
    p = Path(config.DATA_DIR) / "rag.db"
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


class RAGStore:
    """Unified RAG Engine covering RAG-01, 05..15, 17, 25, 28, 29, 30."""

    EMBED_MODEL = "bge-m3:latest"
    EMBED_VERSION = "1.0"

    def __init__(self, db_path: Path | None = None, *, allow_test_embeddings: bool | None = None) -> None:
        self.db_path = db_path or _rag_db_path()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        # RAG-05: NEVER enable fallback embeddings in production; only when explicitly allowed in unit tests.
        self.allow_test_embeddings = (
            bool(allow_test_embeddings)
            if allow_test_embeddings is not None
            else (os.environ.get("RAG_ALLOW_TEST_EMBEDDINGS", "0") == "1")
        )
        self.embedding_status: str = "ready"
        self.embedding_reason: str = ""
        self._init_db()

    def _conn(self) -> sqlite3.Connection:
        import dbconn

        return dbconn.open_db(self.db_path)

    def _init_db(self) -> None:
        with self._conn() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS rag_collections (
                    collection_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    scope TEXT NOT NULL DEFAULT 'personal',
                    owner_id TEXT NOT NULL DEFAULT 'default',
                    is_sample INTEGER NOT NULL DEFAULT 0,
                    quota_docs INTEGER NOT NULL DEFAULT 500,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS rag_documents (
                    doc_id TEXT PRIMARY KEY,
                    collection_id TEXT NOT NULL,
                    title TEXT NOT NULL,
                    source_type TEXT NOT NULL,
                    version INTEGER NOT NULL DEFAULT 1,
                    page_count INTEGER NOT NULL DEFAULT 1,
                    is_sample INTEGER NOT NULL DEFAULT 0,
                    metadata_json TEXT NOT NULL DEFAULT '{}',
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS rag_chunks (
                    chunk_id TEXT PRIMARY KEY,
                    doc_id TEXT NOT NULL,
                    collection_id TEXT NOT NULL,
                    page INTEGER NOT NULL DEFAULT 1,
                    section TEXT NOT NULL DEFAULT '',
                    chunk_index INTEGER NOT NULL DEFAULT 0,
                    offset INTEGER NOT NULL DEFAULT 0,
                    content_hash TEXT NOT NULL,
                    content TEXT NOT NULL,
                    norm_content TEXT NOT NULL,
                    embedding_blob BLOB,
                    embedding_model TEXT NOT NULL DEFAULT '',
                    embedding_dim INTEGER NOT NULL DEFAULT 0,
                    embedding_version TEXT NOT NULL DEFAULT '1.0',
                    is_ocr INTEGER NOT NULL DEFAULT 0,
                    quarantine INTEGER NOT NULL DEFAULT 0,
                    pii_tags_json TEXT NOT NULL DEFAULT '[]',
                    created_at TEXT NOT NULL
                );
                CREATE VIRTUAL TABLE IF NOT EXISTS rag_chunks_fts USING fts5(
                    chunk_id UNINDEXED,
                    collection_id UNINDEXED,
                    title,
                    norm_content,
                    tokenize='unicode61'
                );
                CREATE TABLE IF NOT EXISTS ingest_jobs (
                    job_id TEXT PRIMARY KEY,
                    collection_id TEXT NOT NULL,
                    filename TEXT NOT NULL,
                    status TEXT NOT NULL,
                    progress INTEGER NOT NULL DEFAULT 0,
                    chunks_done INTEGER NOT NULL DEFAULT 0,
                    chunks_total INTEGER NOT NULL DEFAULT 0,
                    retries INTEGER NOT NULL DEFAULT 0,
                    error TEXT NOT NULL DEFAULT '',
                    checkpoint_json TEXT NOT NULL DEFAULT '{}',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS rag_triples (
                    triple_id TEXT PRIMARY KEY,
                    collection_id TEXT NOT NULL,
                    subject TEXT NOT NULL,
                    predicate TEXT NOT NULL,
                    object TEXT NOT NULL,
                    confidence REAL NOT NULL DEFAULT 0.8,
                    source_chunk_id TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_rag_chunks_col ON rag_chunks(collection_id);
                CREATE INDEX IF NOT EXISTS idx_rag_chunks_doc ON rag_chunks(doc_id);
                """
            )

    # ---------------------------------------------------------------- RAG-12 Collections & Permissions

    def ensure_collection(
        self,
        collection_id: str,
        name: str = "",
        *,
        scope: str = "personal",
        owner_id: str = "default",
        is_sample: bool = False,
        quota_docs: int = 500,
    ) -> dict[str, Any]:
        now = datetime.now(UTC).isoformat()
        with self._conn() as conn:
            conn.execute(
                """
                INSERT OR IGNORE INTO rag_collections
                    (collection_id, name, scope, owner_id, is_sample, quota_docs, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (collection_id, name or collection_id, scope, owner_id, int(is_sample), int(quota_docs), now),
            )
            row = conn.execute("SELECT * FROM rag_collections WHERE collection_id = ?", (collection_id,)).fetchone()
        return dict(row) if row else {}

    def list_collections(self, user_id: str = "default") -> list[dict[str, Any]]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT * FROM rag_collections WHERE owner_id = ? OR scope = 'team' OR is_sample = 1 ORDER BY created_at DESC",
                (user_id,),
            ).fetchall()
        return [dict(r) for r in rows]

    def can_access_collection(self, collection_id: str, user_id: str) -> bool:
        with self._conn() as conn:
            row = conn.execute("SELECT owner_id, scope, is_sample FROM rag_collections WHERE collection_id = ?", (collection_id,)).fetchone()
        if not row:
            return False
        return row["owner_id"] == user_id or row["scope"] == "team" or bool(row["is_sample"])

    def delete_document(self, doc_id: str, *, user_id: str = "default") -> bool:
        """RAG-12: Delete document + its embeddings + FTS5 entries immediately."""
        with self._conn() as conn:
            row = conn.execute("SELECT collection_id FROM rag_documents WHERE doc_id = ?", (doc_id,)).fetchone()
            if not row:
                return False
            if not self.can_access_collection(row["collection_id"], user_id):
                raise PermissionError("Bu koleksiyondaki belgeyi silme yetkiniz yok.")
            chunk_ids = [r["chunk_id"] for r in conn.execute("SELECT chunk_id FROM rag_chunks WHERE doc_id = ?", (doc_id,)).fetchall()]
            for cid in chunk_ids:
                conn.execute("DELETE FROM rag_chunks_fts WHERE chunk_id = ?", (cid,))
            conn.execute("DELETE FROM rag_chunks WHERE doc_id = ?", (doc_id,))
            conn.execute("DELETE FROM rag_documents WHERE doc_id = ?", (doc_id,))
        return True

    def list_documents(self, collection_id: str, *, user_id: str = "default") -> list[dict[str, Any]]:
        with self._conn() as conn:
            exists = conn.execute("SELECT 1 FROM rag_collections WHERE collection_id = ?", (collection_id,)).fetchone()
        if not exists:
            return []  # a collection that was never created has no documents; that is not a permission problem
        if not self.can_access_collection(collection_id, user_id):
            raise PermissionError("Bu koleksiyonu görüntüleme yetkiniz yok.")
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT d.*, (SELECT COUNT(*) FROM rag_chunks c WHERE c.doc_id = d.doc_id) AS chunk_count "
                "FROM rag_documents d WHERE d.collection_id = ? ORDER BY d.created_at DESC",
                (collection_id,),
            ).fetchall()
        return [dict(r) for r in rows]

    # ---------------------------------------------------------------- RAG-05 Strict Embedding Resolver

    async def _embed_vector(self, text: str, embed_fn=None) -> tuple[np.ndarray, str, int]:
        if embed_fn is not None:
            raw = await embed_fn(text)
            arr = np.asarray(raw, dtype=np.float32)
            norm = float(np.linalg.norm(arr))
            return (arr / norm if norm > 0 else arr), self.EMBED_MODEL, int(arr.shape[0])

        import gateway

        try:
            vec = await gateway.default_client.embed(text, model=self.EMBED_MODEL)
            if vec and len(vec) >= 32:
                arr = np.asarray(vec, dtype=np.float32)
                norm = float(np.linalg.norm(arr))
                self.embedding_status = "ready"
                self.embedding_reason = ""
                return (arr / norm if norm > 0 else arr), self.EMBED_MODEL, int(arr.shape[0])
        except Exception as exc:
            logging.getLogger(__name__).debug("Ollama embedding fallback triggered: %s", exc)

        if self.allow_test_embeddings:
            arr = _test_fallback_embedding(text)
            return arr, "test-embedding", int(arr.shape[0])

        self.embedding_status = "disabled"
        self.embedding_reason = "Bilgi bankası devre dışı: bge-m3 çekilmedi"
        raise EmbeddingUnavailableError(self.embedding_reason)

    # ---------------------------------------------------------------- RAG-01 Resumable Ingestion Pipeline

    async def ingest_document(
        self,
        *,
        collection_id: str,
        file_path: Path | None = None,
        raw_text: str | None = None,
        title: str = "",
        user_id: str = "default",
        is_sample: bool = False,
        embed_fn=None,
        resume_job_id: str | None = None,
    ) -> dict[str, Any]:
        """RAG-01: Full pipeline (detect -> parse -> scan -> chunk -> embed -> index) with resumable jobs."""
        self.ensure_collection(collection_id, owner_id=user_id, is_sample=is_sample)
        now = datetime.now(UTC).isoformat()
        parsed: ParsedDocument = parse_document(file_path=file_path, raw_text=raw_text, title=title)
        chunks = chunk_document(parsed)
        job_id = resume_job_id or f"ing-{uuid.uuid4().hex[:10]}"
        doc_id = f"doc-{uuid.uuid4().hex[:10]}"

        start_idx = 0
        if resume_job_id:
            with self._conn() as conn:
                jrow = conn.execute("SELECT * FROM ingest_jobs WHERE job_id = ?", (resume_job_id,)).fetchone()
                if jrow:
                    cp = json.loads(jrow["checkpoint_json"] or "{}")
                    start_idx = int(cp.get("next_chunk_index") or 0)
                    doc_id = str(cp.get("doc_id") or doc_id)

        with self._conn() as conn:
            conn.execute(
                """
                INSERT INTO ingest_jobs
                    (job_id, collection_id, filename, status, progress, chunks_done, chunks_total, retries, error, checkpoint_json, created_at, updated_at)
                VALUES (?, ?, ?, 'running', 0, ?, ?, 0, '', ?, ?, ?)
                ON CONFLICT(job_id) DO UPDATE SET status='running', retries=retries+1, updated_at=excluded.updated_at
                """,
                (job_id, collection_id, parsed.title, start_idx, len(chunks), json.dumps({"doc_id": doc_id, "next_chunk_index": start_idx}), now, now),
            )
            conn.execute(
                """
                INSERT OR IGNORE INTO rag_documents
                    (doc_id, collection_id, title, source_type, version, page_count, is_sample, metadata_json, created_at)
                VALUES (?, ?, ?, ?, 1, ?, ?, ?, ?)
                """,
                (doc_id, collection_id, parsed.title, parsed.source_type, len(parsed.pages), int(is_sample), json.dumps({"warnings": parsed.warnings}, ensure_ascii=False), now),
            )

        try:
            for ch in chunks[start_idx:]:
                vec, model_name, dim = await self._embed_vector(ch.content, embed_fn=embed_fn)
                cid = f"chk-{uuid.uuid4().hex[:10]}"
                norm_txt = normalize_turkish_text(ch.content)
                with self._conn() as conn:
                    conn.execute(
                        """
                        INSERT INTO rag_chunks
                            (chunk_id, doc_id, collection_id, page, section, chunk_index, offset, content_hash,
                             content, norm_content, embedding_blob, embedding_model, embedding_dim, embedding_version,
                             is_ocr, quarantine, pii_tags_json, created_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            cid, doc_id, collection_id, ch.page, ch.section, ch.chunk_index, ch.offset,
                            ch.content_hash, ch.content, norm_txt, vec.tobytes(), model_name, dim,
                            self.EMBED_VERSION, int(ch.is_ocr), int(ch.quarantine),
                            json.dumps(ch.pii_tags), datetime.now(UTC).isoformat(),
                        ),
                    )
                    conn.execute(
                        "INSERT INTO rag_chunks_fts (chunk_id, collection_id, title, norm_content) VALUES (?, ?, ?, ?)",
                        (cid, collection_id, normalize_turkish_text(parsed.title), norm_txt),
                    )
                    done = ch.chunk_index + 1
                    pct = int(done * 100 / max(1, len(chunks)))
                    conn.execute(
                        "UPDATE ingest_jobs SET progress=?, chunks_done=?, checkpoint_json=?, updated_at=? WHERE job_id=?",
                        (pct, done, json.dumps({"doc_id": doc_id, "next_chunk_index": done}), datetime.now(UTC).isoformat(), job_id),
                    )
        except Exception as exc:
            with self._conn() as conn:
                conn.execute(
                    "UPDATE ingest_jobs SET status='failed', error=?, updated_at=? WHERE job_id=?",
                    (str(exc)[:300], datetime.now(UTC).isoformat(), job_id),
                )
            raise

        with self._conn() as conn:
            conn.execute(
                "UPDATE ingest_jobs SET status='completed', progress=100, updated_at=? WHERE job_id=?",
                (datetime.now(UTC).isoformat(), job_id),
            )

        return {
            "job_id": job_id,
            "doc_id": doc_id,
            "title": parsed.title,
            "page_count": len(parsed.pages),
            "chunks_indexed": len(chunks),
            "warnings": parsed.warnings,
            "summary_note": f"{len(parsed.pages)} sayfa okundu ({len(chunks)} parça dizinlendi).",
        }

    def get_ingest_job(self, job_id: str) -> dict[str, Any] | None:
        with self._conn() as conn:
            row = conn.execute("SELECT * FROM ingest_jobs WHERE job_id = ?", (job_id,)).fetchone()
        return dict(row) if row else None

    # ---------------------------------------------------------------- RAG-10 Query Rewriter

    def rewrite_query(self, query: str, recent_turns: list[str] | None = None) -> str:
        """RAG-10: Expand pronoun-dependent follow-up queries using recent turn subjects."""
        q = (query or "").strip()
        if not recent_turns:
            return q
        low = tr_lower(q)
        pronouns = ("onun", "bunun", "şunun", "peki ya", "ondan", "buna", "its", "that one", "what about it")
        if any(p in low for p in pronouns):
            anchor = recent_turns[-1].strip()[:120]
            return f"{anchor} - {q}"
        return q

    # ---------------------------------------------------------------- RAG-06, 07, 08, 09, 11, 30 Hybrid Search

    async def search(
        self,
        query: str,
        *,
        collection_ids: list[str] | None = None,
        user_id: str = "default",
        top_k: int = 5,
        risk: str = "low",
        recent_turns: list[str] | None = None,
        min_combined_threshold: float = 0.22,
        rerank: bool = True,
        embed_fn=None,
    ) -> RetrievalResult:
        """Hybrid FTS5 BM25 + vectorized ANN cosine search + absolute relevance gate + citations."""
        rewritten = self.rewrite_query(query, recent_turns)
        try:
            q_vec, _m, q_dim = await self._embed_vector(rewritten, embed_fn=embed_fn)
        except EmbeddingUnavailableError as exc:
            return RetrievalResult(status="disabled", policy_state="disabled", warning=str(exc), rewritten_query=rewritten)

        allowed_cols = [c["collection_id"] for c in self.list_collections(user_id)]
        target_cols = [c for c in (collection_ids or allowed_cols) if c in allowed_cols]
        if not target_cols:
            return self._no_source_result(risk=risk, rewritten=rewritten)

        norm_q = normalize_turkish_text(rewritten, expand_synonyms=True)
        fts_terms = [t for t in norm_q.split() if len(t) >= 2][:12]
        bm25_scores: dict[str, float] = {}

        placeholders = ",".join("?" * len(target_cols))
        with self._conn() as conn:
            if fts_terms:
                fts_query = " OR ".join(f'"{t}"' for t in fts_terms)
                try:
                    rows = conn.execute(
                        f"SELECT chunk_id, bm25(rag_chunks_fts) AS rank FROM rag_chunks_fts "
                        f"WHERE rag_chunks_fts MATCH ? AND collection_id IN ({placeholders}) ORDER BY rank LIMIT 30",
                        (fts_query, *target_cols),
                    ).fetchall()
                    for r in rows:
                        # FTS5 bm25() is negative (more negative = better match)
                        bm25_scores[r["chunk_id"]] = min(1.0, max(0.0, -float(r["rank"]) / 8.0))
                except sqlite3.OperationalError:
                    pass

            chunk_rows = conn.execute(
                f"""
                SELECT c.*, d.title AS doc_title, d.is_sample AS doc_is_sample
                FROM rag_chunks c
                JOIN rag_documents d ON c.doc_id = d.doc_id
                WHERE c.collection_id IN ({placeholders}) AND c.embedding_dim = ?
                """,
                (*target_cols, q_dim),
            ).fetchall()

        if not chunk_rows:
            return self._no_source_result(risk=risk, rewritten=rewritten)

        # RAG-06: Vectorized NumPy ANN similarity matrix
        mat = np.vstack([np.frombuffer(r["embedding_blob"], dtype=np.float32) for r in chunk_rows])
        cos_scores = mat @ q_vec

        # RAG-08: RRF ranking + absolute relevance threshold (prevents irrelevant chunks entering context!)
        bm25_rank = {cid: i + 1 for i, (cid, _) in enumerate(sorted(bm25_scores.items(), key=lambda x: x[1], reverse=True))}
        vec_order = np.argsort(-cos_scores)
        vec_rank = {chunk_rows[int(idx)]["chunk_id"]: i + 1 for i, idx in enumerate(vec_order[:30])}

        q_set = set(fts_terms)
        candidates: list[RetrievalHit] = []
        for idx, row in enumerate(chunk_rows):
            cid = row["chunk_id"]
            b_sc = bm25_scores.get(cid, 0.0)
            c_sc = float(cos_scores[idx])
            if cid not in bm25_rank and cid not in vec_rank:
                continue
            rrf = (1.0 / (60 + bm25_rank.get(cid, 1000))) + (1.0 / (60 + vec_rank.get(cid, 1000)))
            # RAG-09 lightweight cross-signal overlap reranker
            doc_tokens = set(str(row["norm_content"]).split())
            overlap = len(q_set & doc_tokens) / max(1, len(q_set))
            combined = 0.45 * max(0.0, c_sc) + 0.35 * b_sc + 0.20 * overlap + (0.05 * rrf if rerank else 0.0)
            if combined < min_combined_threshold:
                continue
            candidates.append(
                RetrievalHit(
                    chunk_id=cid,
                    doc_id=row["doc_id"],
                    doc_title=row["doc_title"],
                    collection_id=row["collection_id"],
                    page=int(row["page"]),
                    section=str(row["section"]),
                    content=str(row["content"]),
                    bm25_score=round(b_sc, 4),
                    cosine_score=round(c_sc, 4),
                    combined_score=round(combined, 4),
                    is_ocr=bool(row["is_ocr"]),
                    is_sample=bool(row["doc_is_sample"]),
                    quarantine=bool(row["quarantine"]),
                )
            )

        candidates.sort(key=lambda h: h.combined_score, reverse=True)
        hits = candidates[:top_k]
        if not hits:
            return self._no_source_result(risk=risk, rewritten=rewritten)

        # RAG-11: Citation standard [S1]..[Sn]
        citations: list[dict[str, Any]] = []
        ctx_lines: list[str] = []
        for i, h in enumerate(hits, start=1):
            sid = f"S{i}"
            tags = []
            if h.is_sample:
                tags.append("örnek")
            if h.is_ocr:
                tags.append("OCR")
            if h.quarantine:
                tags.append("karantina-güvenilmez-veri")
            tag_str = f" ({', '.join(tags)})" if tags else ""
            citations.append({
                "id": sid,
                "chunk_id": h.chunk_id,
                "doc_id": h.doc_id,
                "doc": h.doc_title,
                "page": h.page,
                "section": h.section,
                "quote": h.content[:240],
                "is_sample": h.is_sample,
                "is_ocr": h.is_ocr,
            })
            body = f"<untrusted_chunk>{h.content}</untrusted_chunk>" if h.quarantine else h.content
            ctx_lines.append(f"[{sid}] {h.doc_title} (Sayfa {h.page}){tag_str}:\n{body}")

        return RetrievalResult(
            status="ok",
            policy_state="grounded",
            hits=hits,
            citations=citations,
            context_block="\n\n".join(ctx_lines),
            rewritten_query=rewritten,
        )

    def _no_source_result(self, *, risk: str, rewritten: str) -> RetrievalResult:
        """RAG-30: Explicit behavior policy when retrieval finds no relevant chunks."""
        if risk == "high":
            return RetrievalResult(
                status="empty",
                policy_state="abstain",
                warning="Yüksek riskli soruda güvenilir kaynak bulunamadı; doğrulama olmadan yanıt üretilemez.",
                rewritten_query=rewritten,
            )
        return RetrievalResult(
            status="empty",
            policy_state="unverified_general",
            warning="Bilgi bankasında ilgili kaynak bulunamadı; genel bilgiyle (doğrulanmamış) yanıt veriliyor.",
            rewritten_query=rewritten,
        )

    def get_chunk(self, chunk_id: str) -> dict[str, Any] | None:
        """RAG-27: Source viewer endpoint lookup."""
        with self._conn() as conn:
            row = conn.execute(
                "SELECT c.*, d.title AS doc_title FROM rag_chunks c JOIN rag_documents d ON c.doc_id = d.doc_id WHERE c.chunk_id = ?",
                (chunk_id,),
            ).fetchone()
        if not row:
            return None
        d = dict(row)
        d.pop("embedding_blob", None)
        return d

    # ---------------------------------------------------------------- RAG-13 External Sample KB Loader

    async def seed_sample_company_kb(self, embed_fn=None) -> int:
        if not SAMPLE_KB_PATH.is_file():
            return 0
        docs = json.loads(SAMPLE_KB_PATH.read_text(encoding="utf-8"))
        self.ensure_collection("sample_company_kb", "Örnek Mühendislik Bilgi Bankası", scope="team", is_sample=True)
        existing = {d["title"] for d in self.list_documents("sample_company_kb", user_id="default")}
        added = 0
        for item in docs:
            if item["title"] in existing:
                continue
            await self.ingest_document(
                collection_id="sample_company_kb",
                raw_text=f"# {item['title']}\n\n{item['content']}",
                title=item["title"],
                is_sample=True,
                embed_fn=embed_fn,
            )
            added += 1
        return added

    # ---------------------------------------------------------------- RAG-15 Multi-Doc Diff & Contradictions

    @staticmethod
    def compare_documents(doc_a_text: str, doc_b_text: str, *, label_a: str = "Belge A", label_b: str = "Belge B") -> dict[str, Any]:
        """RAG-15: Deterministic diff + contradiction matrix across two document texts."""
        lines_a = [ln.strip() for ln in (doc_a_text or "").splitlines() if ln.strip()]
        lines_b = [ln.strip() for ln in (doc_b_text or "").splitlines() if ln.strip()]
        sm = difflib.SequenceMatcher(None, lines_a, lines_b)
        diffs: list[dict[str, Any]] = []
        for tag, i1, i2, j1, j2 in sm.get_opcodes():
            if tag == "equal":
                continue
            diffs.append({
                "change_type": tag,
                label_a: " ".join(lines_a[i1:i2]),
                label_b: " ".join(lines_b[j1:j2]),
                "lines_a": [i1 + 1, i2],
                "lines_b": [j1 + 1, j2],
            })
        return {"similarity": round(sm.ratio(), 4), "difference_count": len(diffs), "differences": diffs}

    # ---------------------------------------------------------------- RAG-28 Codebase AST Indexing

    async def ingest_codebase_file(self, file_path: Path, *, collection_id: str = "codebase", embed_fn=None) -> dict[str, Any]:
        """RAG-28: AST-based symbol chunking (functions/classes) with file:line citations."""
        import asyncio

        src = await asyncio.to_thread(file_path.read_text, encoding="utf-8", errors="ignore")
        lines = src.splitlines()
        sections: list[str] = []
        if file_path.suffix == ".py":
            try:
                tree = ast.parse(src)
                for node in tree.body:
                    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                        start = node.lineno
                        end = getattr(node, "end_lineno", start)
                        snippet = "\n".join(lines[start - 1 : end])
                        sections.append(f"## {file_path.name}:{start}-{end} `{node.name}`\n```python\n{snippet}\n```")
            except SyntaxError:
                pass
        md = "\n\n".join(sections) if sections else f"## {file_path.name}:1-{len(lines)}\n```\n{src[:4000]}\n```"
        return await self.ingest_document(collection_id=collection_id, raw_text=md, title=str(file_path.name), embed_fn=embed_fn)

    # ---------------------------------------------------------------- RAG-17 Gated GraphRAG Triples

    def add_triple(self, collection_id: str, subject: str, predicate: str, obj: str, source_chunk_id: str, confidence: float = 0.85) -> str:
        tid = f"trp-{uuid.uuid4().hex[:10]}"
        with self._conn() as conn:
            conn.execute(
                "INSERT INTO rag_triples (triple_id, collection_id, subject, predicate, object, confidence, source_chunk_id) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (tid, collection_id, subject.strip(), predicate.strip(), obj.strip(), float(confidence), source_chunk_id),
            )
        return tid

    def query_graph_relations(self, entity: str, collection_id: str | None = None) -> list[dict[str, Any]]:
        key = f"%{tr_lower(entity)}%"
        with self._conn() as conn:
            if collection_id:
                rows = conn.execute(
                    "SELECT * FROM rag_triples WHERE collection_id = ? AND (lower(subject) LIKE ? OR lower(object) LIKE ?)",
                    (collection_id, key, key),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM rag_triples WHERE lower(subject) LIKE ? OR lower(object) LIKE ?",
                    (key, key),
                ).fetchall()
        return [dict(r) for r in rows]


default_rag_store = RAGStore()

"""RAG-12, RAG-25, RAG-27: FastAPI Knowledge Base, Source Viewer & Doctor Endpoints (SEC-22 Compliant)."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from access_control import require_local_or_admin
from rag.store import default_rag_store
from rag.web import web_search

router = APIRouter(prefix="/api/rag", tags=["rag"])
_LOCAL_OR_ADMIN = [Depends(require_local_or_admin)]


class CreateCollectionReq(BaseModel):
    collection_id: str = Field(..., min_length=1, max_length=80)
    name: str = ""
    scope: str = "personal"
    user_id: str = "default"


class IngestTextReq(BaseModel):
    collection_id: str = "default"
    title: str = Field(..., min_length=1)
    content: str = Field(..., min_length=1)
    user_id: str = "default"


class SearchReq(BaseModel):
    query: str = Field(..., min_length=1)
    collection_ids: list[str] | None = None
    user_id: str = "default"
    top_k: int = Field(5, ge=1, le=20)
    risk: str = "low"


@router.get("/collections")
async def api_list_collections(user_id: str = "default"):
    return {
        "embedding_status": default_rag_store.embedding_status,
        "embedding_reason": default_rag_store.embedding_reason,
        "collections": default_rag_store.list_collections(user_id=user_id),
    }


@router.post("/collections", dependencies=_LOCAL_OR_ADMIN)
async def api_create_collection(body: CreateCollectionReq):
    return default_rag_store.ensure_collection(
        body.collection_id,
        body.name or body.collection_id,
        scope=body.scope,
        owner_id=body.user_id,
    )


@router.post("/ingest", dependencies=_LOCAL_OR_ADMIN)
async def api_ingest_text(body: IngestTextReq):
    try:
        return await default_rag_store.ingest_document(
            collection_id=body.collection_id,
            raw_text=body.content,
            title=body.title,
            user_id=body.user_id,
        )
    except Exception as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.get("/collections/{collection_id}/documents")
async def api_list_documents(collection_id: str, user_id: str = "default"):
    try:
        return {"documents": default_rag_store.list_documents(collection_id, user_id=user_id)}
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


@router.delete("/documents/{doc_id}", dependencies=_LOCAL_OR_ADMIN)
async def api_delete_document(doc_id: str, user_id: str = "default"):
    try:
        ok = default_rag_store.delete_document(doc_id, user_id=user_id)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    if not ok:
        raise HTTPException(status_code=404, detail="Belge bulunamadı.")
    return {"deleted": True, "doc_id": doc_id}


@router.post("/search", dependencies=_LOCAL_OR_ADMIN)
async def api_search_rag(body: SearchReq):
    res = await default_rag_store.search(
        body.query,
        collection_ids=body.collection_ids,
        user_id=body.user_id,
        top_k=body.top_k,
        risk=body.risk,
    )
    return {
        "status": res.status,
        "policy_state": res.policy_state,
        "warning": res.warning,
        "rewritten_query": res.rewritten_query,
        "citations": res.citations,
        "hits": [h.__dict__ for h in res.hits],
    }


@router.get("/chunks/{chunk_id}")
async def api_get_chunk(chunk_id: str):
    """RAG-27: Source viewer chunk inspection."""
    ch = default_rag_store.get_chunk(chunk_id)
    if not ch:
        raise HTTPException(status_code=404, detail="Kaynak artık yok.")
    return ch


@router.get("/jobs/{job_id}")
async def api_get_ingest_job(job_id: str):
    job = default_rag_store.get_ingest_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Dizinleme işi bulunamadı.")
    return job


@router.get("/web/search")
async def api_web_search(q: str, max_results: int = 5):
    res = await web_search(q, max_results=max_results)
    return {
        "status": res.status,
        "verification_badge": res.verification_badge,
        "warning": res.warning,
        "sources": [s.__dict__ for s in res.sources],
    }


def diagnose_and_repair_rag(store=None, *, repair: bool = False) -> dict[str, Any]:
    """RAG-25: Inspect & optionally repair duplicates, empty embeddings, orphaned chunks, and model mismatches."""
    st = store or default_rag_store
    with st._conn() as conn:
        orphans = [
            r["chunk_id"]
            for r in conn.execute(
                "SELECT chunk_id FROM rag_chunks WHERE doc_id NOT IN (SELECT doc_id FROM rag_documents)"
            ).fetchall()
        ]
        empty_emb = [
            r["chunk_id"]
            for r in conn.execute(
                "SELECT chunk_id FROM rag_chunks WHERE embedding_blob IS NULL OR embedding_dim = 0"
            ).fetchall()
        ]
        dups = [
            r["chunk_id"]
            for r in conn.execute(
                """
                SELECT chunk_id FROM rag_chunks
                WHERE rowid NOT IN (
                    SELECT MIN(rowid) FROM rag_chunks GROUP BY doc_id, content_hash
                )
                """
            ).fetchall()
        ]
        mismatched = [
            r["chunk_id"]
            for r in conn.execute(
                "SELECT chunk_id FROM rag_chunks WHERE embedding_model NOT IN (?, 'test-embedding')",
                (st.EMBED_MODEL,),
            ).fetchall()
        ]
        repaired_count = 0
        if repair:
            to_remove = set(orphans) | set(empty_emb) | set(dups)
            for cid in to_remove:
                conn.execute("DELETE FROM rag_chunks WHERE chunk_id = ?", (cid,))
                conn.execute("DELETE FROM rag_chunks_fts WHERE chunk_id = ?", (cid,))
                repaired_count += 1

    return {
        "healthy": not (orphans or empty_emb or dups or mismatched),
        "orphans": len(orphans),
        "empty_embeddings": len(empty_emb),
        "duplicates": len(dups),
        "model_mismatches": len(mismatched),
        "repaired": repaired_count,
    }


@router.post("/doctor", dependencies=_LOCAL_OR_ADMIN)
async def api_rag_doctor(repair: bool = False):
    return diagnose_and_repair_rag(default_rag_store, repair=repair)

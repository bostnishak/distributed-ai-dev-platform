# ADR-0005: Embedded SQLite FTS5 and sqlite-vec Vector Storage (Decision D5)

- **Status:** Accepted
- **Date:** 2026-11-23
- **Related Plan Items:** RAG-04, RAG-05, DAT-10, DAT-11

## Context
Audit Finding F8 showed naive O(N) full-table scans over unversioned embedding blobs. Running a separate Qdrant/Milvus server adds operational overhead on student laptops.

## Decision
Store lexical indexes in **SQLite FTS5** (with Turkish normalization) and dense vectors in **SQLite (`sqlite-vec` compatible schema)** with explicit `embedding_model`, `dim`, and `version` columns (`DAT-11`). Combine scores via Reciprocal Rank Fusion (RRF) plus a strict relevance threshold gate (`RAG-08`).

## Consequences
- Single-file backup, portability, and zero extra daemons.
- Mixed embedding models are prevented from silently corrupting cosine similarity rankings.

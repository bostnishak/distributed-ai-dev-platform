# ADR-0012: Local Web Archive, Turkish Eval Studio, Numeric Verification, Advanced RAG & Memory Conflicts (Wave 3B)

- **Status:** Accepted
- **Date:** 2026-11-24

## Decision
1. **EPK-01 (`master/rag/crawler.py`):** Supplement SearXNG (`docker-compose.yml`) with a robots.txt-compliant, SSRF-checked, deduplicated local SQLite `web_archive` returning `[S1]` citations in offline mode.
2. **EPK-02 (`master/eval_studio.py` + `eval/datasets/turkish_benchmark_v1.jsonl`):** Versioned 300-sample Turkish evaluation corpus across 6 tasks with dual-annotator Cohen's kappa (`POST /api/eval-studio/kappa`).
3. **EPK-07 (`master/hallucination/numeric_check.py`):** Deterministic sentence-level citation mapping and SI/financial unit-normalized numeric consistency verifier (`POST /api/hallucination/numeric-verify`).
4. **EPK-14 (`master/rag/advanced.py`):** Parent-child hierarchical chunking, Turkish/English query rewriting, cross-reranking, and nDCG@k evaluation.
5. **EPK-15 (`master/memory_conflicts.py`):** Contradiction detection queue (`memory_conflicts`), user-confirmed resolution, and exponential half-life time-decay consolidation with memory provenance IDs.

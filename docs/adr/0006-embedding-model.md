# ADR-0006: Multilingual Embedding Model Selection (Decision D6)

- **Status:** Accepted
- **Date:** 2026-11-23
- **Related Plan Items:** RAG-05, RAG-07, RAG-26

## Context
The platform's UI, prompts, and uploaded university documents are primarily Turkish and English. Earlier fallbacks silently degraded to a 256-dim n-gram hash when Ollama embedding models were absent (Audit Finding F8).

## Decision
Standardize on **`bge-m3`** via local Ollama as the primary multilingual embedding model, paired with deterministic Turkish diacritic folding (`RAG-07`) for FTS5 lexical search. Never silently fall back to low-quality hash vectors without surfacing a degraded readiness status and explicit metadata flag.

## Consequences
- Strong Turkish/English semantic retrieval quality out of the box.
- `/ready` and `scripts/rag_doctor.py` immediately report missing embedding models.

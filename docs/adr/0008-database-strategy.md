# ADR-0008: Unified SQLite WAL Strategy with Versioned Migrations (Decision D8)

- **Status:** Accepted
- **Date:** 2026-11-23
- **Related Plan Items:** DAT-01, DAT-02, DAT-03, DAT-04, DAT-15, DAT-16

## Context
Audit Finding F14 found multiple SQLite files (`platform.db`, `user_profile.db`, `cognitive_memory.db`, `graph_rag.db`) with inconsistent PRAGMAs, manual `ALTER TABLE` lists, and lock contention between HTTP handlers and background workers.

## Decision
1. Route all SQLite connections through `master/dbconn.py` (`WAL`, `synchronous=NORMAL`, `busy_timeout=10000`, `foreign_keys=ON`).
2. Manage schema evolution with numbered SQL migrations and `schema_version` tracking (`master/migrate.py`).
3. Provide reversible consolidation into a single `platform.db` behind the `UNIFIED_DB` feature flag (`master/dbunify.py`), keeping Postgres compatibility (`DAT-16`) deferred until measured scale demands it.

## Consequences
- Zero `database is locked` errors under concurrent read/write stress tests.
- Clean backups, reproducible ERD (`docs/plan-v2/erd.md`), and deterministic schema upgrades.

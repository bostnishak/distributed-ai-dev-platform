# Runbook: Web Search Archive, Eval Studio & Memory Conflict Resolution

## 1. Offline Web Search Mode
- When `SEARXNG_URL` is unreachable, archive vetted references via `POST /api/rag/web/archive` and query them via `POST /api/rag/web/archive/search`.

## 2. Running Inter-Annotator Reliability (Cohen's Kappa)
- Submit labels from two annotators to `POST /api/eval-studio/annotate` and verify `kappa >= 0.61` via `POST /api/eval-studio/kappa`.

## 3. Resolving Memory Contradictions
- Inspect open conflicts via `GET /api/memory/conflicts?status=open` and resolve with `POST /api/memory/conflicts/{id}/resolve`.

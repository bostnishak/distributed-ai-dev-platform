# Sprint 4 — Progress Report

| | |
|---|---|
| Sprint | 4 (19 Kasım – 2 Aralık 2026) |
| Team | team6 — CM6453 Software Engineering Process and DevOps |
| Prepared by | Zeynep Duru Küçük (Scrum Master) |
| Date | 2 Aralık 2026 |

## Summary

Sprint 4 delivered error recovery, automated code quality gates, and conflict resolution. The platform now enforces a maximum retry limit (3 attempts), detects file conflicts between tasks, routes review tasks away from the original author, and provides a contract-check endpoint that verifies frontend API calls match backend routes. 150 unit tests pass (16 new).

## Task assignments and time tracking

| Member | Role | Items | Est. (h) | Actual (h) | Key files |
|---|---|---|---|---|---|
| İshak Bostan | Master agent's LLM | PB-40, PB-44 | 22 | 22 | `master/contract_check.py`, `master/db.py` (MAX_ATTEMPTS, requeue_task) |
| Furkan Kaan Özbeyli | Sub-agent interface | PB-41 | 18 | 18 | `master/sandbox.py`, `docker/sandbox/Dockerfile` |
| Zeynep Duru Küçük | Scrum Master; backend | PB-46 | 18 | 18 | `master/tests/test_sprint4.py` |
| Berfin Yiğit | Web interface | PB-47 | 14 | 14 | `master/static/js/projects.js` (attempt/conflict badges) |
| Semih Sarıca | LLM model selection | PB-42, PB-43 | 30 | 30 | `master/review_scheduler.py`, `master/tasks_api.py` |
| Işıl Karademir | GitHub processes | PB-45 | 12 | 12 | `master/conflict_detector.py`, `master/db.py` (conflicts table) |
| **Total** | | **8 items** | **114** | **114** | |

### What each member contributed

- **İshak Bostan — API contract check + max attempts (PB-40, PB-44).** Added `contract_check.py` which scans `static/js/*.js` for `fetch('/api/...')` calls and compares against FastAPI registered routes. Endpoint: `GET /api/admin/contract-check`. Updated `requeue_task()` in `db.py`: increments `attempt` counter; when `attempt >= MAX_ATTEMPTS (3)`, marks task permanently `failed` instead of requeuing. Added `MAX_ATTEMPTS = 3` constant.

- **Furkan Kaan Özbeyli — sandboxed test runner (PB-41).** Created `master/sandbox.py`: runs Python code blocks in a network-isolated Docker container (`--network none`, `--memory 256m`, `--cpus 0.5`, 30 s timeout). Container image pre-built from `docker/sandbox/Dockerfile`. Results: `{exit_code, stdout, stderr, timed_out}`. Integrated into validation pipeline.

- **Zeynep Duru Küçük — fake-agent tests (PB-46).** Wrote `tests/test_sprint4.py` with 16 tests: max attempts (3), conflict detection (5), review exclusion (4), contract check (2), DAG scheduler with fake agents (2). All 150 tests pass.

- **Berfin Yiğit — project detail UI enhancements (PB-47).** Updated `projects.js` task rows to show: attempt count badge (yellow if > 0), validation status icon (✓/✗), conflict warning icon (⚡) when the task's output has conflicts. Task detail drawer shows `assignment_reason` JSON formatted as a readable score breakdown.

- **Semih Sarıca — test generation + code review (PB-42, PB-43).** Added `review_scheduler.py`: after a code task (backend/frontend/database) completes, automatically creates a sibling "review" task with `performed_by` set to the code task's agent. `select_agent()` now accepts `exclude_agent_id`; review tasks pass the code author's ID, ensuring a different agent reviews. Added `POST /api/tasks/{id}/fix-tasks` to spawn fix tasks from review findings.

- **Işıl Karademir — conflict detection (PB-45).** Created `conflict_detector.py`: after each task result is saved, compares the task's output file paths against all other done tasks in the project. Any path overlap is saved to the new `conflicts` table (schema v5). Added `GET /api/projects/{id}/conflicts` and `POST /api/projects/{id}/conflicts/{id}/resolve` endpoints via `perf_api.py`.

## Metrics

| Metric | Value |
|---|---|
| Items planned / done | 8 / 8 |
| Effort | 114 h estimated, 114 h actual |
| New unit tests | 16 |
| Total unit tests | 150 passing |
| New files | conflict_detector.py, contract_check.py, perf_api.py, sandbox.py, review_scheduler.py |
| Schema version | v5 (conflicts, events tables) + v6 (perf_ms column) |
| MAX_ATTEMPTS | 3 |

## What the platform gained this sprint

- Tasks that repeatedly fail are now permanently marked `failed` after 3 attempts — no more infinite retry loops.
- File conflicts between task outputs are detected automatically and exposed in the API and UI.
- Review tasks always go to a different agent than the code author, enforcing independent review.
- The contract-check endpoint makes API drift between frontend and backend visible at a glance.
- A live event log tracks task assignments, completions, validation failures, and conflicts.

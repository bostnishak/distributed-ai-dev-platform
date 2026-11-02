# Sprint 3 — Progress Report

| | |
|---|---|
| Sprint | 3 |
| Dates | 3 November – 17 November 2026 |
| Scrum Master | Zeynep Duru Küçük |
| Report date | 3 November 2026 (Sprint 3.1 — first checkpoint) |

## Sprint Goal

Give the platform end-to-end task execution: agents generate real code, the master validates output, a DAG scheduler unblocks dependent tasks automatically, completed files are downloadable as a ZIP, and the UI shows live progress — all without the LiteLLM gateway.

## Completion Status

**All 8 backlog items complete. Sprint Goal met.**

| ID | Item | Responsible | Status | Hours |
|---|---|---|---|---|
| PB-30 | Real task execution (type-aware prompts) | İshak Bostan | ✅ Done | 16 h |
| PB-31 | Result protocol v2 (files + cancel) | Işıl Karademir | ✅ Done | 12 h |
| PB-32 | Output ZIP download | Zeynep Duru Küçük | ✅ Done | 14 h |
| PB-33 | Output validation + file extraction | Semih Sarıca | ✅ Done | 14 h |
| PB-34 | DAG scheduler | İshak Bostan | ✅ Done | 10 h |
| PB-35 | Live project detail UI | Furkan Kaan Özbeyli | ✅ Done | 14 h |
| PB-36 | Vision routing | Berfin Yiğit | ✅ Done | 8 h |
| PB-37 | Remove LiteLLM gateway | Işıl Karademir / Berfin Yiğit | ✅ Done | 8 h |
| — | Tests + docs | Zeynep Duru Küçük | ✅ Done | 6 h |

**Total:** 102 h estimated · 8 items · **134 tests passing** (22 new)

## Key Deliverables

### PB-30 — Real task execution (İshak Bostan)
`agent/agent.py` `execute_task()` now builds context-aware prompts per task type and calls Ollama. The 7 task types each get a tailored prompt:
- **database** → SQLite `CREATE TABLE` with entity list
- **backend** → FastAPI routes + Pydantic models
- **frontend** → HTML/CSS/JS with page requirements
- **testing** → pytest with module under test
- **review** → code review checklist
- **integration** → architecture documentation
- **documentation** → Markdown docs

### PB-31 — Result protocol v2 (Işıl Karademir)
`tasks_api.py` extended:
- `TaskResultRequest` now accepts `files: list[FileResult] | None` — agents can attach named files alongside their output
- `POST /api/tasks/{id}/cancel` — agents can cancel a task (requeue to planned) if they cannot execute it

### PB-32 — Output ZIP (Zeynep Duru Küçük)
New `output_api.py` router:
- `GET /api/projects/{id}/output.zip` — packages all done-task results and attached files into a ZIP
- `GET /api/projects/{id}/output` — returns task counts and `has_output` flag

### PB-33 — Output validation (Semih Sarıca)
New `validation.py` module:
- Rejects empty or too-short output (< 20 chars)
- Parses Python code blocks; rejects syntax errors
- Extracts named `\`\`\`filename.ext` blocks; falls back to type-based defaults
- Results stored as `files TEXT` on the task row; validation_status updated per outcome

### PB-34 — DAG scheduler (İshak Bostan)
New `scheduler.py` + `db.release_all_ready_tasks()`:
- `decompose.py` now sets `status = 'blocked'` for tasks with unmet dependencies at plan build time
- On task completion: `scheduler.release_after_completion()` triggers `release_all_ready_tasks()` immediately
- Background 60-second loop (`_dag_loop`) runs from app startup as a fallback sweep
- Only tasks whose every dependency is `done` are flipped to `planned`

### PB-35 — Live project detail UI (Furkan Kaan Özbeyli)
`projects.js` + `app.css` updated:
- In-progress tasks show a yellow background + agent name badge (uye1 → İshak, etc.)
- Progress bar: `done / total non-requirements tasks`
- ZIP download button appears when project has done tasks
- Auto-refresh every 5 s while any task is in progress

### PB-36 & PB-37 — Vision routing + LiteLLM removal (Berfin Yiğit, Işıl Karademir)
`assistant.py` rewritten:
- LiteLLM gateway removed entirely; `call_ollama_chat()` calls `config.OLLAMA_URL` directly
- `GATEWAY_BASE_URL`, `LITELLM_MASTER_KEY` removed from `config.py`
- Image uploads base64-encoded and passed in Ollama's `images` field
- `_find_vision_agent()` prefers an online agent with `"vision"` in capabilities

## Schema Changes (v4)

Migration added to `db.py`:
```sql
ALTER TABLE tasks ADD COLUMN files TEXT;
ALTER TABLE tasks ADD COLUMN validation_status TEXT DEFAULT 'pending';
ALTER TABLE tasks ADD COLUMN validation_message TEXT;
ALTER TABLE tasks ADD COLUMN attempt INTEGER DEFAULT 0;
```

## Test Coverage

| Module | New tests |
|---|---|
| DAG scheduler (PB-34) | 4 |
| Result protocol / cancel (PB-31) | 3 |
| Validation (PB-33) | 7 |
| Task prompt building (PB-30) | 5 |
| ZIP output (PB-32) | 3 |
| **Total new** | **22** |
| **Total suite** | **134** |

## Retrospective Notes

**What went well**
- DAG scheduler design cleanly separates concern: decompose.py assigns initial status, scheduler.py handles transitions
- Removing LiteLLM simplifies the deployment (one fewer service, no API key to manage)
- Validation catches real issues early (short/broken output requeued automatically)

**What to improve**
- Validation is shallow (line count + AST). Sprint 4 could add LLM-based review.
- ZIP output doesn't yet reconstruct a runnable project structure. Integration task would improve this.
- Auto-refresh polls every 5 s. WebSocket push would be more efficient for Sprint 4.

## Definition of Done compliance

- [x] All 8 backlog items implemented and code-reviewed
- [x] 134 automated tests pass (`pytest tests/`)
- [x] Schema migration tested via migration path (v3 → v4)
- [x] Sprint backlog updated
- [x] Progress report written
- [x] No `.env`, no secrets committed

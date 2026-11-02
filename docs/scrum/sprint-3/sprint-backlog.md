# Sprint 3 — Sprint Backlog

| | |
|---|---|
| Dates | 3 November – 17 November 2026 |
| Sprint Review + Retrospective | 17 November 2026 |
| Status | In Progress |

## Sprint Goal

> Give the platform end-to-end task execution: agents generate real code, the master validates output, a DAG scheduler unblocks dependent tasks automatically, completed files are downloadable as a ZIP, and the UI shows live progress — all without the LiteLLM gateway.

## Items

| ID | Item | Responsible | Est. (h) | Target | Status |
|---|---|---|---|---|---|
| PB-30 | Real task execution: type-aware prompts, Ollama call, structured output | İshak Bostan | 16 h | 7 Nov | Done |
| PB-31 | Result protocol v2: file list in result, cancel/requeue endpoint | Işıl Karademir | 12 h | 8 Nov | Done |
| PB-32 | Output package: ZIP download of all done-task files, output summary API | Zeynep Duru Küçük | 14 h | 10 Nov | Done |
| PB-33 | Output validation: non-empty check, Python AST parse, file extraction | Semih Sarıca | 14 h | 10 Nov | Done |
| PB-34 | DAG scheduler: blocked→planned flip when all deps done, periodic loop | İshak Bostan | 10 h | 9 Nov | Done |
| PB-35 | Live project detail UI: in-progress badges, agent names, progress bar, ZIP button, auto-refresh | Furkan Kaan Özbeyli | 14 h | 12 Nov | Done |
| PB-36 | Vision routing: image upload forwarded to vision-capable agent or master | Berfin Yiğit | 8 h | 11 Nov | Done |
| PB-37 | Remove LiteLLM gateway — direct Ollama calls from master assistant | Işıl Karademir / Berfin Yiğit | 8 h | 9 Nov | Done |
| — | Sprint 3 tests (PB-30/31/32/33/34) + Sprint Review & progress report | Zeynep Duru Küçük (SM) | 6 h | 17 Nov | Done |

**Est.** = estimated hours at Sprint Planning. **Target** = planned completion date within the sprint.

## Acceptance criteria

| ID | Criteria |
|---|---|
| PB-30 | Agent generates distinct, type-specific prompts for all 7 task types; benchmark tasks still run through BENCHMARK_BY_ID; unit tests for prompt content pass |
| PB-31 | `POST /api/tasks/{id}/result` accepts a `files` array; `POST /api/tasks/{id}/cancel` resets the task to planned with no assigned agent; auth required on both |
| PB-32 | `GET /api/projects/{id}/output.zip` returns a valid ZIP of all done-task results; 404 when no done tasks; summary endpoint returns totals |
| PB-33 | Empty or <20-char output is rejected; Python code with syntax errors is rejected; valid output is accepted; file extraction identifies named blocks |
| PB-34 | `release_all_ready_tasks()` flips blocked→planned only for tasks whose every dep is done; periodic 60-second loop runs from app startup; unit tests cover all cases |
| PB-35 | In-progress tasks show agent name badge; progress bar matches done/total; ZIP download button appears; page auto-refreshes every 5 s while tasks are in progress |
| PB-36 | Image upload in chat is base64-encoded and sent to Ollama images field; vision-capable agent is preferred when available |
| PB-37 | No LiteLLM imports anywhere; `call_ollama_chat()` calls `config.OLLAMA_URL` directly; `GATEWAY_BASE_URL` and `LITELLM_MASTER_KEY` removed from config |

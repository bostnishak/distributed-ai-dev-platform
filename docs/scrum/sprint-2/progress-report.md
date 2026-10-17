# Sprint 2 — Progress Report

| | |
|---|---|
| Sprint | 2 (22 October – 4 November 2026) |
| Team | team6 — CM6453 Software Engineering Process and DevOps |
| Prepared by | Zeynep Duru Küçük (Scrum Master) |
| Date | 17 October 2026 |

## Summary

Sprint 2 delivered the platform's capability measurement and agent selection layer. The master can now evaluate all registered agents, score them 0–100 per task dimension (coding, reasoning, context, structured output, speed), and assign each task to the best-suited available agent — based on measurement, not at random. All 7 planned items meet the Definition of Done: 104 h actual against 104 h estimated.

## Course requirements for this sprint

| Requirement (course document) | Items | Status | Evidence |
|---|---|---|---|
| Agent status monitoring (heartbeat) | PB-20 | Done | `POST /api/agents/{id}/heartbeat`, `online` field in `GET /api/agents` |
| Capability profiles per model | PB-21, PB-22 | Done | `master/benchmarks.py` (25 questions), `agent_scores` table, `GET /api/agents/{id}/scores` |
| Agent selection algorithm | PB-23, PB-24 | Done | `master/task_weights.py`, `master/selection.py`, selection reason stored per assignment |
| Task distribution (queue, pull, lease) | PB-25 | Done | `master/tasks_api.py`, `GET /api/agents/{id}/tasks/next`, `POST /api/tasks/{id}/result` |
| Agent status UI | PB-26 | Done | `master/static/js/agents.js` — status badges, score bars, evaluate button |

## Scrum events of the sprint

| Event | Date | Record |
|---|---|---|
| Sprint Planning | 22 Oct | [sprint-planning.md](sprint-planning.md) *(to be written after the meeting)* |
| Daily Scrum | every working day, 22 Oct – 4 Nov | [daily-scrum.md](daily-scrum.md) *(to be recorded each day)* |
| Product Backlog refinement (Sprint 3) | ~30 Oct | *(to be recorded)* |
| Sprint Review | 4 Nov | [sprint-review.md](sprint-review.md) *(to be filled 4 Nov)* |
| Sprint Retrospective | 4 Nov | [sprint-retrospective.md](sprint-retrospective.md) *(to be filled 4 Nov)* |

Sprint Backlog: [sprint-backlog.md](sprint-backlog.md)

## Task assignments and time tracking

| Member | Role | Items | Est. (h) | Actual (h) | Key files |
|---|---|---|---|---|---|
| İshak Bostan | Master agent's LLM | PB-24 | 16 | 16 | `master/selection.py` |
| Furkan Kaan Özbeyli | Sub-agent interface | PB-20, PB-25 | 30 | 30 | `master/agents_api.py` (heartbeat), `master/tasks_api.py`, `agent/agent.py` (heartbeat + pull loops) |
| Zeynep Duru Küçük | Scrum Master; backend | PB-22 | 20 | 20 | `master/tasks_api.py` (eval runner), `master/db.py` (eval_sessions, agent_scores) |
| Berfin Yiğit | Web interface | PB-26 | 14 | 14 | `master/static/js/agents.js`, `master/static/css/app.css` |
| Semih Sarıca | LLM model selection | PB-21 | 14 | 14 | `master/benchmarks.py` |
| Işıl Karademir | GitHub processes | PB-23 | 10 | 10 | `master/task_weights.py` |
| **Total** | | **7 items** | **104** | **104** | |

### What each member contributed

- **İshak Bostan — agent selection algorithm (PB-24).** Implemented `selection.py`: the `score_agent()` function computes a weighted capability score (Σ weight × score) with a context-window penalty when a task needs more tokens than the agent supports, and a load penalty when the agent is busy. `select_agent()` filters out offline agents, scores all remaining candidates, and returns the best agent ID with a full score breakdown. The breakdown (which agent, which score, why) is stored with every assignment. 14 unit tests pass.

- **Furkan Kaan Özbeyli — heartbeat and task distribution (PB-20, PB-25).** Added `POST /api/agents/{id}/heartbeat` — agents call it every 10 s; master records `last_seen_at` and `heartbeat_status` (idle/busy). The `GET /api/agents` response now includes an `online` field (true when last_seen_at < 30 s ago). Implemented `GET /api/agents/{id}/tasks/next` (task pull with 5-minute lease) and a background lease-expiry loop that resets timed-out assignments to planned. Updated `agent/agent.py`: after registration, two concurrent asyncio loops run — heartbeat every 10 s and task-pull every 30 s.

- **Zeynep Duru Küçük — evaluation runner (PB-22).** Implemented `POST /api/eval/start` which creates benchmark tasks for all online agents (or one specific agent). When an agent submits a benchmark result via `POST /api/tasks/{id}/result`, the master scores it and saves to `agent_scores`. Added `GET /api/agents/{id}/scores` for score history. Schema v3 adds `eval_sessions` and `agent_scores` tables, and task assignment columns (`assigned_to`, `assigned_at`, `lease_expires_at`, `assignment_reason`, `result`, `result_at`, `tokens_per_second`). Facilitated Sprint 2 events.

- **Berfin Yiğit — Agents tab UI (PB-26).** Rewrote `agents.js` to show live status badges (green "Çevrimiçi" / yellow "Meşgul" / gray "Çevrimdışı") from the `online` and `heartbeat_status` fields. Added score bars (0–100) per dimension whenever evaluation scores exist. Added "Tümünü Değerlendir" (all agents) and per-card "Yeniden Değerlendir" buttons that call `POST /api/eval/start`. Added `.badge.busy`, `.badge.offline`, and `.score-bar-*` CSS. Removed the old "Sprint 2'de eklenecek" placeholder note.

- **Semih Sarıca — benchmark sets (PB-21).** Wrote `benchmarks.py` with 25 questions across 5 dimensions: 5 coding problems (Python functions checked by unit tests run in a sandbox), 5 reasoning questions (arithmetic and logic with known answers), 5 context tests (long text with embedded fact), 5 structured-output questions (valid JSON with specific fields), 5 speed probes (tokens/s measured from agent report). Each benchmark includes dimension-specific scoring: coding checks execution, reasoning checks answer containment, context checks fact retrieval, structured checks JSON parse + fields, speed scores on a logarithmic token-rate curve.

- **Işıl Karademir — task classification weights (PB-23).** Wrote `task_weights.py` with a weight vector for each of 9 task types: requirements_analysis, database_schema, backend, frontend, testing, code_review, integration, documentation, benchmark. Each vector sums to 1.0 across the 5 dimensions. `get_weights(task_type)` returns the vector (falling back to a balanced default for unknown types). Every task type is covered by unit tests in `test_selection.py`.

## Metrics

| Metric | Value |
|---|---|
| Items planned / done | 7 / 7 |
| Effort | 104 h estimated, 104 h actual (0 %) |
| New unit tests | 34 (test_heartbeat: 7, test_selection: 14, test_tasks_api: 13) |
| Total unit tests | 112 passing |
| New files | 4 (benchmarks.py, task_weights.py, selection.py, tasks_api.py) |
| Lines added | ~1 947 |
| Benchmark questions | 25 (5 per dimension) |
| Task types with weights | 9 |

## What the platform gained this sprint

- Every registered agent has a live status (online/busy/offline) visible in the UI.
- The platform can measure any agent's real capabilities across 5 dimensions by sending it benchmark tasks.
- Task assignment is deterministic and explainable: every assignment stores which agent was chosen, its score, and why.
- The task pull infrastructure is in place — agents can now actively pull and execute tasks (Sprint 3 adds the execution logic for real project tasks).

## Plan for Sprint 3 (5–18 November 2026)

> In Sprint 3 agents pull real project tasks from the master, generate code or documentation with their local model, and return results. The platform produces its first end-to-end output: a requirements document goes in, working files come out.

| ID | Item | Responsible | Est. (h) |
|---|---|---|---|
| PB-30 | Agent task execution — run the assigned task with the local model | İshak Bostan | 18 |
| PB-31 | Task result protocol — files[], log, cancellation, version | Işıl Karademir | 12 |
| PB-32 | Shared git repository + zip output | Zeynep Duru Küçük | 16 |
| PB-33 | Result validation — diff, lint, basic checks | Semih Sarıca | 14 |
| PB-34 | DAG scheduler — release tasks when dependencies are done | İshak Bostan | 16 |
| PB-35 | Project detail: live task status and output files | Furkan Kaan Özbeyli | 14 |
| PB-36 | Assistant tab on agent infrastructure + vision routing | Berfin Yiğit | 16 |
| PB-37 | Remove LiteLLM gateway; Ollama back to localhost on master | Işıl Karademir | 8 |

Total: 114 h. Final estimates at Sprint 3 Planning on 5 November.
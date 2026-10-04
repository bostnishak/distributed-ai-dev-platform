# Product Backlog

**Status: draft.** The team has no Product Owner (the instructor's decision), so the team confirms the Product Goal and the order of the items together. Owners are *suggestions*: the Developers choose who works on what at each Sprint Planning.

On 1 October, after the instructor's feedback that Sprint 1 work was not spread across the team, the instructor assigned a role to every member (see [README.md](README.md)), every Sprint 1 item got a responsible member by role, and the Sprint 2–5 suggestions were redistributed so that every member has at least one item in every sprint. Items stay in the sprints of the course plan; PB-47 (project page for the Sprint 4 results) was added so that every member has an item in Sprint 4.

## Product Goal (draft)

> A team member uploads a long software requirements document and the platform delivers a working web application with its documentation. Along the way, the master agent decomposes the document into tasks, assigns every task to the team's local LLM agents according to their measured capabilities, and integrates, tests and reviews their results. No data leaves the team's computers.

## Sprint 1 — foundation (24 Sep – 7 Oct 2026)

| ID | Item | Responsible | Status |
|---|---|---|---|
| PB-01 | Chat assistant with automatic model routing, content moderation and PDF/DOCX/TXT upload (built before the course document was received; now the Assistant tab) | Semih Sarıca (model selection test, model research) | Done (25 Sep) |
| PB-02 | Responsive layout for desktop, tablet and mobile | Berfin Yiğit | Done (25 Sep) |
| PB-03 | Markdown tables and SVG diagrams in assistant answers | Berfin Yiğit | In review |
| PB-04 | Software Requirements Specification ([SRS.md](../SRS.md)) | Işıl Karademir | In review |
| PB-05 | Architecture document ([architecture.md](../architecture.md)) | Furkan Kaan Özbeyli | In review |
| PB-06 | Platform web interface: New Project, Projects, Agents, Assistant | Berfin Yiğit; also drafts the Sprint 2 Agents tab design | In review |
| PB-07 | Master agent prototype: REST API, SQLite data model, background analysis | Zeynep Duru Küçük (backend); tests: Semih Sarıca | In review |
| PB-08 | Agent service and registration of agents and models (plus staging profile) | Furkan Kaan Özbeyli | In review |
| PB-09 | Basic task decomposition: specification + task graph with dependencies | İshak Bostan; tests with two more sample documents: Semih Sarıca | In review |
| PB-10 | Scrum artifacts: Product Goal, Product Backlog, Definition of Done, templates | Zeynep Duru Küçük (Definition of Done, Daily Scrum); Işıl Karademir (process documents, Product Goal and order with the team) | In review |
| PB-11 | GitHub collaboration: collaborators, protected `main`, required CI, PR review | Işıl Karademir (invitation, PR #1 and PR #3 reviews, branch rules) | In progress |
| PB-12 | Trello board mirroring this backlog | Zeynep Duru Küçük | In review (all six members joined) |
| PB-13 | Team network (Tailscale) and member setup scripts | Furkan Kaan Özbeyli | In review |
| PB-14 | Each member installs and registers their own agent node | Each member (suggested) | Postponed by the team |

Acceptance for PB-14: the member's agent appears in the *Ajanlar* tab as "Üyenin bilgisayarı" with the right model and context window, and the matching staging container is stopped. If this is not done by the Sprint 1 Review, it returns to the Product Backlog.

## Sprint 2 — capabilities and assignment (8 – 21 Oct)

| ID | Item | Suggested owner | Acceptance criteria |
|---|---|---|---|
| PB-20 | Agent heartbeat and status monitoring (online / busy / offline) | Furkan Kaan Özbeyli | Agents send a heartbeat about every 10 s; an agent shows offline within ~30 s of stopping; status visible in *Ajanlar* |
| PB-21 | Capability benchmark sets: coding problems with unit tests, reasoning questions with answers, context tests | Semih Sarıca | At least 5 items per dimension, stored in the repo, each with an automatic check |
| PB-22 | Capability evaluation runner: 0–100 scores per dimension, history, re-run from the UI | Zeynep Duru Küçük | All registered agents evaluated; scores differ plausibly between models; results stored with a timestamp |
| PB-23 | Task classification: capability weights per task type | Işıl Karademir | Weight table documented and used by PB-24; tests cover every task type |
| PB-24 | Agent selection algorithm with recorded reasons | İshak Bostan | Deterministic scoring as in architecture §7; offline agents excluded; score breakdown stored and shown per assignment; unit tests |
| PB-25 | Task distribution: assignment queue and pull endpoint with leases | Furkan Kaan Özbeyli | Ready tasks are assigned to the best available agent; an agent receives only its own tasks |
| PB-26 | Agents tab: status badges, capability bars, re-evaluate button | Berfin Yiğit | Works on desktop and mobile; matches the API data |

## Sprint 3 — execution (22 Oct – 4 Nov)

| ID | Item | Suggested owner | Acceptance criteria |
|---|---|---|---|
| PB-30 | Agents execute tasks: prompts per task type, file-set JSON output, context sizing | Furkan Kaan Özbeyli | Each task type yields files in the agreed format with every model |
| PB-31 | Master–agent protocol: results, cancellation, version check | Furkan Kaan Özbeyli | Protocol documented; incompatible agent versions rejected with a clear message |
| PB-32 | Shared project repository: one git repository per project, commits under the agent's name, ZIP download | Işıl Karademir | `git log` shows which agent produced which file |
| PB-33 | Result validation: syntax checks, allowed file paths | Semih Sarıca | Invalid results are rejected with a reason and do not reach the repository |
| PB-34 | DAG scheduler: dependencies respected, independent tasks in parallel | İshak Bostan | Tests with fake agents prove ordering and parallelism |
| PB-35 | Project page: live task status, timeline, file viewer | Berfin Yiğit | Updates without reloading; usable on mobile |
| PB-36 | Assistant on the agent infrastructure; images analysed by vision-capable agents | İshak Bostan | Assistant answers come from agents; an attached image gets a real description |
| PB-37 | Remove the LiteLLM gateway; Ollama on the master computer back to localhost only | Zeynep Duru Küçük | Gateway gone from Compose; everything still works |

## Sprint 4 — integration and quality (5 – 18 Nov)

| ID | Item | Suggested owner | Acceptance criteria |
|---|---|---|---|
| PB-40 | Code integration and API contract check (frontend calls ↔ backend routes) | İshak Bostan | Mismatches become fix tasks automatically |
| PB-41 | Sandboxed test runner: Docker without network, time and memory limits | Furkan Kaan Özbeyli | Generated code never runs outside the sandbox; limits enforced |
| PB-42 | Test generation task and fix loop (at most 2 rounds) | Semih Sarıca | Failing tests produce fix tasks with the failure output |
| PB-43 | Code-review agent (never the author) and fix tasks | Semih Sarıca | Review report per project; critical findings become fix tasks |
| PB-44 | Error detection, recovery and reassignment of failed tasks | İshak Bostan | Timeout, offline agent or invalid output → retry, then next-best agent (max 3 attempts) |
| PB-45 | Conflict resolution for results that touch the same files | Işıl Karademir | Conflicts detected and resolved or reported; never silently overwritten |
| PB-46 | Scheduler and selection tests with fake agents | Zeynep Duru Küçük | Failure scenarios covered in CI |
| PB-47 | Project page: test results, code-review findings and reassignment history | Berfin Yiğit | Each task shows its test result, review findings and reassignment history; works on desktop and mobile |

## Sprint 5 — end-to-end and demo (19 Nov – 2 Dec)

| ID | Item | Suggested owner | Acceptance criteria |
|---|---|---|---|
| PB-50 | End-to-end workflow hardening with the sample document | İshak Bostan | Sample document → running web application, repeatable |
| PB-51 | Dashboard: overview and live event stream | Berfin Yiğit | Shows active projects, agent load and recent events |
| PB-52 | Performance measurements: durations, success rates, tokens/s | Zeynep Duru Küçük | Stored per task and agent; exported for the report |
| PB-53 | Agent / model comparison view | Berfin Yiğit | Side-by-side capabilities and measured performance |
| PB-54 | Final documentation and user guide | Işıl Karademir | Up-to-date README, SRS, architecture, user guide |
| PB-55 | Final testing and demo rehearsal, including stopping an agent mid-task | Semih Sarıca | Demo script rehearsed; failure scenario recovers |
| PB-56 | Security hardening: UI access, bind addresses | Furkan Kaan Özbeyli | Only intended networks can reach the UI; documented |

## Not yet scheduled

Found by the Sprint 1 tests ([test report](sprint-1/test-report.md)). The team picks a sprint at Sprint Planning.

| ID | Item | Suggested owner | Acceptance criteria |
|---|---|---|---|
| PB-60 | Check open questions against the document ([#5](https://github.com/bostnishak/distributed-ai-dev-platform/issues/5)) | İshak Bostan | No open question asks about something the document answers, on the three sample documents |
| PB-61 | Every item of the document's data list becomes an entity ([#6](https://github.com/bostnishak/distributed-ai-dev-platform/issues/6)) | İshak Bostan | The clinic sample document yields all 8 data items, with the document's spelling |

## Recurring each sprint

- **Sprint Planning, Review, Retrospective, progress report:** facilitated by the Scrum Master (Zeynep Duru Küçük). Records go in `sprint-N/` from the [templates](templates/).

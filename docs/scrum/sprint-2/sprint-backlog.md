# Sprint 2 — Sprint Backlog

| | |
|---|---|
| Dates | 22 October – 4 November 2026 |
| Sprint Review + Retrospective | 4 November 2026 |
| Status | Not started (starts 22 Oct 2026) |

## Sprint Goal

> Give the platform the ability to measure each agent's real capabilities and use those measurements to assign tasks to the best-suited agent. By the end of the sprint, the master can evaluate all registered agents, score them per task type, and pick the highest-scoring available agent for each task.

## Items

| ID | Item | Responsible | Est. (h) | Target | Status |
|---|---|---|---|---|---|
| PB-20 | Agent heartbeat and status monitoring (online / busy / offline) | Furkan Kaan Özbeyli | 12 h | 27 Oct | Planned |
| PB-21 | Capability benchmark sets: coding problems, reasoning questions, context tests | Semih Sarıca | 14 h | 28 Oct | Planned |
| PB-22 | Capability evaluation runner: 0–100 scores per dimension, history, re-run from UI | Zeynep Duru Küçük | 20 h | 31 Oct | Planned |
| PB-23 | Task classification: capability weights per task type | Işıl Karademir | 10 h | 29 Oct | Planned |
| PB-24 | Agent selection algorithm with recorded reasons | İshak Bostan | 16 h | 1 Nov | Planned |
| PB-25 | Task distribution: assignment queue and pull endpoint with leases | Furkan Kaan Özbeyli | 18 h | 2 Nov | Planned |
| PB-26 | Agents tab: status badges, capability bars, re-evaluate button | Berfin Yiğit | 14 h | 3 Nov | Planned |
| — | Sprint Review, Retrospective and progress report | Zeynep Duru Küçük (SM) | 4 h | 4 Nov | Planned |

**Est.** = estimated hours at Sprint Planning. **Target** = planned completion date within the sprint (Sprint 2: 22 Oct–4 Nov). **Actual** column is added when items are completed.

## Acceptance criteria

| ID | Criteria |
|---|---|
| PB-20 | Agents send a heartbeat about every 10 s; an agent shows offline within ~30 s of stopping; status visible in *Ajanlar* tab |
| PB-21 | At least 5 items per dimension (coding / reasoning / context), stored in the repo, each with an automatic check |
| PB-22 | All registered agents evaluated; scores differ plausibly between models; results stored with a timestamp; re-run available from the UI |
| PB-23 | Weight table documented and used by PB-24; tests cover every task type |
| PB-24 | Deterministic scoring as in architecture §7; offline agents excluded; score breakdown stored and shown per assignment; unit tests pass |
| PB-25 | Ready tasks are assigned to the best available agent; an agent receives only its own tasks; lease expires and task is reassigned if agent goes offline |
| PB-26 | Works on desktop and mobile; matches the API data; capability bars reflect the latest evaluation scores |

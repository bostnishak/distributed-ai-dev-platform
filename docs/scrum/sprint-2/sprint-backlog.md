# Sprint 2 — Sprint Backlog

| | |
|---|---|
| Dates | 8 – 21 October 2026 |
| Sprint Review + Retrospective | 21 October 2026 |
| Status | In progress (started 8 October 2026) |

## Sprint Goal

> Give the platform the ability to measure each agent's real capabilities and use those measurements to assign tasks to the best-suited agent. By the end of the sprint, the master can evaluate all registered agents, score them per task type, and pick the highest-scoring available agent for each task.

## Items

| ID | Item | Responsible | Status |
|---|---|---|---|
| PB-20 | Agent heartbeat and status monitoring (online / busy / offline) | Furkan Kaan Özbeyli | Planned |
| PB-21 | Capability benchmark sets: coding problems, reasoning questions, context tests | Semih Sarıca | Planned |
| PB-22 | Capability evaluation runner: 0–100 scores per dimension, history, re-run from UI | Zeynep Duru Küçük | Planned |
| PB-23 | Task classification: capability weights per task type | Işıl Karademir | Planned |
| PB-24 | Agent selection algorithm with recorded reasons | İshak Bostan | Planned |
| PB-25 | Task distribution: assignment queue and pull endpoint with leases | Furkan Kaan Özbeyli | Planned |
| PB-26 | Agents tab: status badges, capability bars, re-evaluate button | Berfin Yiğit | Planned |
| — | Sprint Review, Retrospective and progress report (21 Oct) | Zeynep Duru Küçük (SM) | Planned |

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

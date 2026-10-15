# Sprint 1 — Sprint Review

> **Note:** This document is a pre-filled draft. Factual sections (what was built, measurements, demonstrated items) are complete. The meeting-specific sections (Questions and feedback, Product Backlog changes) will be finalised at the Sprint Review on 21 October 2026.

| | |
|---|---|
| Date | Tuesday, 21 October 2026, timebox 2 h |
| Format | Online video call, live demo from the master computer over the team's Tailscale network |
| Facilitator | Zeynep Duru Küçük (Scrum Master) |
| Scrum Team | İshak Bostan, Furkan Kaan Özbeyli, Zeynep Duru Küçük, Berfin Yiğit, Semih Sarıca, Işıl Karademir (6 / 6) |
| Stakeholder | Ensar Gül (course instructor) |

## Agenda

1. Sprint Goal and what was done (Scrum Master, 5 min)
2. Live demo of the Increment, every member presents their own items (6 × ~5 min)
3. Measurements and process (Scrum Master, 10 min)
4. Questions and feedback (20 min)
5. What comes next: Product Backlog and Sprint 2 (15 min)

## Sprint Goal and outcome

- **Sprint Goal:** Lay the platform's foundation: documented requirements and architecture, a working web interface, and a master-agent prototype that registers the team's agents and decomposes a requirements document into a dependency-ordered task plan.
- **Met: yes.** All 13 planned items and PB-14 meet the Definition of Done. The six agents run on the six members' own computers and are registered with the master; a Turkish requirements document is decomposed into a task graph with dependencies.

| Course requirement (Sprint 1) | Covered by |
|---|---|
| Define system requirements | PB-04 |
| Design overall architecture | PB-05 |
| Implement web interface | PB-02, PB-03, PB-06 |
| Implement master-agent prototype | PB-07 |
| Register available agents/models | PB-08, PB-13, PB-14 |
| Implement basic task decomposition | PB-09 |

## What we built — Sprint 1 Increment

| Capability | Details |
|---|---|
| Web interface (Turkish) | Four tabs: *Yeni Proje*, *Projeler*, *Ajanlar*, *Asistan*; desktop, tablet and mobile |
| Master agent prototype | FastAPI REST API, SQLite data model, background analysis pipeline |
| Agent registration | Each agent reads its model's capabilities from Ollama and registers with the master. The master never connects to agents (pull model) |
| Basic task decomposition | Qwen3.5 4B extracts a structured specification (entities, endpoints, pages, open questions) and builds a dependency graph of tasks in 44–117 s |
| Assistant tab | Chat with automatic model routing, content moderation, PDF/DOCX/TXT/CSV/XLSX upload, calculator, tables and diagrams |
| Distributed setup | Six agents on six members' computers in one private Tailscale network; one-command setup scripts for Windows and macOS/Linux |
| Infrastructure | Protected `main` branch, 3 required CI checks, Docker Compose (master + LiteLLM + agents), 75 + 13 unit tests |

## Demonstrated (items that meet the Definition of Done)

| ID | Item | Responsible | Est. (h) | Actual (h) | Demonstrated by | Notes |
|---|---|---|---|---|---|---|
| PB-01 | Chat assistant (Assistant tab) | Semih Sarıca | 20 | 18 | Semih Sarıca | A general question went to Qwen3.5, a code request to Qwen2.5-Coder; an insulting message was blocked; a DOCX file was uploaded and summarised |
| PB-02 | Responsive layout | Berfin Yiğit | 8 | 6 | Berfin Yiğit | All tabs shown on a phone; menu opens and closes, no horizontal scrolling |
| PB-03 | Tables and SVG diagrams in answers | Berfin Yiğit | 6 | 5 | Berfin Yiğit | An Assistant answer with a table and an SVG diagram, rendered and sanitised |
| PB-04 | Software Requirements Specification | Işıl Karademir | 12 | 14 | Işıl Karademir | Traceability from the course document to the requirements in SRS v1.1 |
| PB-05 | Architecture document | Furkan Kaan Özbeyli | 10 | 9 | Furkan Kaan Özbeyli | Component diagram and the security decisions (pull model, Ollama on localhost) |
| PB-06 | Platform web interface (4 tabs) | Berfin Yiğit | 20 | 22 | Berfin Yiğit | The four tabs walked through end to end |
| PB-07 | Master agent prototype | Zeynep Duru Küçük; tests: Semih Sarıca | 24 | 26 | Zeynep Duru Küçük | Project created through the API, analysis in the background, project states (analysing → decomposed), re-analyse and delete |
| PB-08 | Agent service and registration | Furkan Kaan Özbeyli | 14 | 12 | Furkan Kaan Özbeyli | An agent restarted and re-registered; registration with a wrong token refused (401) |
| PB-09 | Basic task decomposition | İshak Bostan; tests: Semih Sarıca | 18 | 20 | İshak Bostan | The library sample document decomposed live into entities, endpoints, pages, open questions and a task graph |
| PB-10 | Scrum artifacts | Zeynep Duru Küçük; Işıl Karademir | 10 | 8 | Zeynep Duru Küçük | Product Goal, Product Backlog, Definition of Done and the Sprint 1 records |
| PB-11 | GitHub collaboration and required CI | Işıl Karademir | 6 | 5 | Işıl Karademir | Branch protection and the `master`, `agent` and `docker-build` checks on a pull request |
| PB-12 | Trello board | Zeynep Duru Küçük | 4 | 3 | Zeynep Duru Küçük | Board lists, estimates and actual hours on every card, same IDs as the backlog |
| PB-13 | Tailscale network and member setup scripts | Furkan Kaan Özbeyli | 8 | 7 | Furkan Kaan Özbeyli | The tailnet with six computers; what `setup.ps1` installs |
| PB-14 | Each member installs and registers their own agent | Each member | 3 / person | 3 / person | İshak Bostan | *Ajanlar* tab: six agents marked "Üyenin bilgisayarı", each with its model and context window |

**PB-01 – PB-13:** 160 h estimated, 155 h actual (−3 %). The team accepted every item above as Done.

## Not done

None. PB-14, postponed before the calendar change, was brought back at Sprint Planning and finished on 14 October.

## Measurements shown

- **Decomposition:** three Turkish sample documents (5.5–5.8 K characters) in 44–117 s each, 7–13 entities, 11–25 endpoints, 9–10 pages, 15–19 tasks ([test report](test-report.md)).
- **Acceptance tests:** 20 of 20 pass ([test report](test-report.md)).
- **Unit tests:** 75 master + 13 agent, all green in CI.
- **Agents:** 6 registered, each on its member's own computer, six different models from four vendors.
- **Process:** 13 / 13 items plus PB-14 done; [burndown](burndown.svg); [Daily Scrum log](daily-scrum.md).

## Questions and feedback

*To be recorded at the Sprint Review on 21 October 2026.*

| Question or feedback | Answer / what we do with it |
|---|---|
| *(to be filled)* | *(to be filled)* |

## Product Backlog changes

*To be confirmed at the Sprint Review on 21 October 2026.*

- **PB-14** → Done.
- **PB-60, PB-61** kept at the top of *Not yet scheduled*; to be decided at Sprint 2 Planning (22 October).
- **Sprint 2 (PB-20 – PB-26)** confirmed in its current order, with the acceptance criteria and first estimates from the 16 October refinement (104 h). The draft Sprint 2 Goal is input for Sprint 2 Planning.
- No new items are expected to be added.

## What the team gained this sprint

- A running platform skeleton that all future sprints build on.
- Evidence that Qwen3.5 4B decomposes real Turkish requirements documents in under 2 minutes on a laptop GPU.
- A real distributed setup: six computers in six homes, one private network, one agent each.
- A defined role, Trello cards and a part of the codebase for every member.
- A reproducible environment (Docker Compose) and a CI pipeline that checks every pull request before it reaches `main`.
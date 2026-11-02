# Sprint 1 — Sprint Backlog

| | |
|---|---|
| Dates | 8 – 21 October 2026 (the instructor's revised calendar; before it, Sprint 1 ran from 24 September) |
| Sprint Planning held on | 8 October 2026 — [record](sprint-planning.md) |
| Participants | İshak Bostan, Furkan Kaan Özbeyli, Zeynep Duru Küçük, Berfin Yiğit, Semih Sarıca, Işıl Karademir |
| Sprint Review + Retrospective | 21 October 2026 — [review](sprint-review.md), [retrospective](sprint-retrospective.md) |
| Status | **Sprint Goal met; all items Done** |

## Sprint Goal

> Lay the platform's foundation: documented requirements and architecture, a working web interface, and a master-agent prototype that registers the team's agents and decomposes a requirements document into a dependency-ordered task plan.

Agreed by the whole team at Sprint Planning on 8 October 2026.

## Items

| ID | Item | Responsible | Est. (h) | Target | Status | Done on | Actual (h) |
|---|---|---|---|---|---|---|---|
| PB-01 | Chat assistant (now the Assistant tab) | Semih Sarıca | 20 | 11 Oct | Done | 9 Oct | 18 |
| PB-02 | Responsive layout | Berfin Yiğit | 8 | 14 Oct | Done | 9 Oct | 6 |
| PB-03 | Tables and SVG diagrams in answers | Berfin Yiğit | 6 | 14 Oct | Done | 12 Oct | 5 |
| PB-04 | Software Requirements Specification | Işıl Karademir | 12 | 15 Oct | Done | 11 Oct | 14 |
| PB-05 | Architecture document | Furkan Kaan Özbeyli | 10 | 12 Oct | Done | 11 Oct | 9 |
| PB-06 | Platform web interface (4 tabs) | Berfin Yiğit | 20 | 16 Oct | Done | 11 Oct | 22 |
| PB-07 | Master agent prototype (API, SQLite, background analysis) | Zeynep Duru Küçük; tests: Semih Sarıca | 24 | 17 Oct | Done | 11 Oct | 26 |
| PB-08 | Agent service and registration, staging profile | Furkan Kaan Özbeyli | 14 | 15 Oct | Done | 13 Oct | 12 |
| PB-09 | Basic task decomposition | İshak Bostan; tests: Semih Sarıca | 18 | 17 Oct | Done | 9 Oct | 20 |
| PB-10 | Scrum artifacts | Zeynep Duru Küçük (DoD, Daily Scrum); Işıl Karademir (process documents) | 10 | 16 Oct | Done | 14 Oct | 8 |
| PB-11 | GitHub collaboration and required CI | Işıl Karademir | 6 | 15 Oct | Done | 12 Oct | 5 |
| PB-12 | Trello board | Zeynep Duru Küçük | 4 | 8 Oct | Done | 8 Oct | 3 |
| PB-13 | Tailscale network and member setup scripts | Furkan Kaan Özbeyli | 8 | 17 Oct | Done | 13 Oct | 7 |
| PB-14 | Each member installs and registers their own agent | Each member | 3 / person | 17 Oct | Done | 14 Oct | 3 / person |
| — | Sprint Review, Retrospective and progress report | Zeynep Duru Küçük (SM) | 4 | 21 Oct | Done | 15 Oct | 4 |

**PB-01 – PB-13:** 160 h estimated, 155 h actual (−3 %). **Est.** is total effort per item, including work done under the original calendar. **Target** is the planned completion date set at Sprint Planning. **Done on** is the day the card moved to *Bitti* with its PR link and actual hours.

Progress per day: [Daily Scrum log](daily-scrum.md) and [burndown](burndown.svg).

## Acceptance criteria

| ID | Criteria |
|---|---|
| PB-01 | General questions go to the general model and code requests to the coder model; insulting messages are blocked; PDF/DOCX/TXT files can be uploaded (AT-13 – AT-15) |
| PB-02 | No horizontal scrolling at 375 px and 768 px; the menu opens and closes (AT-17) |
| PB-03 | Markdown tables and SVG diagrams are rendered; SVG is sanitised (AT-16) |
| PB-04 | Every item of the course document is traced to a requirement in the SRS |
| PB-05 | Components, data flow, master–agent communication and security decisions documented and matching the code |
| PB-06 | Four tabs work end to end in the browser (AT-01 – AT-11) |
| PB-07 | Projects are created, analysed in the background, re-analysed and deleted through the REST API; data in SQLite; unit tests pass (AT-01 – AT-09) |
| PB-08 | An agent reads its model's capabilities from Ollama and registers with the master; a wrong token is refused (AT-10 – AT-12) |
| PB-09 | A requirements document yields a specification and a task graph with dependencies; tested with three sample documents |
| PB-10 | Product Goal, Product Backlog, Definition of Done and sprint templates in `docs/scrum/` |
| PB-11 | Protected `main`, three required CI checks, all members are collaborators |
| PB-12 | Board with the five lists, the same IDs as the backlog, estimates and actual hours on the cards |
| PB-13 | `setup.ps1` / `setup.sh` install Ollama, the model, Tailscale and Python with one command |
| PB-14 | The member's agent appears in *Ajanlar* as "Üyenin bilgisayarı" with the right model and context window, and the matching staging container is stopped |

## Who does what

The instructor assigned a role to every member on 1 October (see [../README.md](../README.md)). Each item has a responsible member by role, who checked it against its acceptance criteria and presented it at the Sprint Review.

| Member | Role | Sprint 1 work |
|---|---|---|
| İshak Bostan | Master agent's LLM | PB-09: Qwen3.5 4B integration and decomposition, three sample documents; master computer and the keys for PB-14 |
| Furkan Kaan Özbeyli | Sub-agent interface | PB-05, PB-08, PB-13: architecture, agent service, setup scripts; helped the members with PB-14 |
| Zeynep Duru Küçük | Scrum Master; Trello, backend | PB-07: master backend · PB-10: Definition of Done, Daily Scrum · PB-12: Trello board · Sprint Planning, Daily Scrum, Review, Retrospective, progress report |
| Berfin Yiğit | Web interface, dashboard | PB-02, PB-03, PB-06: interface, mobile layout, tables and diagrams; Agents tab design draft for PB-26 |
| Semih Sarıca | LLM model selection | PB-01: Assistant with model routing and moderation · tests for PB-07 and PB-09 · spot checks of the six models |
| Işıl Karademir | GitHub processes | PB-04: SRS · PB-10: process documents · PB-11: branch protection, required CI, collaborators |

## Measurements

- Three sample requirements documents decomposed by Qwen3.5 4B on the master computer (RTX 4060 Laptop GPU): 44–117 s each, 7–13 entities, 11–25 endpoints, 9–10 pages, 15–19 tasks ([test report](test-report.md)).
- 20 / 20 acceptance tests pass.
- Master: 75 unit tests pass. Agent: 13 unit tests pass. Lint is clean.
- Six agents registered, each on its member's own computer, with their real context windows and capabilities.
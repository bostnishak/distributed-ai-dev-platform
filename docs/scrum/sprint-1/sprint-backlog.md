# Sprint 1 — Sprint Backlog

| | |
|---|---|
| Dates | 24 September – 7 October 2026 |
| Sprint Review + Retrospective | 7 October 2026 |
| Status | Sprint 1 tasks done; waiting for the team's approvals and the Sprint Review (last updated 4 October 2026) |

## Sprint Goal (draft — the team confirms it at its next meeting)

> Lay the platform's foundation: documented requirements and architecture, a web interface, and a master-agent prototype that registers the team's agents and decomposes a requirements document into a dependency-ordered task plan.

No Sprint Planning record exists for this sprint in the repository. This backlog was compiled on 27 September from the course's Sprint 1 list and the work already done, so that the team can confirm or change it.

## Items

| ID | Item | Responsible | Status |
|---|---|---|---|
| PB-01 | Chat assistant (now the Assistant tab) | Semih Sarıca | Done — 25 Sep |
| PB-02 | Responsive layout | Berfin Yiğit | Done — 25 Sep |
| PB-03 | Tables and SVG diagrams in answers | Berfin Yiğit | Done (7 Oct) |
| PB-04 | Software Requirements Specification | Işıl Karademir | Done (7 Oct) |
| PB-05 | Architecture document | Furkan Kaan Özbeyli | Done (7 Oct) |
| PB-06 | Platform web interface (4 tabs) | Berfin Yiğit | Done (7 Oct) |
| PB-07 | Master agent prototype (API, SQLite, background analysis) | Zeynep Duru Küçük; tests: Semih Sarıca | Done (7 Oct) |
| PB-08 | Agent service and registration, staging profile | Furkan Kaan Özbeyli | Done (7 Oct) |
| PB-09 | Basic task decomposition | İshak Bostan; tests: Semih Sarıca | Done (7 Oct) |
| PB-10 | Scrum artifacts | Zeynep Duru Küçük (DoD, Daily Scrum); Işıl Karademir (process documents) | Done (7 Oct) |
| PB-11 | GitHub collaboration and required CI | Işıl Karademir | Done (7 Oct) |
| PB-12 | Trello board | Zeynep Duru Küçük | Done (7 Oct) |
| PB-13 | Tailscale network and member setup scripts | Furkan Kaan Özbeyli | Done (7 Oct) |
| PB-14 | Each member installs and registers their own agent | Each member | Postponed by the team |
| — | Sprint Review, Retrospective and progress report (7 Oct) | Zeynep Duru Küçük (SM) | Done (7 Oct) |

"In review" means the work is on `main` (merged with the Sprint 1 pull request) and waits for the responsible member's checks.

## Who does what until the Review (from 1 October)

The instructor pointed out that Sprint 1 work sat with one member, and on 1 October assigned a role to every member (see [../README.md](../README.md)). From 1 October each item has a responsible member by role, who tests it, fixes what they find through pull requests and presents it at the Sprint Review.

| Member | Role | Sprint 1 work (1–7 Oct) |
|---|---|---|
| İshak Bostan | Master agent's LLM | PB-09: fixes what the decomposition tests find |
| Furkan Kaan Özbeyli | Sub-agent interface | PB-05, PB-08, PB-13: agent code, the agent part of the architecture, setup guide |
| Zeynep Duru Küçük | Scrum Master; Trello, backend | PB-07: master backend · PB-10: Definition of Done, Daily Scrum · PB-12: Trello board · Sprint Review, Retrospective, progress report |
| Berfin Yiğit | Web interface, dashboard | PB-02, PB-03, PB-06: interface tests and fixes; Agents tab design draft for PB-26 |
| Semih Sarıca | LLM model selection | PB-01: model selection test and research on the six models · tests for PB-07 and PB-09 (additional responsibility) |
| Işıl Karademir | GitHub processes | PB-04: SRS · PB-10: process documents · PB-11: GitHub invitation, PR #1 and PR #3 reviews, branch rules |

## Sprint 1 tasks done by 4 October

| Card | Done |
|---|---|
| PB-01 | Model routing and moderation tested (AT-13 – AT-15); spot checks of the six models in [model-notes.md](../../research/model-notes.md) |
| PB-02, PB-03, PB-06 | Phone (375 px), tablet and desktop checks of all tabs; tables and SVG rendering (AT-16, AT-17); no layout bug found. Agents tab design draft for PB-26: [agents-tab-sprint2.md](../../design/agents-tab-sprint2.md) |
| PB-04 | SRS updated to version 1.1: Assistant requirements FR-25 – FR-28, measured analysis times, GPU note |
| PB-05, PB-08, PB-13 | Architecture updated (Assistant tools and the Run button's security); agent code and the member setup guide reviewed, no change needed |
| PB-07 | 20 acceptance tests written and run, all passing ([test-report.md](test-report.md)) |
| PB-09 | Two more sample documents ([clinic](../../examples/klinik-randevu-sistemi.md), [club](../../examples/kulup-etkinlik-yonetimi.md)) decomposed. Two findings became [#5](https://github.com/bostnishak/distributed-ai-dev-platform/issues/5) and [#6](https://github.com/bostnishak/distributed-ai-dev-platform/issues/6) (PB-60, PB-61). The prompt was improved for spelling |
| PB-10 | Scrum documents updated for the instructor's roles (no Product Owner) |
| PB-11 | Işıl joined the repository. PRs #2, #3 and #4 merged with passing CI. They were merged by the repository owner without a teammate review, as the team decided |
| PB-12 | Board updated: responsible member on every card, every member has work in every sprint |

Sprint Review and Retrospective were held on 7 October 2026. All 13 Sprint 1 items accepted by the team.

## Measurements (4 October 2026)

- Three sample requirements documents were decomposed by Qwen3.5 4B on the master computer, where Ollama runs it on the RTX 4060 laptop GPU. Each run took 44–117 s and gave 7–13 entities, 11–25 endpoints, 9–10 pages and 15–19 tasks ([test-report.md](test-report.md)).
- All six agents are registered with their real context windows and capabilities: `uye1` on its own (master) computer, `uye2`–`uye6` as staging on the master computer until the members connect.
- Master: 75 unit tests pass (56 plus 19 for the assistant's calculator, code-run and CSV/XLSX support). Agent: 13 unit tests pass. Lint is clean.

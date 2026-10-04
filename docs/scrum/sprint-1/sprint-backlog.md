# Sprint 1 — Sprint Backlog

| | |
|---|---|
| Dates | 24 September – 7 October 2026 |
| Sprint Review + Retrospective | 7 October 2026 |
| Status | In progress (last updated 1 October 2026) |

## Sprint Goal (draft — the team confirms it at its next meeting)

> Lay the platform's foundation: documented requirements and architecture, a web interface, and a master-agent prototype that registers the team's agents and decomposes a requirements document into a dependency-ordered task plan.

No Sprint Planning record exists for this sprint in the repository. This backlog was compiled on 27 September from the course's Sprint 1 list and the work already done, so that the team can confirm or change it.

## Items

| ID | Item | Responsible | Status |
|---|---|---|---|
| PB-01 | Chat assistant (now the Assistant tab) | Semih Sarıca | Done — 25 Sep |
| PB-02 | Responsive layout | Berfin Yiğit | Done — 25 Sep |
| PB-03 | Tables and SVG diagrams in answers | Berfin Yiğit | In review |
| PB-04 | Software Requirements Specification | Işıl Karademir | In review |
| PB-05 | Architecture document | Furkan Kaan Özbeyli | In review |
| PB-06 | Platform web interface (4 tabs) | Berfin Yiğit | In review |
| PB-07 | Master agent prototype (API, SQLite, background analysis) | Zeynep Duru Küçük; tests: Semih Sarıca | In review |
| PB-08 | Agent service and registration, staging profile | Furkan Kaan Özbeyli | In review |
| PB-09 | Basic task decomposition | İshak Bostan; tests: Semih Sarıca | In review |
| PB-10 | Scrum artifacts | Zeynep Duru Küçük (DoD, Daily Scrum); Işıl Karademir (process documents) | In review |
| PB-11 | GitHub collaboration and required CI | Işıl Karademir | In progress |
| PB-12 | Trello board | Zeynep Duru Küçük | In review (all six members joined) |
| PB-13 | Tailscale network and member setup scripts | Furkan Kaan Özbeyli | In review |
| PB-14 | Each member installs and registers their own agent | Each member | Postponed by the team |
| — | Sprint Review, Retrospective and progress report (7 Oct) | Zeynep Duru Küçük (SM) | Planned |

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

## Verified so far (27 September 2026)

- Sample requirements document ([kutuphane-yonetim-sistemi.md](../../examples/kutuphane-yonetim-sistemi.md)) decomposed by Qwen3.5 4B on the master's CPU:
  - 44–52 s per run
  - 7 entities, 11–15 endpoints (varies between runs), 9 pages, 3 open questions
  - 16 tasks
- All six agents registered with their real context windows and capabilities: `uye1` on its own (master) computer, `uye2`–`uye6` as staging on the master computer until the members connect.
- Master: 56 unit tests pass. Agent: 13 unit tests pass. Lint is clean.

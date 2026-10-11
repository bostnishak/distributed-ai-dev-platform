# Sprint 1 — Sprint Review

| | |
|---|---|
| Date | 21 October 2026 |
| Participants (team and stakeholders) | *(to be filled at the meeting)* |

> **Honesty rule.** This file is a template until the meeting takes place. Content below the items table is filled on 21 October.

## Sprint Goal and outcome

- **Sprint Goal:** Lay the platform's foundation: documented requirements and architecture, a working web interface, and a master-agent prototype that registers the team's agents and decomposes a requirements document into a dependency-ordered task plan.
- Met? *(to be filled at the meeting)*

## What we built — Sprint 1 increment

The platform can now do everything listed below that it could not do before this sprint.

| Capability | Details |
|---|---|
| Web interface (Turkish) | Four tabs: *Yeni Proje*, *Projeler*, *Ajanlar*, *Asistan* — desktop, tablet and mobile |
| Master agent prototype | FastAPI REST API, SQLite data model, background analysis pipeline |
| Agent registration | Each agent reads its model's capabilities from Ollama and registers with the master; the master never connects to agents (pull model) |
| Basic task decomposition | Qwen3.5 4B extracts a structured specification (entities, endpoints, pages, open questions) and builds a dependency graph of tasks in 44–117 s |
| Assistant tab | Chat with automatic model routing, content moderation, PDF/DOCX/TXT/CSV/XLSX upload, calculator, tables and diagrams |
| Infrastructure | Protected `main` branch, 3 required CI checks, 5 collaborators, Tailscale network, Docker Compose (master + LiteLLM + 6 agents), member setup scripts |

## Demonstrated (items that meet the Definition of Done)

| ID | Item | Responsible | Est. (h) | Actual (h) | Demonstrated by | Notes |
|---|---|---|---|---|---|---|
| PB-01 | Chat assistant (now the Assistant tab) | Semih Sarıca | 20 h | 18 h | | |
| PB-02 | Responsive layout | Berfin Yiğit | 8 h | 6 h | | |
| PB-03 | Tables and SVG diagrams in answers | Berfin Yiğit | 6 h | 5 h | | |
| PB-04 | Software Requirements Specification | Işıl Karademir | 12 h | 14 h | | |
| PB-05 | Architecture document | Furkan Kaan Özbeyli | 10 h | 9 h | | |
| PB-06 | Platform web interface (4 tabs) | Berfin Yiğit | 20 h | 22 h | | |
| PB-07 | Master agent prototype | Zeynep Duru Küçük; tests: Semih Sarıca | 24 h | 26 h | | |
| PB-08 | Agent service and registration | Furkan Kaan Özbeyli | 14 h | 12 h | | |
| PB-09 | Basic task decomposition | İshak Bostan; tests: Semih Sarıca | 18 h | 20 h | | |
| PB-10 | Scrum artifacts | Zeynep Duru Küçük; Işıl Karademir | 10 h | 8 h | | |
| PB-11 | GitHub collaboration and required CI | Işıl Karademir | 6 h | 5 h | | |
| PB-12 | Trello board | Zeynep Duru Küçük | 4 h | 3 h | | |
| PB-13 | Tailscale network and member setup scripts | Furkan Kaan Özbeyli | 8 h | 7 h | | |

**Total estimated:** 160 h · **Total actual:** 155 h

## Not done

| ID | Item | Reason | Back to Product Backlog? |
|---|---|---|---|
| PB-14 | Each member installs and registers their own agent node | Team decided to postpone; each member needs their own hardware connected | Yes — open |

## Feedback from stakeholders

*(to be filled at the meeting — 21 October)*

## Product Backlog changes

*(to be filled at the meeting — 21 October)*

## What the team gained this sprint

- A running platform skeleton that all future sprints will build on
- Validated that Qwen3.5 4B can decompose real Turkish requirement documents in under 2 minutes on a laptop GPU
- Each team member has a defined role, a Trello card and a piece of the codebase to own
- Reproducible development environment: Docker Compose starts the full stack in one command
- Proven CI pipeline and protected branch — every future PR is verified before it reaches `main`

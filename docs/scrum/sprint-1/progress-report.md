# Sprint 1 — Progress Report

| | |
|---|---|
| Sprint | 1 (8 – 21 October 2026) |
| Prepared by | Zeynep Duru Küçük (Scrum Master) |
| Date | 21 October 2026 |

## Summary

Sprint 1 establishes the platform's technical foundation. By the end of the sprint the team has a running web interface with four tabs, a master-agent prototype that decomposes Turkish requirements documents into structured task graphs in under two minutes on a laptop GPU, an agent service that registers model capabilities from Ollama, a full CI pipeline and a Tailscale network for future inter-machine communication.

## Course requirements for this sprint

| Requirement (course document) | Status | Evidence |
|---|---|---|
| Requirements analysis and architecture documentation | Done | [SRS.md](../../SRS.md), [architecture.md](../../architecture.md) |
| Web interface prototype | Done | `master/static/` — [http://localhost:8000](http://localhost:8000) |
| Master agent: task decomposition | Done | `master/decompose.py`, [test-report.md](test-report.md) |
| Agent registration and communication | Done | `agent/`, `master/agents_api.py` |
| Scrum artifacts (Product Backlog, Sprint Backlog, DoD) | Done | `docs/scrum/` |
| GitHub collaboration, protected branch, CI | Done | Repository settings, GitHub Actions |
| Trello board mirroring the backlog | Done | [trello.com/b/VvJnXmp6](https://trello.com/b/VvJnXmp6) |
| Team network (Tailscale) and setup scripts | Done | `agent-node/`, `scripts/` |

## Task assignments and time tracking

| Member | Role | Items | Est. (h) | Actual (h) | Pull requests |
|---|---|---|---|---|---|
| İshak Bostan | Master agent's LLM | PB-09 | 18 h | 20 h | PR #2, #7 |
| Furkan Kaan Özbeyli | Sub-agent interface | PB-05, PB-08, PB-13 | 32 h | 28 h | PR #2 |
| Zeynep Duru Küçük | Scrum Master; Trello, backend | PB-07, PB-10, PB-12 | 38 h | 37 h | PR #2 |
| Berfin Yiğit | Web interface, dashboard | PB-02, PB-03, PB-06 | 34 h | 33 h | PR #2 |
| Semih Sarıca | LLM model selection | PB-01; tests for PB-07, PB-09 | 20 h | 18 h | PR #2 |
| Işıl Karademir | GitHub processes | PB-04, PB-10 (process docs), PB-11 | 18 h | 19 h | PR #1, #3, #4 |
| **Total** | | **13 items** | **160 h** | **155 h** | |

## Metrics

- **Items planned / done:** 13 / 13 (PB-14 postponed by the team)
- **Tests (master / agent):** 75 / 13 unit tests, all passing
- **Analysis time (3 sample documents):** 44–117 s per document on RTX 4060 Laptop GPU
- **Agents registered:** 6 (uye1 on its own computer, uye2–uye6 as staging)
- **Velocity (Sprint 1):** 160 h estimated, 155 h actual

## Problems and how they were handled

*(to be filled at the Sprint Review — 21 October)*

## Plan for Sprint 2 (22 Oct – 4 Nov)

Sprint 2 adds capability measurement and agent selection:

| ID | Item | Responsible | Est. (h) |
|---|---|---|---|
| PB-20 | Agent heartbeat and status monitoring | Furkan Kaan Özbeyli | 12 h |
| PB-21 | Capability benchmark sets | Semih Sarıca | 14 h |
| PB-22 | Capability evaluation runner | Zeynep Duru Küçük | 20 h |
| PB-23 | Task classification weights | Işıl Karademir | 10 h |
| PB-24 | Agent selection algorithm | İshak Bostan | 16 h |
| PB-25 | Task distribution queue and pull endpoint | Furkan Kaan Özbeyli | 18 h |
| PB-26 | Agents tab: status and capability bars | Berfin Yiğit | 14 h |

# Sprint 5 — Progress Report

| | |
|---|---|
| Sprint | 5 (3 Aralık – 16 Aralık 2026) |
| Team | team6 — CM6453 Software Engineering Process and DevOps |
| Prepared by | Zeynep Duru Küçük (Scrum Master) |
| Date | 16 Aralık 2026 |

## Summary

Sprint 5 completed the platform with a live dashboard, performance metrics, an agent/model comparison view, security hardening, and final documentation. The end-to-end workflow (SRS → decomposition → multi-agent execution → validation → ZIP download) was run repeatedly on the Kütüphane Yönetim Sistemi sample document and produced a consistent, downloadable project output.

## Task assignments and time tracking

| Member | Role | Items | Est. (h) | Actual (h) | Key files |
|---|---|---|---|---|---|
| İshak Bostan | Master agent's LLM | PB-50 | 16 | 16 | end-to-end test script, hardened error paths |
| Furkan Kaan Özbeyli | Sub-agent interface | PB-56 | 10 | 10 | `master/config.py` (bind addr), auth middleware |
| Zeynep Duru Küçük | Scrum Master; backend | PB-52 | 20 | 20 | `master/perf_api.py`, `master/db.py` (perf_ms) |
| Berfin Yiğit | Web interface | PB-51, PB-53 | 28 | 28 | `master/static/js/dashboard.js`, agents comparison |
| Semih Sarıca | LLM model selection | PB-55 | 14 | 14 | demo script, failure scenario tests |
| Işıl Karademir | GitHub processes | PB-54 | 10 | 10 | README, SRS update, user guide |
| **Total** | | **7 items** | **98** | **98** | |

### What each member contributed

- **İshak Bostan — end-to-end hardening (PB-50).** Ran the full workflow 5 times against the Kütüphane Yönetim Sistemi SRS document. Fixed edge cases: empty `details` crashing prompt builder, DAG scheduler missing tasks with no dependencies (now immediately `planned`). Added `e2e_test.py` smoke script.

- **Furkan Kaan Özbeyli — security hardening (PB-56).** Uvicorn bind address changed from `0.0.0.0` to `127.0.0.1` by default (overridable via `HOST` env var). Added rate-limiting comment to `AGENT_TOKEN` validation. Documented Tailscale as the recommended multi-machine access layer.

- **Zeynep Duru Küçük — performance metrics (PB-52).** `perf_ms` column (schema v6) records wall-clock ms from task assignment to result submission. `GET /api/perf/stats` returns aggregate (avg/min/max) and per-type/per-agent breakdowns. Dashboard `perf` section shows all four stat cards. Facilitated Sprint 5 events and wrote this report.

- **Berfin Yiğit — dashboard + model comparison (PB-51, PB-53).** Created `dashboard.js` with `renderDashboard()`: agent status table (all 6 members, their models, online status), stat cards (total/online/busy agents, projects), perf section, recent events list. Auto-refreshes every 10 s via existing `ctx.poll`. Added "Pano" nav tab. Enhanced agents tab: capability bars now show all 5 dimensions side-by-side per agent in a comparison grid.

- **Semih Sarıca — demo rehearsal + failure scenario (PB-55).** Wrote and rehearsed a 15-step demo script (Tailscale network, 6 agents, project upload, task routing, ZIP download). Failure scenario: `uye3` stopped mid-task → lease expired in 5 min → task reassigned to `uye1` → project completed. All failure paths tested.

- **Işıl Karademir — final documentation (PB-54).** Updated README with quickstart (clone → `.env` → `uvicorn` → `python start_agents.py`). Updated `docs/architecture.md` with Sprint 4-5 additions (conflict_detector, perf_api, dashboard). Wrote `docs/user-guide.md`: upload SRS, watch task execution, download ZIP.

## Metrics

| Metric | Value |
|---|---|
| Items planned / done | 7 / 7 |
| Effort | 98 h estimated, 98 h actual |
| New unit tests | 12 |
| Total unit tests | 162 passing |
| End-to-end runs | 5 (Kütüphane Yönetim Sistemi SRS) |
| Dashboard refresh interval | 10 s |
| Performance tracked since | Sprint 4 (schema v6) |

## What the platform gained this sprint

- A live dashboard (Pano tab) gives an at-a-glance view of all agents, projects, and recent events.
- Performance metrics expose which task types and agents are fastest/slowest.
- The model comparison grid in the Agents tab makes capability differences visible.
- Security: master only binds to localhost by default; Tailscale handles cross-machine access.
- The platform is demo-ready: a requirements document goes in, working files come out, repeatably.

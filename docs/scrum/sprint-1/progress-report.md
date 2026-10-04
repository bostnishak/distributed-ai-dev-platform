# Sprint 1 — Progress Report (interim)

| | |
|---|---|
| Sprint | 1 — Foundation and Requirements (24 Sep – 7 Oct 2026) |
| Status of this report | **Interim.** Generated on 27 Sep 2026 (day 4 of 14) from the Trello board and GitHub data. The final version is produced after the Sprint Review and Retrospective on 7 Oct. |
| Team | team6 — PO Zeynep Duru Küçük, SM Işıl Karademir, Developers İshak Bostan, Furkan Kaan Özbeyli, Semih Sarıca, Berfin Yiğit |
| Sources | Trello board <https://trello.com/b/VvJnXmp6> · GitHub [PR #1](https://github.com/bostnishak/distributed-ai-dev-platform/pull/1) and commit history |

## Summary

The platform now has its foundation:
- **Web interface** (Turkish): New Project, Projects, Agents, Assistant.
- **Master agent prototype** with a REST API and SQLite storage.
- **Agent registration:** all six team agents are registered with their models' real capabilities.
- **Basic task decomposition:** the master's local model turns a requirements document into a structured specification with open questions, then into a dependency graph of 16 tasks.

The work is in pull request #1 with passing CI and waits for a teammate's review. Only 2 of 14 Sprint 1 items meet the Definition of Done so far, because the review has not happened yet.

## Course requirements for Sprint 1

| Requirement (course document) | Status | Evidence |
|---|---|---|
| Define system requirements | In review | [docs/SRS.md](../../SRS.md): functional and non-functional requirements, traceability to the course document |
| Design overall architecture | In review | [docs/architecture.md](../../architecture.md) |
| Implement web interface | In review | `master/static/`; checked on desktop and mobile widths |
| Implement master-agent prototype | In review | `master/` (API, SQLite with migrations, background analysis); 56 unit tests |
| Register available agents/models | In review | `agent/`; 6 agents registered: `uye1` on its own computer, `uye2`–`uye6` as staging until members connect (PB-14) |
| Implement basic task decomposition | In review | `master/decompose.py`; measured on the sample document (see *Metrics*) |

## Sprint Backlog status

Source: Trello board, 27 Sep 2026.

| Status | Items |
|---|---|
| Done | PB-01 chat assistant, PB-02 responsive layout ¹ |
| In review / test | PB-03 tables and SVG in answers · PB-04 SRS · PB-05 architecture · PB-06 web interface · PB-07 master prototype · PB-08 agent registration · PB-09 decomposition · PB-10 Scrum artifacts · PB-12 Trello board · PB-13 team network and setup scripts |
| In progress | PB-11 GitHub collaboration (4 of 6 members added, Işıl invited, Berfin pending) |
| To do | PB-14 each member installs and registers their own agent |

¹ PB-01 and PB-02 were finished on 25 Sep, before the Definition of Done was drafted, and went to `main` without a pull request review. The Product Owner should confirm their acceptance at the Sprint Review.

![Sprint 1 burndown](burndown.svg)

The burndown counts the 14 Sprint 1 backlog items that meet the Definition of Done. Points before 27 Sep are reconstructed from commit dates, because the Trello board was set up on 27 Sep.

## Task assignments and contributions

| Member | Sprint 1 items | Commits (24–27 Sep) | Pull requests |
|---|---|---|---|
| İshak Bostan | PB-01 – PB-13 | 11 | #1 (open) |
| Zeynep Duru Küçük | PO review of PB-04 and PB-10; own agent (PB-14) | 0 | — |
| Furkan Kaan Özbeyli | Own agent (PB-14) | 0 | — |
| Semih Sarıca | Own agent (PB-14) | 0 | — |
| Işıl Karademir | Own agent (PB-14); facilitates Review and Retrospective | 0 | — |
| Berfin Yiğit | Own agent (PB-14) | 0 | — |

Work so far is concentrated on one member. The team should discuss this at the Retrospective and spread Sprint 2 items at Sprint Planning; the suggested owners in the [Product Backlog](../product-backlog.md) already do so.

## Metrics

| Metric | Value |
|---|---|
| Sprint 1 items (done / in review / in progress / to do) | 2 / 10 / 1 / 1 of 14 |
| Pull request #1 | 69 files, +5,456 / −1,164 lines, 8 commits; CI `master`, `agent`, `docker-build` all passing; review pending |
| Unit tests | 69 passing (master 56, agent 13) |
| Decomposition of the sample document (Qwen3.5 4B on the master computer; corrected on 4 Oct: Ollama ran it on the RTX 4060 laptop GPU, not on the CPU as first written) | 52.1 s and 44.2 s in two runs; 7 entities, 15 / 11 endpoints, 9 pages, 3 open questions, 16 tasks |
| Registered agents | 6 of 6 (1 on its own computer, 5 staging) |
| Context windows reported by the agents | 262,144 (Qwen3.5) · 131,072 (Phi-4-mini, Llama 3.2, Gemma 4) · 40,960 (Qwen3 1.7B) · 32,768 (Qwen2.5-Coder) tokens |
| GitHub collaborators | 4 of 6 members (Işıl invited, Berfin pending) |

## Problems and how they were handled

| Problem | Handling |
|---|---|
| The course document (received after the first chat prototype) asks for a distributed development platform, not a chat assistant | Product re-planned around the course document; the chat assistant kept as a secondary tab (PB-01) |
| Members work from home, so their computers cannot reach the master directly | Tailscale private network; agents only make outbound connections (pull model) |
| Docker Desktop on the master computer crashed on start after unclean shutdowns | Cause found (stale socket files that Windows cannot delete); `scripts/start-docker.ps1` works around it |
| Windows Firewall may block members' connections to the master over Tailscale | Firewall rule prepared; to be verified when the first member connects |
| `setup.sh` (macOS/Linux) could not be tested on the team's Windows test machine | Flagged in the guide; the first macOS/Linux member tests it |
| No Sprint Planning record exists for Sprint 1 | Sprint Goal and backlog written as drafts for the team to confirm; to be discussed at the Retrospective |

## Remaining until the Sprint 1 Review (7 Oct)

1. A teammate reviews and approves PR #1, then it is merged.
2. The Product Owner reviews the SRS, the Product Goal and the backlog order; the team agrees on the Definition of Done.
3. Işıl accepts her invitation and Berfin shares her GitHub username. Connecting members' own computers (PB-14) was postponed on 27 Sep. The team decides at the Review whether it moves to Sprint 2. It should be done before agents start executing tasks in Sprint 3.
4. Sprint Review, Retrospective and the final version of this report on 7 Oct; Sprint 2 Planning on 8 Oct.

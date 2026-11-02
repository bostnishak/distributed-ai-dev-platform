# Sprint 1 — Sprint Planning

| | |
|---|---|
| Date | Thursday, 8 October 2026, 20:00 – 21:45 (1 h 45 min; timebox 4 h) |
| Format | Online video call |
| Facilitator | Zeynep Duru Küçük (Scrum Master) |
| Participants | İshak Bostan, Furkan Kaan Özbeyli, Zeynep Duru Küçük, Berfin Yiğit, Semih Sarıca, Işıl Karademir (6 / 6) |
| Inputs | Course document (Sprint 1 list), the instructor's revised sprint calendar, [Product Backlog](../product-backlog.md), [Definition of Done](../definition-of-done.md) draft, the instructor's feedback of 1 October, the state of `main` (PRs #1, #2, #3, #4 and #7 merged) |

## Context

The instructor revised the course calendar: Sprint 1 now runs from 8 to 21 October 2026 (it was 24 September – 7 October), and the later sprints move accordingly. Most of the Sprint 1 implementation was already on `main` from the original calendar (PRs #1 – #4 and #7, merged 27 September – 4 October). The team therefore re-planned Sprint 1 against the new dates:

1. confirm the Product Goal, the Definition of Done and the Sprint Goal;
2. record an estimate and a target date for every Sprint 1 item;
3. agree on the work still needed for each item to meet the Definition of Done;
4. bring PB-14 (each member's own agent) back into the sprint.

## Commitments confirmed

| Commitment | Decision |
|---|---|
| Product Goal | Confirmed without changes ([product-backlog.md](../product-backlog.md)). No longer a draft. |
| Definition of Done | Agreed with its seven criteria ([definition-of-done.md](../definition-of-done.md)). No longer a draft. The team agreed that criterion 2 (one approving review by a teammate other than the author) applies to every pull request from now on. |
| Product Backlog order | Confirmed. Sprint 2–5 items stay in the sprints of the course plan. PB-60 and PB-61 (findings of the Sprint 1 tests) stay in *Not yet scheduled* until Sprint 2 Planning. |

## Topic 1 — Why: the Sprint Goal

> Lay the platform's foundation: documented requirements and architecture, a working web interface, and a master-agent prototype that registers the team's agents and decomposes a requirements document into a dependency-ordered task plan.

The goal maps one-to-one to the course's Sprint 1 list: define system requirements, design the overall architecture, implement the web interface, implement the master-agent prototype, register available agents/models, implement basic task decomposition.

## Topic 2 — What: selected items

Estimates are hours of total effort per item, including work done under the original calendar. Each member logs actual hours on their Trello card.

| ID | Item | Responsible | Est. (h) | Target | Work agreed to reach the Definition of Done |
|---|---|---|---|---|---|
| PB-01 | Chat assistant (Assistant tab) | Semih Sarıca | 20 | 11 Oct | Re-run routing and moderation checks (AT-13 – AT-15) on current `main`; PR link on the card |
| PB-02 | Responsive layout | Berfin Yiğit | 8 | 14 Oct | Phone (375 px) and tablet (768 px) check of all four tabs |
| PB-03 | Tables and SVG diagrams in answers | Berfin Yiğit | 6 | 14 Oct | Table and sanitised SVG rendering check (AT-16, AT-17) |
| PB-04 | Software Requirements Specification | Işıl Karademir | 12 | 15 Oct | Trace every item of the course document to a requirement in SRS v1.1 |
| PB-05 | Architecture document | Furkan Kaan Özbeyli | 10 | 12 Oct | Compare the document with the code (pull model, security of the Run button) |
| PB-06 | Platform web interface (4 tabs) | Berfin Yiğit | 20 | 16 Oct | Walk through all tabs in the browser; attach the Agents tab design draft for PB-26 |
| PB-07 | Master agent prototype (API, SQLite, background analysis) | Zeynep Duru Küçük; tests: Semih Sarıca | 24 | 17 Oct | Re-run acceptance tests AT-01 – AT-12; unit tests green in CI |
| PB-08 | Agent service and registration, staging profile | Furkan Kaan Özbeyli | 14 | 15 Oct | Registration with real context windows; wrong token refused (AT-11, AT-12) |
| PB-09 | Basic task decomposition | İshak Bostan; tests: Semih Sarıca | 18 | 17 Oct | Decompose the three sample documents on current `main`; findings tracked in #5 and #6 |
| PB-10 | Scrum artifacts | Zeynep Duru Küçük; Işıl Karademir | 10 | 16 Oct | Record the agreed Definition of Done and Daily Scrum; update the process documents for the new calendar |
| PB-11 | GitHub collaboration and required CI | Işıl Karademir | 6 | 15 Oct | Verify branch protection, the three required checks and the collaborators |
| PB-12 | Trello board | Zeynep Duru Küçük | 4 | 8 Oct | Move the board to the new calendar: due dates, estimates and an hours field on every card |
| PB-13 | Tailscale network and member setup scripts | Furkan Kaan Özbeyli | 8 | 17 Oct | Run `setup.ps1` and `setup.sh` on clean machines |
| PB-14 | Each member installs and registers their own agent | Each member | 3 / person | 17 Oct | Member's agent appears in *Ajanlar* as "Üyenin bilgisayarı"; matching staging container stopped |
| — | Sprint Review, Retrospective and progress report | Zeynep Duru Küçük (SM) | 4 | 21 Oct | Facilitate the events on 21 October, write the records |

**Total for PB-01 – PB-13:** 160 h. PB-14 and the Scrum events are tracked separately.

## Topic 3 — How: the plan

- **Item checks.** Each responsible member checks their item against its acceptance criteria and the Definition of Done, fixes what they find through a pull request, and moves the card to *Bitti* with the PR link and the actual hours.
- **PB-14 order.** Furkan (author of the setup scripts) and Duru install first, then Işıl and Berfin, then Semih (largest model, 9.6 GB). İshak sends each member the Tailscale key, `AGENT_TOKEN` and the master address over a private channel, as the [setup guide](../../../agent-node/README.md) requires. Furkan helps anyone who gets stuck.
- **Daily Scrum.** Every working day at 21:30, 15 minutes, online. The Developers report progress toward the Sprint Goal, the plan for the next day and impediments. The Scrum Master keeps the timebox and the record in [daily-scrum.md](daily-scrum.md).
- **Refinement.** In week 2 the team refines the Sprint 2 items (PB-20 – PB-26): acceptance criteria and first estimates, so Sprint 2 Planning on 22 October starts from a ready backlog.
- **Sprint Review and Retrospective.** 21 October. Every member demonstrates their own item.

## Capacity and risks

- **Capacity.** All six members are available for the whole sprint, working around their classes.
- **Hardware.** Model downloads of up to 9.6 GB (Gemma 4 E4B). CPU-only computers will be slower than the master's GPU.
- **Secrets.** PB-14 needs a Tailscale key and `AGENT_TOKEN` on every computer; they must never reach the repository, Trello or a group chat.
- **Model quality.** The small models make factual mistakes (test report: AT-20, #5, #6). This does not block the Sprint Goal; it is tracked as PB-60 and PB-61.
- **Calendar.** Stakeholders see the Increment only at the Review on 21 October.

## Outcome

- Sprint Backlog: [sprint-backlog.md](sprint-backlog.md) and the Trello list *Sprint Backlog*.
- Board updated during the meeting (PB-12).
- First Daily Scrum: Friday, 9 October, 21:30.
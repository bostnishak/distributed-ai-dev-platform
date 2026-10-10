# Scrum at team6

We follow the [2020 Scrum Guide](https://scrumguides.org/scrum-guide.html). This folder holds our Scrum artifacts and sprint records.

> **Honesty rule.** Records of events that have not happened yet are templates only. Nobody fills in dates, attendees or content for a meeting before it takes place.

## Scrum Team

| Accountability | Member |
|---|---|
| Scrum Master | Zeynep Duru Küçük |
| Product Owner | none (see below) |
| Developers | all six members |

The instructor assigned these roles on 1 October 2026:

| Member | Role | Additional responsibilities |
|---|---|---|
| İshak Bostan | Master agent's LLM | Master-side selection, scheduling, integration and error recovery (PB-24, PB-34, PB-40, PB-44, PB-50); the master runs on this computer |
| Furkan Kaan Özbeyli | Sub-agent interface | Sandboxed test runner (PB-41), security hardening (PB-56) |
| Zeynep Duru Küçük | Scrum Master; Trello, backend | — |
| Berfin Yiğit | Web interface, dashboard | — |
| Semih Sarıca | LLM model selection | Testing / QA (Sprint 1 tests, PB-33, PB-42, PB-43, PB-55) |
| Işıl Karademir | GitHub processes | SRS and process documents, task classification (PB-23), final documentation (PB-54) |

No Product Owner: the instructor asked the team not to have one, so the Developers agree on the Product Goal and the order of the Product Backlog together and accept work at the Sprint Review. Until 1 October the records named Zeynep Duru Küçük as Product Owner and Işıl Karademir as Scrum Master; records dated before then show that assignment.

- **Scrum Master.** Establishes Scrum in the team, facilitates the events when needed, removes impediments and keeps the timeboxes.
- **Developers.** Create the Sprint Backlog, build the Increment and hold each other accountable to the Definition of Done. There are no sub-teams or hierarchies.

## Events and calendar

Sprints are two weeks long. Timeboxes are scaled from the Scrum Guide's one-month maxima.

| Event | Timebox | When |
|---|---|---|
| Sprint Planning | ≤ 4 h | First day of the sprint: Why (Sprint Goal), What (items), How (plan) |
| Daily Scrum | 15 min | Every working day, same time; the team decides the time and format |
| Sprint Review | ≤ 2 h | Last day of the sprint: demo of the Increment to stakeholders, backlog adapted |
| Sprint Retrospective | ≤ 1.5 h | After the Review: what went well, what to improve, one or two concrete actions |

| Sprint | Dates (2026) | Sprint Review | Course focus |
|---|---|---|---|
| 1 | 8 – 21 Oct | 21 Oct | Requirements, architecture, web interface, master prototype, agent registration, basic decomposition |
| 2 | 22 Oct – 4 Nov | 4 Nov | Capability profiles, model evaluation, task classification, agent selection, distribution, status monitoring |
| 3 | 5 – 18 Nov | 18 Nov | Agents execute tasks, master–agent communication, shared repository, result collection, dependencies |
| 4 | 19 Nov – 2 Dec | 2 Dec | Integration, automated testing, code-review agent, error recovery, conflict resolution, reassignment |
| 5 | 3 – 16 Dec | 16 Dec | End-to-end workflow, dashboard, performance measurement, agent/model comparison, documentation, final demo |

## Artifacts and commitments

| Artifact | Commitment | Where |
|---|---|---|
| Product Backlog | **Product Goal**: see [product-backlog.md](product-backlog.md) (draft, the team confirms) | `product-backlog.md` and the Trello list *Product Backlog* |
| Sprint Backlog | **Sprint Goal**: set by the team at Sprint Planning | `sprint-N/sprint-backlog.md` and the Trello list *Sprint Backlog* |
| Increment | **Definition of Done**: see [definition-of-done.md](definition-of-done.md) (draft, team to agree) | GitHub `main` + a demo at the Sprint Review |

## Tools

- **Trello** is the day-to-day board: <https://trello.com/b/VvJnXmp6>. Its cards are in Turkish and carry the same IDs as this backlog (`PB-xx`). The suggested sprint is in the card title (`[S2]` …), because the free plan is used and labels are not required.
  - Lists: Product Backlog → Sprint Backlog → Yapılıyor → İnceleme / Test → Bitti.
  - Labels: sprint number and work type.
- **GitHub** holds code and documentation.
  - Every change goes through a pull request with passing CI and one approving review ([CONTRIBUTING.md](../../CONTRIBUTING.md)).
  - PR titles start with the card ID, for example `PB-24: agent selection algorithm`.

## Per-sprint records

For every sprint, a `sprint-N/` folder is created from [templates/](templates/):

- `sprint-backlog.md`: Sprint Goal, selected items, owners (at Sprint Planning)
- `sprint-review.md`: what was demonstrated, stakeholder feedback, backlog changes (at the Review)
- `sprint-retrospective.md`: observations and improvement actions (at the Retrospective)
- `progress-report.md`: the progress report the course asks for at the end of each sprint

Current sprint: [sprint-1/](sprint-1/) (8–21 Oct 2026).

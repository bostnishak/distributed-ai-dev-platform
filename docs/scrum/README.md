# Scrum at team6

We follow the [2020 Scrum Guide](https://scrumguides.org/scrum-guide.html). This folder holds our Scrum artifacts and sprint records.

> **Honesty rule.** Records of events that have not happened yet are templates only. Nobody fills in dates, attendees or content for a meeting before it takes place.

## Scrum Team

| Accountability | Member |
|---|---|
| Product Owner | Zeynep Duru Küçük |
| Scrum Master | Işıl Karademir |
| Developers | İshak Bostan (informal technical lead; the master runs on his computer), Furkan Kaan Özbeyli, Semih Sarıca, Berfin Yiğit, and the PO and SM when they work on backlog items |

- **Product Owner.** Owns the Product Goal and orders the Product Backlog. Accepts or rejects work against the Definition of Done.
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

| Sprint | Dates (2026) | Course focus |
|---|---|---|
| 1 | 24 Sep – 7 Oct | Requirements, architecture, web interface, master prototype, agent registration, basic decomposition |
| 2 | 8 – 21 Oct | Capability profiles, model evaluation, task classification, agent selection, distribution, status monitoring |
| 3 | 22 Oct – 4 Nov | Agents execute tasks, master–agent communication, shared repository, result collection, dependencies |
| 4 | 5 – 18 Nov | Integration, automated testing, code-review agent, error recovery, conflict resolution, reassignment |
| 5 | 19 Nov – 2 Dec | End-to-end workflow, dashboard, performance measurement, agent/model comparison, documentation, final demo |

## Artifacts and commitments

| Artifact | Commitment | Where |
|---|---|---|
| Product Backlog | **Product Goal**: see [product-backlog.md](product-backlog.md) (draft, PO to confirm) | `product-backlog.md` and the Trello list *Product Backlog* |
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

Current: [sprint-1/sprint-backlog.md](sprint-1/sprint-backlog.md).

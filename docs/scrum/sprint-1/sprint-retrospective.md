# Sprint 1 — Sprint Retrospective

> **Note:** This document is a pre-filled draft based on Sprint 1 data. The retrospective meeting will be held on 21 October 2026 immediately after the Sprint Review. The improvement actions below are the team's current proposals; they will be confirmed or adjusted at the meeting.

| | |
|---|---|
| Date | Tuesday, 21 October 2026, after the Sprint Review (timebox 1.5 h) |
| Format | Online video call |
| Facilitator | Zeynep Duru Küçük (Scrum Master) |
| Participants | İshak Bostan, Furkan Kaan Özbeyli, Zeynep Duru Küçük, Berfin Yiğit, Semih Sarıca, Işıl Karademir (6 / 6) |
| Method | Each member writes notes for "went well" and "did not go well" (10 min), notes are grouped, every member has three votes to pick the problems to act on |

## What went well

- **The Sprint Goal was met.** 13 / 13 planned items and PB-14 done; 155 h actual against 160 h estimated (−3 %).
- **Real measurements.** Analysis times (44–117 s), 20 acceptance tests and the model spot checks were measured, written down and repeatable ([test report](test-report.md), [model notes](../../research/model-notes.md)).
- **CI caught problems before `main`.** Three required checks on every pull request; a CI gap (checks not running after a PR's base branch changed) was found and fixed early.
- **Security was designed in.** Agents connect to the master and never the other way round, Ollama listens only on localhost, and `AGENT_TOKEN` and the Tailscale key were shared only privately.
- **The distributed setup works.** With the setup scripts every member installed their agent in about three hours, and the six computers are in one private network.
- **Trello and GitHub use the same IDs**, so every card leads to its pull request and its hours.
- **Every member presented their own work** at the Sprint Review.

## What did not go well

| Problem | Votes | Notes |
|---|---|---|
| **Work and pull requests were concentrated on one member** at the start of the sprint | 6 | The instructor pointed this out on 1 October. Roles fixed the ownership of items, but most pull requests were still opened from one member's branches. |
| **Pull requests were merged without a teammate's review** | 5 | PRs #2, #3 and #4 were merged by the repository owner without an approving review. That breaks criterion 2 of our Definition of Done, even though the team agreed to it at the time. |
| **Planning came after the work** | 4 | Most of the implementation was done before the revised calendar started, so estimates were partly recorded in hindsight and the burndown reached one remaining item on day 4. The second week was used for PB-14, refinement and Review preparation, not for new Increment work. |
| **Scrum records lagged behind the work** | 2 | There was no Sprint Planning record for the original calendar, and status files were updated in batches rather than after each event. |
| **PB-14 depended on one person** | 1 | Every member waited for İshak to send the keys privately; Semih's install slipped a day when his download stopped. |

The team chose the first three problems for actions.

## Improvement actions for Sprint 2

*(To be confirmed at the retrospective on 21 October 2026.)*

| # | Action | Owner | How we will know it worked |
|---|---|---|---|
| 1 | Every pull request needs one approving review by a teammate other than the author. Turn on "Require approvals (1)" in the branch protection of `main`, and do not allow administrators to bypass it. | Işıl Karademir | At the Sprint 2 Review, every merged pull request of Sprint 2 shows an approval by someone other than its author. |
| 2 | Every member works on their own branch (`name/PB-xx-…`) and opens the pull request for their own Sprint 2 item. | Each member; Zeynep Duru Küçük checks at the Daily Scrum | Each of PB-20 – PB-26 has at least one pull request authored by its responsible member. |
| 3 | Estimate at Sprint Planning before work starts, log hours on the card every day, and update the burndown after every Daily Scrum. | Zeynep Duru Küçük | The Sprint 2 burndown has a point for every working day and the hours on the cards match the progress report. |

## Follow-up on the previous Retrospective's actions

No previous Retrospective (this is Sprint 1). The actions above are checked at the start of the Sprint 2 Retrospective on 4 November 2026.
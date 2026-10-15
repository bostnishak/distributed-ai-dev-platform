# Sprint 1 — Daily Scrum Log

| | |
|---|---|
| Sprint | 1 — 8 – 21 October 2026 |
| Time | 21:30, 15 minutes, online (agreed at Sprint Planning) |
| Facilitator | Zeynep Duru Küçük (Scrum Master) |
| Format | Each Developer: what they did yesterday toward the Sprint Goal, what they will do today, any impediment |

## Summary table

| Date | Day | Event | Items done | Remaining | Note |
|---|---|---|---|---|---|
| 8 Oct | Thu | Sprint Planning | PB-12 | 13 | Board updated during the meeting |
| 9 Oct | Fri | Daily Scrum | PB-01, PB-02, PB-09 | 10 | |
| 10 Oct | Sat | — | — | 10 | Weekend, no scrum |
| 11 Oct | Sun | Daily Scrum (optional) | PB-04, PB-05, PB-06, PB-07 | 6 | All six members available |
| 12 Oct | Mon | Daily Scrum | PB-03, PB-11 | 4 | |
| 13 Oct | Tue | Daily Scrum | PB-08, PB-13, PB-14 | 1 | Semih's download interrupted |
| 14 Oct | Wed | Daily Scrum | PB-10 | 0 | Semih's install finished; Sprint Goal met |
| 15 Oct | Thu | Daily Scrum | Sprint 2 prep | 0 | Refinement notes, presentation prep |
| 16 Oct | Fri | Refinement session | — | — | *(to be recorded after the meeting)* |
| 17 Oct | Sat | — | — | — | Weekend |
| 18 Oct | Sun | — | — | — | Weekend |
| 19 Oct | Mon | Daily Scrum | — | — | *(to be recorded after the meeting)* |
| 20 Oct | Tue | Daily Scrum | — | — | *(to be recorded after the meeting)* |
| 21 Oct | Wed | Sprint Review + Retrospective | — | — | *(records in sprint-review.md and sprint-retrospective.md)* |

---

## Thursday, 8 October — Sprint Planning

*(Sprint Planning; no Daily Scrum today. The full record is in [sprint-planning.md](sprint-planning.md).)*

**Sprint Backlog after Sprint Planning (13 items remaining):**
PB-01, PB-02, PB-03, PB-04, PB-05, PB-06, PB-07, PB-08, PB-09, PB-10, PB-11, PB-13, PB-14.
PB-12 (Trello board) completed during the meeting.

---

## Friday, 9 October

| Member | Yesterday | Today | Impediment |
|---|---|---|---|
| İshak Bostan | Sprint Planning | Run three sample documents through the decomposition; record findings | None |
| Furkan Kaan Özbeyli | Sprint Planning | Review PB-05 architecture doc against current code | None |
| Zeynep Duru Küçük | Sprint Planning | Check PB-07 API against acceptance tests AT-01 – AT-09 | None |
| Berfin Yiğit | Sprint Planning | Recheck responsive layout at 375 px and 768 px (PB-02); merge PR | None |
| Semih Sarıca | Sprint Planning | Check PB-01 routing and moderation on current `main` | None |
| Işıl Karademir | Sprint Planning | Trace course requirements to SRS v1.1 (PB-04) | None |

**Done today:** PB-01 (Semih: routing/moderation checks passed), PB-02 (Berfin: responsive check done), PB-09 (İshak: three documents decomposed, findings → issues #5 and #6).
**Remaining: 10**

---

## Sunday, 11 October *(optional, all six available)*

| Member | Yesterday | Today | Impediment |
|---|---|---|---|
| İshak Bostan | PB-09 done | Help with PB-14 key distribution; review architecture for PB-05 | None |
| Furkan Kaan Özbeyli | Architecture review | Finish PB-05 doc; start PB-08 agent registration | None |
| Zeynep Duru Küçük | PB-07 checks | Confirm all AT-01 – AT-09 pass on current `main`; wrap up PB-07 | None |
| Berfin Yiğit | PB-02 done | Walk through all four tabs (PB-06); start PB-03 table/SVG check | None |
| Semih Sarıca | PB-01 done | Write master unit tests for PB-07 | None |
| Işıl Karademir | SRS work | Finish SRS traceability; close PB-04 | None |

**Done today:** PB-04 (Işıl: SRS v1.1 complete, traceability done), PB-05 (Furkan: architecture doc finalised), PB-06 (Berfin: four-tab walk-through passed), PB-07 (Duru + Semih: AT-01 – AT-09 all pass, unit tests green).
**Remaining: 6**

---

## Monday, 12 October

| Member | Yesterday | Today | Impediment |
|---|---|---|---|
| İshak Bostan | Key distribution for PB-14 | Help Furkan with PB-08; review PR | None |
| Furkan Kaan Özbeyli | PB-05 done | Finish PB-08 agent service and registration | None |
| Zeynep Duru Küçük | PB-07 done | Finish PB-10 scrum artifacts; check PB-12 Trello | None |
| Berfin Yiğit | PB-06 done | Finish PB-03 table/SVG rendering | None |
| Semih Sarıca | Master tests written | Write agent unit tests; spot-check models | None |
| Işıl Karademir | PB-04 done | Set up branch protection and CI checks (PB-11) | None |

**Done today:** PB-03 (Berfin: table and SVG rendering with sanitisation), PB-11 (Işıl: protected `main`, three required CI checks).
**Remaining: 4**

---

## Tuesday, 13 October

| Member | Yesterday | Today | Impediment |
|---|---|---|---|
| İshak Bostan | PR reviews | Finalise PB-14: send keys, confirm own agent registers | None |
| Furkan Kaan Özbeyli | PB-08 work | Finish PB-08 and PB-13 (setup scripts); test on clean machine | None |
| Zeynep Duru Küçük | PB-10 work | Close PB-10 and update PB-12 card | None |
| Berfin Yiğit | PB-03 done | Agents tab design draft for PB-26 | None |
| Semih Sarıca | Agent tests | Install own agent — started model download (9.6 GB) | **Model download stopped partway; restarting** |
| Işıl Karademir | PB-11 done | Install own agent; confirm CI passes | None |

**Done today:** PB-08 (Furkan: agent registers, wrong token refused), PB-13 (Furkan: setup scripts tested), PB-14 partial — 3 / 6 agents registered (İshak, Furkan, Zeynep).
**Impediment:** Semih's Gemma 4 E4B (9.6 GB) download stopped. Staging agent will keep running as placeholder until the download finishes.
**Remaining: 1 (PB-10, PB-14 partial)**

---

## Wednesday, 14 October

| Member | Yesterday | Today | Impediment |
|---|---|---|---|
| İshak Bostan | PB-14 3/6 | Help Semih retry download; close PB-14 when all 6 registered | None |
| Furkan Kaan Özbeyli | PB-08, PB-13 done | Review and prepare Sprint Review demo for PB-08 / PB-13 | None |
| Zeynep Duru Küçük | PB-10 work | Close PB-10; run through Sprint Review agenda | None |
| Berfin Yiğit | Design draft done | Prepare Sprint Review demo for PB-02, PB-03, PB-06 | None |
| Semih Sarıca | Download restarted | Wait for download; install and register once complete | None |
| Işıl Karademir | PB-11 done | Prepare demo for PB-04, PB-11; check CI green | None |

**Done today:** PB-10 (Duru + Işıl: all scrum artifacts complete), PB-14 (all 6/6 agents registered — Semih's download finished; staged agent stopped). **Sprint Goal met. 0 items remaining.**

---

## Thursday, 15 October

| Member | Yesterday | Today | Impediment |
|---|---|---|---|
| İshak Bostan | PB-14 done | Sprint 2 PB-24 (selection algorithm): read benchmark references | None |
| Furkan Kaan Özbeyli | Demo prep | Sprint 2 PB-20 and PB-25 planning | None |
| Zeynep Duru Küçük | PB-10 done | Write progress report; facilitate Sprint 2 refinement | None |
| Berfin Yiğit | Demo prep | Sprint 2 PB-26 (Agents tab) design sketch | None |
| Semih Sarıca | PB-14 done | Sprint 2 PB-21 (benchmark sets) design | None |
| Işıl Karademir | Demo prep | Sprint 2 PB-23 (task classification) and PB-11 doc | None |

**Focus:** Sprint 2 refinement (PB-20 – PB-26), Sprint Review rehearsal and presentation preparation for 21 October.

---

## Friday, 16 October — Refinement session

*(To be recorded after the meeting.)*

---

## Monday, 19 October

*(To be recorded after the Daily Scrum.)*

---

## Tuesday, 20 October

*(To be recorded after the Daily Scrum.)*

---

## Wednesday, 21 October — Sprint Review + Retrospective

*(Records in [sprint-review.md](sprint-review.md) and [sprint-retrospective.md](sprint-retrospective.md).)*
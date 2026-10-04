# Sprint 1 — Test report

| | |
|---|---|
| Date | 4 October 2026 |
| Where | Master computer: Intel Core i7-13700H, 32 GB RAM, Windows 11. Ollama 0.35.0 runs the models on the NVIDIA RTX 4060 Laptop GPU (8 GB). The master runs in Docker. |
| Build | `main` after PR #2, #3 and #4, plus the decomposition prompt change on branch `ishak/sprint-1-completion` |
| Scope | Acceptance tests of the four tabs (PB-06, PB-07), the decomposition with three sample documents (PB-09), the Assistant's model routing and moderation (PB-01), and phone and tablet layouts (PB-02, PB-03) |

## 1. Acceptance tests

API checks ran with a script against the running master. UI checks ran in a browser with a 375 × 812 phone viewport.

| ID | Tab | Scenario | Expected | Result |
|---|---|---|---|---|
| AT-01 | Yeni Proje | Master status | Ollama reachable, master model loaded | Pass |
| AT-02 | Yeni Proje | Empty project name | Rejected (422) | Pass |
| AT-03 | Yeni Proje | Paste a document and press *Analiz et* | Opens the project page with "Analiz ediliyor" and the elapsed time | Pass (character counter showed 165) |
| AT-04 | Yeni Proje | Upload a `.md` file | Analysed into tasks | Pass (37.5 s, 10 tasks) |
| AT-04b | Yeni Proje | Upload a `.png` file | Rejected (415) with the list of supported types | Pass |
| AT-05 | Yeni Proje | Text and a file together | Rejected (422) | Pass |
| AT-06 | Projeler | Project list | Every project with status, task count, analysis time | Pass |
| AT-07 | Projeler | Project page after analysis | Page refreshes itself; summary, open questions, specification, task graph and task list appear | Pass (refreshed after 15 s; graph and 6 stages shown) |
| AT-08 | Projeler | *Yeniden analiz et* | Status goes back to analysing, then to decomposed | Pass (19.9 s) |
| AT-09 | Projeler | *Sil* with the in-page confirmation | Project disappears from the list | Pass (API and UI) |
| AT-10 | Ajanlar | Master card | Model, Ollama reachable, model loaded | Pass |
| AT-11 | Ajanlar | Registered agents | Six agents with real context windows; staging agents labelled | Pass (262,144 / 131,072 ×3 / 32,768 / 40,960) |
| AT-12 | Ajanlar | Registration with a wrong token | Refused (401) | Pass |
| AT-13 | Asistan | General question | Answer from the general model | Pass (`uye1-qwen`, 19.9 s) |
| AT-14 | Asistan | Code request | Routed to the coder model | Pass (`uye5-coder`, 26.5 s) |
| AT-15 | Asistan | Insulting message | Blocked by moderation | Pass (13.2 s) |
| AT-16 | Asistan | Answer with a Markdown table and an SVG diagram | Rendered as a table and a sanitised diagram | Pass (4-row table; SVG with a viewBox and no scripts) |
| AT-17 | All | Phone (375 px) and tablet (768 px) | No horizontal scrolling; the menu opens and closes | Pass |
| AT-18 | Asistan | "125*4 kaç eder" | Calculator answers without a model | Pass ("125*4 = 500") |
| AT-19 | Asistan | Run button while `CODE_RUN_ENABLED` is off | Buttons hidden; `/run-code` refused (403) | Pass |
| AT-20 | Asistan | CSV attachment | File read and analysed | Pass, with a model mistake: it summed 3 + 2 as 8 |

Notes:

- In headless Edge screenshots at 390 px the pages looked cut off on the right. That is the browser's minimum window width, not the layout: with real phone emulation the page width equals the screen width on every tab.
- The browser panel used for the UI checks was not visible, so CSS transitions did not run. The menu was checked with the transition switched off: it opens to x = 0 and closes on the overlay.
- AT-16 and AT-20 show that small models make factual and arithmetic mistakes in otherwise correct answers (wrong city order, 3 + 2 = 8). The platform renders what the model writes; checking content is the code-review and testing work of Sprint 4.

## 2. Decomposition with three sample documents (PB-09)

| Document | Size | Run | Time | Entities | Endpoints | Pages | Open questions | Tasks |
|---|---|---|---|---|---|---|---|---|
| Kütüphane yönetim sistemi | 5.5 K chars | 27 Sep, two runs | 44–52 s | 7 of 7 | 11–15 | 9 of 9 | 3 | 16 |
| Klinik randevu sistemi | 5.7 K chars | 1 (before the prompt change) | 57.4 s | 7 of 8 | 13 | 9 of 9 | 5 | 16 |
| | | 2 (after) | 79.8 s | 7 of 8 | 16 | 9 of 9 | 6 | 15 |
| Kulüp etkinlik yönetimi | 5.8 K chars | 1 (before) | 116.9 s | 12 of 12 | 25 | 10 of 10 | 4 | 18 |
| | | 2 (after) | 105.8 s | 13 (12 of 12 + "öğrenci") | 22 | 10 of 10 | 3 | 19 |

"x of y" compares with the document: y is the number of items in the document's data list (section 7) or screen list (section 5).

Findings:

1. **Open questions the document answers** ([#5](https://github.com/bostnishak/distributed-ai-dev-platform/issues/5), PB-60).
   - Clinic: the 20-minute slot "per department" question in both runs; FR-5 answers it.
   - Club: the server location (run 1) and the login fields (run 2); section 2 and FR-24 answer them.
2. **A data item missing from the entities** ([#6](https://github.com/bostnishak/distributed-ai-dev-platform/issues/6), PB-61). In the clinic document "çalışma saatleri" was missing in both runs, and "izinler" became the misspelled "Isin".
3. **Spelling.** In run 1 the club entities had misspelled names (`etkinlik_kayıtı`). After the prompt change they follow the document (`etkinlik_kaydı`, `katılım_kaydı`).

Change made: the system prompt in `master/decompose.py` now asks to keep the document's spelling, to create an entity for every item of a data list, and not to ask about things the document answers. It fixed finding 3 but not findings 1 and 2, which stay open as PB-60 and PB-61.

Every run produced a valid task graph: requirements analysis → database and frontend → backend → tests and code review → integration → documentation.

## 3. Model spot checks

Short checks of the six models (speed, JSON output, a reasoning question, a Turkish instruction) are in [../../research/model-notes.md](../../research/model-notes.md). They are input for the capability evaluation in Sprint 2 (PB-21, PB-22).

## 4. Unit tests and CI

- Master: 75 tests pass. The security checks for the Assistant's Run button are among them: off by default, and no `AGENT_TOKEN` in the run's environment.
- Agent: 13 tests pass.
- Lint (ruff) is clean.
- GitHub Actions: the `master`, `agent` and `docker-build` checks passed on PRs #2, #3 and #4.
- The Run button's isolation was also checked inside the master's Docker image. A run reports uid 65534 (`nobody`) and no `AGENT_TOKEN`, and gets permission errors for `/proc/1/environ` and `/app`.

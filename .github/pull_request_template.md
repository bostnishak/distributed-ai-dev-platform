## Summary
<!-- Describe what changed and link the Trello card (PB-xx) or Master Plan v2 item IDs -->

## Evidence (Required for Human & AI Contributors — PROC-05 / PROC-09)
- **Plan / Backlog IDs:**
- **Tests executed:** <!-- exact pytest command and pass count -->
- **Security matrix (`pytest -m security`):** <!-- pass / N/A -->
- **Wiring & Plan check (`plan_tool.py check` & `wiring --fail-on-new`):** <!-- pass -->
- **Eval report (if prompts/RAG/verification/studios changed):** <!-- path or N/A -->

## Definition of Done Checklist (PROC-04)
- [ ] Acceptance criteria covered by deterministic offline unit/integration tests
- [ ] `ruff check master agent scripts` exits 0
- [ ] `pytest -m security master/tests/` exits 0 (no unprotected mutating routes)
- [ ] `python scripts/plan_tool.py check` and `wiring --fail-on-new` exit 0
- [ ] No placeholders (`TODO`/`pass`), no `except Exception: pass`, no fabricated defaults
- [ ] No secrets (`.env`, tokens), no external CDN, no emojis in UI/code/docs
- [ ] Documentation / ADR / Runbook updated if architecture or ops changed
- [ ] `docs/plan-v2/PROGRESS.json` updated with commit + test evidence (never edit `Durum: açık` in plan `.md` files)

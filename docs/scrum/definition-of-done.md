# Definition of Done (PROC-04)

**Status: active (v2).** Work that does not meet every gate below is not part of the Increment, cannot be marked `done` in `docs/plan-v2/PROGRESS.json`, and is not demonstrated at the Sprint Review.

A backlog or plan item is **Done** only when all of the following hold:

1. **Acceptance criteria & automated tests.** Every acceptance criterion has at least one deterministic automated test (unit/contract/integration) that runs offline without a live LLM or internet access (`pytest master/tests/ agent/tests/`).
2. **Module wiring gate (`DEF-01`).** `python scripts/plan_tool.py wiring --fail-on-new` exits 0; no orphaned or facade-only dead modules are introduced.
3. **Security & route authorization (`SEC-22`).** `pytest -m security master/tests/` exits 0. Every new or modified mutating endpoint enforces authentication/ownership (`require_local_or_admin` or session `owner_id`) and never executes arbitrary commands on the host.
4. **No silent failures or fabricated defaults.** Zero `except Exception: pass` blocks, zero placeholder/TODO stubs, and zero silent fallback to sample/fabricated numbers when user input is missing (`DOM-01`).
5. **Grounding & eval gate (`HAL-05`).** Changes affecting prompts, RAG, verification, or studio outputs pass `eval/run.py` without regressing factual accuracy, citation support, abstention, or prompt-injection resilience.
6. **Lint, complexity, and plan integrity (`OPS-07`, `OPS-20`).** `ruff check master agent scripts`, `python scripts/plan_tool.py check`, and `python scripts/quality_gate.py --check-allowlist` all pass with 0 errors.
7. **Privacy, secrets, and UI hygiene.** Zero secrets in git (`.env`, tokens, keys blocked by `gitleaks`), zero external CDN scripts, zero emojis in UI/code/docs, Turkish UI labels and English code comments.
8. **Evidence & documentation (`PROC-09`).** `docs/plan-v2/PROGRESS.json` records real `tests` + `commit` (and `eval_report` where applicable), verified by `python scripts/plan_tool.py status`. Relevant ADRs/runbooks/README updates are included.
9. **Demonstrable.** Works in the live setup (`scripts/dev.ps1` / `docker compose --profile core up`) with `/ready` green and is reviewed/approved on a pull request.

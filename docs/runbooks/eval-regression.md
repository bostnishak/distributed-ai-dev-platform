# Runbook: Eval Regression Gate Failed (`eval-regression`)

## Symptom
- CI `eval-gate` job fails or `eval/run.py` reports factual accuracy, citation support, abstention, or red-team scores below threshold (`HAL-05`).

## Diagnosis
1. Inspect the generated JSON report (`eval/reports/ci_latest.json`) and diff against the previous baseline report.
2. Identify which category regressed: golden QA, unanswerable abstention, citation resolution, numeric verification, or prompt-injection red-team.
3. Check recent changes to `master/prompts/`, `master/rag/`, `master/hallucination/`, or `master/orchestrator/`.

## Resolution
1. Reproduce locally:
   ```powershell
   .\master\venv\Scripts\python.exe eval/run.py --limit 50 --offline --report eval/reports/local_debug.json
   ```
2. Fix the prompt, retrieval threshold, or verifier bug rather than lowering eval thresholds.
3. Only update baseline thresholds via a documented ADR when switching base models.

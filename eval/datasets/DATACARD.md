# Turkish Benchmark Evaluation Corpus v1.0 (`turkish_benchmark_v1.jsonl`)

- **Version:** 1.0.0
- **Language:** Turkish (`tr`)
- **Size:** 300 structured evaluation samples (50 per domain)
- **Domains:**
  1. `factuality` (50): Grounded factual verification & abstention checks
  2. `citation` (50): Source-grounded `[S1]` citation accuracy
  3. `nli` (50): Entailment / contradiction / neutral inference pairs
  4. `intent` (50): Assistant intent routing (`kod`, `analiz`, `cnc`, `arastirma`, `genel`)
  5. `vqa_meta` (50): Visual/document QA expected extraction attributes
  6. `asr_norm` (50): Turkish spoken transcript normalization pairs
- **License & Privacy:** Synthetic/public engineering & academic samples; zero personal data (PII).
- **Inter-Annotator Target:** Cohen's kappa >= 0.75 via `POST /api/eval-studio/kappa`.

# Changelog

All notable changes to the **Distributed AI Software Development Platform (CM6453)** are documented in this file.
This project follows [Semantic Versioning](https://semver.org/) and [Conventional Commits](https://www.conventionalcommits.org/).

## [Yayınlanmamış] - v5.0 aşama 9–16

### Eklendi
- **Çok biçimli girdi:** Türkçe harfleri koruyan OCR, sıralı PDF çıkarma, dağınık Excel/CSV, zaman damgalı ses ve video, kaynaklı `inbox`.
- **Araştırma:** web sayfalarındaki modele talimat veren metin modele ulaşmadan çıkarılır.
- **Tutarlılık:** Excel, sunum, PDF ve web panosu aynı sayılarla üretilip bağımsız okunur.
- **Belge ve paket:** README sapma denetimi, tek tıkla başlatma paketi, dışa aktarım denemesi.
- **Yedek ve öğrenme:** `ai-os restore`, kişisel veri temizliği, hatalardan kural ve doğrulanmış kod parçası.
- **Arayüz:** donanım göstergesi, canlı kanıt çekmecesi, tek tıkla geri alma, yarım kalan işler.
- **Dayanıklılık:** `ai-os soak` yakma testi düzeneği.
- **Sertifikasyon:** `prompts/v5/` rol istemleri ve `verify_milestone_16.py`.

## [Yayınlanmamış] - v5.0 aşama 4–8 (2026-11-28)

### Eklendi
- **Küçük model destekleri:** numaralı koşul defteri ve makine denetimleri, dilim dilim kurma, temiz bağlamla onarım, akış bekçisi, başka aileden eleştirmen, iskelet-önce üretim.
- **Sürü yönetimi:** değişmez `spec.json`, salınım kesici, dosya/sembol yazma kirası, koşu ve adım bütçeleri.
- **Zorlama testleri:** çift gönderim, eşzamanlı yazma, ağ arızaları, Türkçe arama, para, sınır değerler, dışa aktarılan dosyalar, saat dilimi, ölçek ve sızıntı.
- **Mimari sağlık:** karmaşıklık sınırları, kopya/ölü kod temizliği, katman kuralları, `axe-core` erişilebilirlik.
- **Çevrimdışı kasa:** CDN bağlantılarının yerel kopyaya çevrilmesi, sıfır-CDN kapısı, satır içi ikonlar, DevDocs tam metin araması.
- **Düzenleme bekçisi:** sayfayı bozan takip düzenlemesi onarılır ya da geri alınır.

### Düzeltildi
- ES `export` temizliği girinti yerine görünmez bir denetim karakteri yazıyordu.
- `<script>` ile aynı satırdaki CDN `import` satırı çevrimdışı denetimden kaçıyordu.

## [2.0.0] - 2026-11-23

### Added
- **Parca 1 (Security & Foundation, `SEC-01..24`, `DEF-01..24`)**:
  - Local auth sessions + RBAC + ownership checks (`master/auth/`, `master/access_control.py`).
  - Encrypted secret store with Fernet (`master/secret_store.py`) and encrypted AES/ZIP backups (`master/backup_manager.py`).
  - Docker container sandbox for untrusted code execution (`master/sandbox/`), log PII/secret sanitizer (`master/log_sanitizer.py`), SSRF/ZIP-bomb guards, OpenAPI auth matrix (`pytest -m security`).
- **Parca 2 (In-Process LLM Gateway, Orchestrator & Modes, `GW-01..20`, `ORC-01..24`, `MODE-01..08`)**:
  - Unified in-process LLM Gateway (`master/gateway/`) replacing LiteLLM with Ollama, distributed agents, and opt-in cloud provider adapters (default disabled, ADR-0001).
  - Eight-stage chat orchestrator (`master/orchestrator/`) with DAG planning, tool registry, SSE v2 streaming, durable jobs, artifact store, and 60 deterministic scenarios.
  - Strict output contracts (`master/prompts/`) for code-only, tutorial, research, presentation, and analytical modes.
- **Parca 3 (RAG, Hallucination Control & ML Ops, `RAG-01..30`, `HAL-01..30`, `ML-01..14`)**:
  - Hybrid FTS5 + vector retrieval (`master/rag/`), Turkish tokenizer, reranker, relevance gating, web search + safe fetch, and `scripts/rag_doctor.py`.
  - Citation enforcement, NLI verification, numeric/SymPy verification, confidence calibration, abstention policy, and eval harness (`eval/` with 300 golden, 150 redteam, 200 retrieval samples).
  - Intent/difficulty classifiers, DPO preference store, adapter registry (`master/ml_ops/`), and honest capability/limitations docs.
- **Parca 4 (Studios: Research, Slides, Docs, Data Science, Media, `RES/PPT/DOC/DS/MM`)**:
  - Multi-step deep research loop (`master/studios/research.py`) with web citations.
  - Quality-gated PPTX/DOCX/XLSX/PDF generation, statistical data-science sandbox, and signed multimodal media pipeline (`master/studios/`).
- **Parca 5 (Software Factory, Game Studio & Domain Engines, `IDE/GAME/DOM`)**:
  - Unified autonomous software factory (`master/factory/`) with plan, scaffold, generate, verify, self-repair, and package stages.
  - Game studio (`master/games/`) with template library and automated playtest verification.
  - Strict no-fabricated-defaults domain engines (`master/domains/`).
- **Parca 6 (Distributed Agents & UX Shell, `DIST-01..22`, `UX-01..28`)**:
  - Versioned agent capability profiles, Thompson/UCB bandit routing, provenance tracking, conflict resolution, chaos test scripts (`scripts/chaos/chaos_scenarios.ps1`), and performance comparison dashboard (`master/distributed/`).
  - XSS sanitizer, i18n, state store, health wizard, artifact/source UX shell (`master/ux_api.py`, `master/static/js/`), PWA manifest/SW, and frontend toolchain (`frontend/package.json`).
- **Parca 7 (Data, Operations & Scrum Process, `DAT-01..15`, `OPS-01..24`, `PROC-01..10`)**:
  - Shared WAL SQLite connection layer (`master/dbconn.py`), versioned migrations (`master/migrate.py`), optional unified DB migration (`master/dbunify.py`), content-addressed blobstore, retention/erasure, FTS5 search, portability, `db_doctor`, scheduled backups, and ERD (`docs/plan-v2/erd.md`).
  - Structured JSON logging with `request_id`, Prometheus `/metrics`, deep `/ready` with runbook links, feature flags, error grouping, deterministic fake Ollama server (`master/fake_ollama.py`), power manager (`master/power_manager.py`), SBOM/quality-gate/load/chaos/demo scripts, 8 ADRs, 8 runbooks, MkDocs config, and Scrum automation scripts.

### Removed
- Removed external `litellm-gateway` container from `docker-compose.yml` in favor of the in-process Python gateway (`master/gateway/`, ADR-0001).

## [1.0.0] - 2026-10-21

### Added
- Sprint 1 baseline: FastAPI Master prototype, Ollama agent registration, requirements decomposition, 4-tab Turkish web UI, Scrum docs, and GitHub CI.

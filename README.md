# Distributed AI Software Development Platform

CM6453 Software Engineering Process and DevOps (instructor: Ensar Gül) — term project of **team6**.

A local-first, privacy-preserving web platform where a **master agent** decomposes software requirements into a DAG of development tasks, evaluates each teammate's local LLM capabilities, and orchestrates distributed execution, verification, conflict resolution, grounded research, document/slide/data studios, and an autonomous software factory. Managed with **Scrum** (5 sprints x 2 weeks), **Trello**, and **GitHub**.

## Core Principles

- **100% local and private by default.** Models run on the team's own computers with [Ollama](https://ollama.com). External cloud LLM escalation is disabled by default (`CLOUD_PROVIDERS_ENABLED=false`, [ADR-0001](docs/adr/0001-cloud-providers.md)).
- **No external LiteLLM proxy.** Inference is managed by an in-process Python LLM Gateway (`master/gateway/`) supporting Ollama and distributed team agents.
- **Evidence-driven reliability.** Hallucinations are controlled architecturally via hybrid FTS5 + vector RAG, web citations, deterministic tools (SymPy/pandas), Docker sandbox verification, confidence calibration, and explicit abstention ([docs/plan-v2/halusinasyon-mimarisi.md](docs/plan-v2/halusinasyon-mimarisi.md)).
- **Different open-source model per member.** Six open models across four vendors so capability-based routing and empirical comparison are meaningful ([docs/plan-v2/model-licenses-ethics.md](docs/plan-v2/model-licenses-ethics.md)).

## Team

| Name | Student no. | Role (assigned by the instructor) | Agent · Model |
|---|---|---|---|
| İshak Bostan | 2304010592 | Master agent's LLM (the master runs on this computer) | `uye1` · `qwen3.5:4b` (Alibaba) |
| Zeynep Duru Küçük | 2304010588 | Scrum Master · Trello, backend | `uye2` · `phi4-mini` (Microsoft) |
| Furkan Kaan Özbeyli | 2304010585 | Sub-agent interface | `uye3` · `llama3.2:3b` (Meta) |
| Semih Sarıca | 2304010590 | LLM model selection | `uye4` · `gemma4:e4b` (Google) |
| Işıl Karademir | 2304010607 | GitHub processes | `uye5` · `qwen2.5-coder:7b` (Alibaba) |
| Berfin Yiğit | 2304010589 | Web interface, dashboard | `uye6` · `qwen3:1.7b` (Alibaba) |

## Platform Capabilities (v2.0)

- **Web Interface (Turkish, 5 tabs + Personal Space):** *Yeni Proje*, *Projeler*, *Ajanlar*, *Pano*, *Asistan*, plus Personal Space (usage stats, profile, theme, personalization, memory, privacy/data controls) with XSS sanitization (`master/static/js/sanitizer.js`), PWA support, and zero external CDNs.
- **In-Process LLM Gateway & 8-Stage Orchestrator (`master/gateway/`, `master/orchestrator/`, `master/prompts/`):** Model registry synced with Ollama, capability/tier routing, input guards, DAG planner, tool registry, SSE v2 streaming, durable background jobs, artifact store, and strict output mode contracts.
- **Grounded RAG, Hallucination Control & ML Ops (`master/rag/`, `master/hallucination/`, `master/ml_ops/`, `eval/`):** Turkish FTS5 + versioned vector search, relevance gating, SearXNG + SSRF-safe web fetch, citation resolution, NLI & numeric verification, confidence calibration, abstention policy, and a 650-sample eval suite (`eval/run.py`).
- **Studios, Software Factory & Domain Engines (`master/studios/`, `master/factory/`, `master/games/`, `master/domains/`):** Multi-step cited Deep Research, quality-gated PPTX/DOCX/XLSX/PDF generation, statistical Data Science sandbox, signed Media pipeline, unified autonomous Software Factory (plan -> scaffold -> generate -> verify -> repair -> package), Game Studio, and strict no-fabricated-defaults domain engines.
- **Distributed Agent Orchestration (`master/distributed/`, `agent/`):** Versioned capability profiles, Thompson/UCB bandit assignment with explanations, pull-based task leasing & failover, per-agent tokens & result ownership, provenance tags, conflict resolution, performance comparison, and chaos scripts (`scripts/chaos/chaos_scenarios.ps1`).
- **Security, Unified Data & Operations (`master/access_control.py`, `master/sandbox/`, `master/dbconn.py`, `master/ops.py`):** Local session auth + RBAC + `owner_id` isolation, Fernet secret store, AES-encrypted backups, isolated Docker Python sandbox, shared SQLite WAL with versioned SQL migrations (`master/migrate.py`), content-addressed blobstore, structured JSON logging with `request_id`, Prometheus `/metrics`, deep `/ready` with runbook links (`docs/runbooks/`), and OpenAPI security matrix (`pytest -m security`).

## Architecture (Summary)

```text
Browser (Turkish UI, 5 tabs + Personal Space, PWA, XSS-sanitized)
   │ REST + SSE v2
Master (FastAPI, 127.0.0.1:8000 / Tailnet IP)
   ├─ Auth/RBAC · Secrets (Fernet) · Audit · Rate/Size Limits · /metrics · /ready
   ├─ 8-Stage Orchestrator -> RAG/Web (FTS5+Vec+SearXNG) · Studios · Factory · Verifier
   ├─ In-Process LLM Gateway -> Local Ollama + Distributed Agents (+ Opt-In Cloud Off)
   ├─ Unified SQLite WAL (dbconn + versioned migrations + blobstore)
   └─ Docker Code Sandbox (ephemeral, --network none, non-root)
   ▲ Pull-only agents (per-agent Bearer auth over Tailscale WireGuard mesh)
Agent x 6 (each member's machine) ── local Ollama on localhost:11434
```

Details: [docs/architecture.md](docs/architecture.md) · [docs/plan-v2/README.md](docs/plan-v2/README.md) · [docs/plan-v2/erd.md](docs/plan-v2/erd.md) · [docs/adr/](docs/adr/)

## Quick Start

### 1. Local Development (Single Command)
Requirements: Python 3.12, Ollama with `qwen3.5:4b` (and `bge-m3` for embeddings), `.env` created from `.env.example`.

- **Windows (PowerShell):**
  ```powershell
  .\scripts\dev.ps1
  ```
- **Linux / macOS:**
  ```bash
  ./scripts/dev.sh
  ```
- **Pre-Demo Readiness Checklist:**
  ```powershell
  .\scripts\demo_checklist.ps1
  ```

### 2. Docker Compose (Hardened Profiles, Zero LiteLLM)
```bash
docker compose --profile core up -d --build                  # Master (in-process gateway)
docker compose --profile core --profile agents up -d --build # Master + uye1 node agent
docker compose --profile staging up -d --build               # Master + staging agents uye2..uye6
docker compose --profile web-search up -d                    # Local SearXNG search engine
docker compose --profile sandbox build                       # Isolated Python sandbox image
```

Open `http://127.0.0.1:8000` (health: `/health`, deep readiness: `/ready`, metrics: `/metrics`).
Team members configure remote agents using [agent-node/README.md](agent-node/README.md).

## Testing, Verification & CI Gates

```powershell
# Lint
.\master\venv\Scripts\python.exe -m ruff check master agent scripts

# Full Master test suite
.\master\venv\Scripts\python.exe -m pytest master/tests/ -q

# Security & OpenAPI route authorization matrix (SEC-22)
.\master\venv\Scripts\python.exe -m pytest -m security master/tests/ -v

# Plan v2 integrity, module wiring & evidence-based progress
.\master\venv\Scripts\python.exe scripts/plan_tool.py check
.\master\venv\Scripts\python.exe scripts/plan_tool.py wiring --fail-on-new
.\master\venv\Scripts\python.exe scripts/plan_tool.py status

# Offline hallucination/grounding eval gate
.\master\venv\Scripts\python.exe eval/run.py --limit 50 --offline
```

## Repository Layout

| Path | Contents |
|---|---|
| `master/` | FastAPI Master: `gateway/`, `orchestrator/`, `rag/`, `hallucination/`, `ml_ops/`, `studios/`, `factory/`, `games/`, `domains/`, `distributed/`, `sandbox/`, `migrations/`, `static/`, `tests/` |
| `agent/` | Distributed agent service running on each member's computer + tests |
| `agent-node/` | Setup and startup scripts for team members (Windows / macOS / Linux) |
| `docker/` | Isolated execution sandbox Dockerfile (`docker/sandbox/`) |
| `eval/` | Golden QA, red-team, and retrieval datasets + offline/live eval runner |
| `frontend/` | Vite + TypeScript `checkJs` + Playwright incremental UI toolchain |
| `scripts/` | Dev launchers, `plan_tool.py`, `quality_gate.py`, SBOM, chaos/load bench, Scrum & academic report generators |
| `docs/` | `plan-v2/` (Master Plan v2 + `PROGRESS.json` + ERD), `adr/` (D1-D8), `runbooks/`, `scrum/` (traceability, DoD, demo script) |

## Process & Documentation

- **Master Plan v2 & Evidence Progress:** [docs/plan-v2/README.md](docs/plan-v2/README.md) · [docs/plan-v2/08-yol-haritasi-riskler.md](docs/plan-v2/08-yol-haritasi-riskler.md) · [docs/plan-v2/PROGRESS.json](docs/plan-v2/PROGRESS.json)
- **Scrum & Traceability:** [docs/scrum/traceability.md](docs/scrum/traceability.md) · [docs/scrum/definition-of-done.md](docs/scrum/definition-of-done.md) · [docs/scrum/demo-script.md](docs/scrum/demo-script.md)
- **Operations:** [docs/runbooks/README.md](docs/runbooks/README.md) · [CHANGELOG.md](CHANGELOG.md) · [CONTRIBUTING.md](CONTRIBUTING.md)

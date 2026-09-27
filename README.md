# Distributed AI Software Development Platform

CM6453 Software Engineering Process and DevOps (instructor: Ensar Gül) — term project of **team6**.

A web-based platform where a **master agent** turns a long software requirements document into a plan of development tasks and, over the course of the project, distributes those tasks to **LLM-based agents running on each team member's computer**, chosen by the measured capabilities of their models. The agents' results are integrated, tested and reviewed into a working web application. The project is managed with **Scrum** (5 sprints × 2 weeks), **Trello** and **GitHub**.

## Principles

- **100% local and private.** Every model runs on the team's own computers with [Ollama](https://ollama.com). No cloud LLM API is used and no document or prompt leaves the team's machines.
- **Open-source, pretrained models only.** No training or fine-tuning; the models are used for inference only.
- **Different model per member.** Six different open models from four vendors, so capability-based assignment is meaningful.

## Team

| Name | Student no. | Scrum role | Agent · model |
|---|---|---|---|
| İshak Bostan | 2304010592 | Developer · technical lead, hosts the master | `uye1` · Qwen3.5 4B (Alibaba) |
| Zeynep Duru Küçük | 2304010588 | Product Owner · Developer | `uye2` · Phi-4-mini 3.8B (Microsoft) |
| Furkan Kaan Özbeyli | 2304010585 | Developer | `uye3` · Llama 3.2 3B (Meta) |
| Semih Sarıca | 2304010590 | Developer | `uye4` · Gemma 4 E4B (Google) |
| Işıl Karademir | 2304010607 | Scrum Master · Developer | `uye5` · Qwen2.5-Coder 7B (Alibaba) |
| Berfin Yiğit | 2304010589 | Developer | `uye6` · Qwen3 1.7B (Alibaba) |

"Technical lead" is an informal responsibility (the master runs on İshak's computer), not a hierarchy: the Scrum Guide has no sub-teams or ranks among Developers.

## Status — Sprint 1 (24 Sep – 7 Oct 2026)

Working now:

- **Web interface** (Turkish) with four tabs: *Yeni Proje* (new project), *Projeler* (projects), *Ajanlar* (agents), *Asistan* (assistant).
- **Master agent prototype:** REST API, SQLite storage, agent registry.
- **Agent registration:** each agent reads its model's capabilities from Ollama (context window, vision, thinking, tools) and registers with the master using a shared token. The master never connects to agents (pull model).
- **Basic task decomposition:** the master's own model (Qwen3.5 4B) extracts a structured specification from a requirements document (entities, API endpoints, pages, non-functional requirements and **open questions** instead of guesses), then builds a dependency graph of tasks: requirements analysis → database / backend / frontend → testing + code review → integration → documentation. In Sprint 1 tasks are planned, not executed.
- **Assistant tab:** the earlier chat assistant (automatic model routing, content moderation, PDF/DOCX/TXT upload, tables and diagrams).

Measured on the master's computer (CPU only, ~32 GB RAM): the sample requirements document (`docs/examples/kutuphane-yonetim-sistemi.md`) is decomposed in about 45–55 s into 7 entities, 11–15 endpoints, 9 pages and 16 tasks.

Planned for Sprints 2–5 (see the [Product Backlog](docs/scrum/product-backlog.md)): capability evaluation and agent selection, task execution by agents, shared repository, integration, sandboxed automated testing, code-review agent, failure recovery and reassignment, dashboard and performance comparison.

## Architecture (summary)

```
Browser (Turkish UI)
   │ REST
Master (FastAPI, Docker, İshak's computer) ── local Ollama: Qwen3.5 4B for requirements analysis
   ├─ agent registry · decomposition · (Sprint 2+) capability evaluation and selection
   └─ SQLite
   ▲ agents connect to the master only (Bearer AGENT_TOKEN), over Tailscale (WireGuard, end-to-end encrypted)
Agent × 6 (each member's computer, Python) ── its own Ollama, listening on localhost only
```

Details: [docs/architecture.md](docs/architecture.md) · Requirements: [docs/SRS.md](docs/SRS.md)

## Quick start (master computer)

Requirements: Docker Desktop, Ollama with `qwen3.5:4b`, a `.env` file created from `.env.example` (`LITELLM_MASTER_KEY`, `AGENT_TOKEN`).

```bash
docker compose up -d --build          # master + LiteLLM gateway + uye1's agent
```

Open <http://localhost:8000>. To also run the other five members' agents on this computer until their own machines are connected:

```bash
docker compose --profile staging up -d --build
```

On Windows, `scripts\start-docker.ps1` starts Docker Desktop and works around a stale-socket start-up failure seen on the master's computer.

Team members set up their own agent with [agent-node/README.md](agent-node/README.md) (Turkish).

### Development and tests

```bash
cd master                              # or: cd agent
python -m venv .venv
.venv\Scripts\pip install -r requirements-dev.txt     # Linux/macOS: .venv/bin/pip
.venv\Scripts\python -m pytest tests/ -v
.venv\Scripts\python -m ruff check .
```

CI (GitHub Actions) runs lint and tests for `master` and `agent` and builds both Docker images on every pull request. `main` is protected: changes arrive through pull requests that need passing CI and one approving review.

## Repository layout

| Path | Contents |
|---|---|
| `master/` | Master agent: FastAPI app, decomposition, agent registry, web UI (`static/`), tests |
| `agent/` | Agent service that runs on each member's computer, tests |
| `agent-node/` | Setup and start scripts for members' computers (Windows / macOS / Linux) |
| `gateway/` | LiteLLM gateway configuration (Assistant tab only; removed in Sprint 3) |
| `docs/` | SRS, architecture, Scrum artifacts, example requirements document |
| `scripts/` | Helper scripts for the master computer |

## Process

- **Scrum:** roles, events, calendar, Product Backlog, Definition of Done and sprint records are in [docs/scrum/](docs/scrum/README.md).
- **Trello:** planning board with the same backlog items (IDs `PB-xx`).
- **GitHub:** branch → pull request → CI → review by a teammate; see [CONTRIBUTING.md](CONTRIBUTING.md) (Turkish).

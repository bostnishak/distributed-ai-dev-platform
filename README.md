# Distributed AI Software Development Platform

CM6453 Software Engineering Process and DevOps (instructor: Ensar Gül) — term project of **team6**.

A web-based platform where a **master agent** turns a long software requirements document into a plan of development tasks and, over the course of the project, distributes those tasks to **LLM-based agents running on each team member's computer**, chosen by the measured capabilities of their models. The agents' results are integrated, tested and reviewed into a working web application. The project is managed with **Scrum** (5 sprints × 2 weeks), **Trello** and **GitHub**.

## Principles

- **100% local and private.** Every model runs on the team's own computers with [Ollama](https://ollama.com). No cloud LLM API is used and no document or prompt leaves the team's machines.
- **Open-source, pretrained models only.** No training or fine-tuning; the models are used for inference only.
- **Different model per member.** Six different open models from four vendors, so capability-based assignment is meaningful.

## Team

| Name | Student no. | Role (assigned by the instructor) | Agent · model |
|---|---|---|---|
| İshak Bostan | 2304010592 | Master agent's LLM (the master runs on this computer) | `uye1` · Qwen3.5 4B (Alibaba) |
| Zeynep Duru Küçük | 2304010588 | Scrum Master · Trello, backend | `uye2` · Phi-4-mini 3.8B (Microsoft) |
| Furkan Kaan Özbeyli | 2304010585 | Sub-agent interface | `uye3` · Llama 3.2 3B (Meta) |
| Semih Sarıca | 2304010590 | LLM model selection | `uye4` · Gemma 4 E4B (Google) |
| Işıl Karademir | 2304010607 | GitHub processes | `uye5` · Qwen2.5-Coder 7B (Alibaba) |
| Berfin Yiğit | 2304010589 | Web interface, dashboard | `uye6` · Qwen3 1.7B (Alibaba) |

Every member is also a Developer. No Product Owner: the instructor asked the team not to have one, so the Developers agree on the Product Goal and the order of the Product Backlog together and accept work at the Sprint Review. Work outside a role title is listed as an additional responsibility in [docs/scrum/README.md](docs/scrum/README.md).

## Status — Sprint 1 (8 – 21 Oct 2026)

**Sprint 1 in progress** (8 – 21 Oct 2026, Week 1 of 2). Sprint Review and Retrospective scheduled for 21 October.

Working now (Sprint 1 increment):

- **Web interface** (Turkish) with four tabs: *Yeni Proje* (new project), *Projeler* (projects), *Ajanlar* (agents), *Asistan* (assistant).
- **Master agent prototype:** REST API, SQLite storage, agent registry.
- **Agent registration:** each agent reads its model's capabilities from Ollama (context window, vision, thinking, tools) and registers with the master using a shared token. The master never connects to agents (pull model).
- **Basic task decomposition:** the master's own model (Qwen3.5 4B) extracts a structured specification from a requirements document (entities, API endpoints, pages, non-functional requirements and **open questions** instead of guesses), then builds a dependency graph of tasks: requirements analysis → database / backend / frontend → testing + code review → integration → documentation. In Sprint 1 tasks are planned, not executed.
- **Assistant tab:** the earlier chat assistant (automatic model routing, content moderation, PDF/DOCX/TXT/CSV/XLSX upload, a built-in calculator, tables and diagrams, and an optional Run button for Python code that is off by default).

Measured on the master's computer (Intel Core i7-13700H, 32 GB RAM; Ollama runs the models on its NVIDIA RTX 4060 Laptop GPU with 8 GB): the three sample requirements documents in [`docs/examples/`](docs/examples/) are decomposed in 44–117 s into 7–13 entities, 11–25 endpoints, 9–10 pages and 15–19 tasks. Details: [Sprint 1 test report](docs/scrum/sprint-1/test-report.md).

Sprint 1 focus: requirements and architecture documents, platform web interface (4 tabs), master-agent prototype with SQLite and background analysis, agent service and registration, basic task decomposition, GitHub CI and collaboration setup, Trello board, and Tailscale network. See the [Product Backlog](docs/scrum/product-backlog.md) and [Sprint 1 backlog](docs/scrum/sprint-1/sprint-backlog.md).

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

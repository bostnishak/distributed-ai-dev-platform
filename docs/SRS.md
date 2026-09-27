# Software Requirements Specification

**Distributed AI Software Development Platform** — team6, CM6453 Software Engineering Process and DevOps

| | |
|---|---|
| Version | 1.0 (Sprint 1 draft; to be reviewed by the Product Owner, Zeynep Duru Küçük) |
| Date | 27 September 2026 |
| Source | Course term project document (`term project_updated.pdf`) and decisions of the team |

## 1. Introduction

### 1.1 Purpose

This document specifies the requirements of a web-based platform in which several computers, each running an LLM-based agent, collaborate to develop a software application from a long requirements document. It is the reference for the Product Backlog and for the acceptance of every sprint increment.

### 1.2 Scope

The platform receives a software requirements document, analyses it with a **master agent**, decomposes it into development tasks, assigns the tasks to agents according to the evaluated capabilities of their models, coordinates execution, and integrates, tests and reviews the results into a complete web application with documentation. The project itself is run with Scrum, Trello and GitHub.

Out of scope: training or fine-tuning models, cloud-hosted LLM services, deployment of the generated applications to production.

### 1.3 Definitions

| Term | Meaning |
|---|---|
| Master agent | Service on the master computer that analyses documents, plans and coordinates work |
| Agent | Service on a member's computer that runs that member's local model through Ollama |
| Capability profile | Measured scores of a model: coding, reasoning, context capacity, speed, structured output, vision |
| Specification (spec) | Structured result of the requirements analysis: entities, endpoints, pages, non-functional requirements, open questions |
| Task graph (DAG) | Tasks with dependencies; a task may start only when all tasks it depends on are done |
| Staging | Running a member's agent temporarily on the master computer until the member's own computer is connected |

### 1.4 Stakeholders

- **Instructor** (Ensar Gül) — evaluates the platform, process and documentation.
- **Scrum Team** (team6) — Product Owner, Scrum Master and Developers (see README).
- **Platform user** — a person who submits a requirements document and follows the generated project.

## 2. Overall description

### 2.1 Product perspective

The platform is a distributed system of one master and six agents, one per team member. Each agent runs a different open-source model (Qwen3.5 4B, Phi-4-mini, Llama 3.2 3B, Gemma 4 E4B, Qwen2.5-Coder 7B, Qwen3 1.7B). The members work from their homes, so the computers are connected through an end-to-end encrypted private network (Tailscale). The user interacts through a web interface served by the master.

### 2.2 Constraints

- C-1: Only free, open-source, pretrained models; no training or fine-tuning.
- C-2: All inference runs locally on the team's computers; no document or prompt may be sent to an external AI service.
- C-3: The platform must run on ordinary CPU-only laptops and desktops.
- C-4: Generated applications use HTML/CSS/JavaScript for the frontend, Python FastAPI for the backend and SQLite for the database.
- C-5: The project is managed with Scrum in five two-week sprints, using Trello and GitHub.

### 2.3 Assumptions

- A-1: Every member can install Ollama, Python and Tailscale on their computer.
- A-2: The master computer is running whenever agents should do work.
- A-3: Small local models produce simple applications and can make mistakes; the platform therefore validates, tests and reviews their output instead of trusting it.

## 3. Functional requirements

Status: **Done** = implemented and demonstrable, **Planned** = in the Product Backlog.

### 3.1 Web interface

| ID | Requirement | Sprint | Status |
|---|---|---|---|
| FR-1 | The user can submit a requirements document by pasting text or uploading PDF, DOCX, TXT or Markdown (up to 5 MB). | 1 | Done |
| FR-2 | The user can list projects and open a project to see its specification, task graph and status. | 1 | Done |
| FR-3 | The user can see the registered agents with their models and capabilities. | 1 | Done |
| FR-4 | The interface works on desktop, tablet and mobile browsers. | 1 | Done |
| FR-5 | A dashboard shows live progress, agent status and performance measurements. | 5 | Planned |

### 3.2 Master agent: analysis and decomposition

| ID | Requirement | Sprint | Status |
|---|---|---|---|
| FR-6 | The master analyses a requirements document with its local model and produces a structured specification (entities with fields, API endpoints, pages, actors, non-functional requirements). | 1 | Done |
| FR-7 | Ambiguous or missing information is reported as open questions rather than filled in by guessing. | 1 | Done |
| FR-8 | Documents that do not fit the model's context window are analysed in parts and the partial specifications are merged. | 1 | Done |
| FR-9 | The master decomposes the specification into tasks of the types requirements analysis, database, backend, frontend, testing, code review, integration and documentation, with dependencies forming an acyclic graph. | 1 | Done |
| FR-10 | Each task is classified by the capabilities it needs (for example coding-heavy or context-heavy). | 2 | Planned |

### 3.3 Agents and capability evaluation

| ID | Requirement | Sprint | Status |
|---|---|---|---|
| FR-11 | An agent registers with the master, reporting its member, model, context window, capabilities (vision, thinking, tools) and hardware. Registration requires the shared agent token. | 1 | Done |
| FR-12 | The master tracks agent status (online, busy, offline) through heartbeats. | 2 | Planned |
| FR-13 | The master evaluates every model with a benchmark set and stores a capability profile (coding, reasoning, context capacity, speed, structured-output reliability, vision). | 2 | Planned |
| FR-14 | The master assigns each task to the most suitable available agent using a documented scoring algorithm, never randomly, and records the reason for every assignment. | 2 | Planned |

### 3.4 Execution, integration and quality

| ID | Requirement | Sprint | Status |
|---|---|---|---|
| FR-15 | Agents fetch assigned tasks from the master, generate code or documents with their model and return the results. | 3 | Planned |
| FR-16 | Results are collected in a shared repository per project, with each agent's contribution committed under its name. | 3 | Planned |
| FR-17 | Tasks start only when their dependencies are done; independent tasks run in parallel. | 3 | Planned |
| FR-18 | The master integrates the results and checks that the frontend calls the endpoints the backend provides. | 4 | Planned |
| FR-19 | Generated tests run automatically in an isolated sandbox without network access. | 4 | Planned |
| FR-20 | A code-review agent, different from the author, reviews generated code; findings become fix tasks. | 4 | Planned |
| FR-21 | Failures (timeout, offline agent, invalid output) are detected; failed tasks are retried and reassigned to the next suitable agent. | 4 | Planned |
| FR-22 | Conflicting results (for example two agents writing the same file) are detected and resolved. | 4 | Planned |
| FR-23 | The end-to-end workflow produces a working web application and its documentation, downloadable as an archive. | 5 | Planned |
| FR-24 | The platform measures task durations, success rates and speed, and compares agents and models. | 5 | Planned |

### 3.5 Assistant (secondary feature)

| ID | Requirement | Sprint | Status |
|---|---|---|---|
| FR-25 | A chat assistant answers questions and writes code, routing each message automatically to a suitable model, blocking insulting messages and reading attached PDF/DOCX/TXT files. | before pivot | Done |
| FR-26 | The assistant uses the agent infrastructure and vision-capable agents analyse attached images. | 3 | Planned |

## 4. Non-functional requirements

| ID | Category | Requirement |
|---|---|---|
| NFR-1 | Privacy | No document, prompt or generated code is sent to a service outside the team's computers. Trello and GitHub hold planning data and source code only. |
| NFR-2 | Security | Agents authenticate with a shared secret; secrets are never committed. Agents open no listening ports and Ollama listens on localhost only. Network traffic between computers is end-to-end encrypted (Tailscale). Generated code is executed only inside an isolated sandbox (Sprint 4). |
| NFR-3 | Performance | On a CPU-only computer, analysing a requirements document of a few pages completes within minutes (measured: about 45–55 s for the sample document). The interface shows progress while it runs. |
| NFR-4 | Reliability | An agent retries registration until the master is reachable. A restart of the master marks interrupted analyses as failed so they can be re-run. |
| NFR-5 | Usability | The interface is in Turkish and usable on desktop, tablet and mobile browsers. |
| NFR-6 | Portability | The master runs with Docker Compose. Agents run with Python 3.10+ on Windows, macOS or Linux; Docker is not required on members' computers. |
| NFR-7 | Maintainability | Every change reaches `main` through a reviewed pull request with passing lint and unit tests (CI). |
| NFR-8 | Transparency | Every task assignment records why the agent was chosen (Sprint 2). Staging agents are labelled as running on the master computer. |

## 5. Traceability to the course document

| Course requirement | SRS items | Sprint |
|---|---|---|
| Web-based system; long requirements document as input | FR-1, FR-2 | 1 |
| Each computer runs an LLM-based agent; register agents and models | FR-11 | 1 |
| Master divides the document into smaller tasks (requirements analysis, frontend, backend, database, testing, integration, documentation) | FR-6 – FR-9 | 1 |
| Define the requirements and the general architecture | this document, [architecture.md](architecture.md) | 1 |
| Evaluate each model's capabilities; capability profiles; model evaluation | FR-13 | 2 |
| Task classification; agent selection; assignment by strengths, not randomly | FR-10, FR-14 | 2 |
| Task distribution; agent status monitoring | FR-12, FR-14 | 2 |
| Agents perform programming tasks; master–agent communication | FR-15 | 3 |
| Shared project repository; result collection; dependency management | FR-16, FR-17 | 3 |
| Code integration; automated testing; code-review agent | FR-18 – FR-20 | 4 |
| Error detection and recovery; conflict resolution; reassignment of failed tasks | FR-21, FR-22 | 4 |
| End-to-end workflow; dashboard; performance measurement; agent/model comparison | FR-5, FR-23, FR-24 | 5 |
| Documentation; final testing and demo | FR-23, [scrum/product-backlog.md](scrum/product-backlog.md) | 5 |
| Scrum, Trello, GitHub | [scrum/README.md](scrum/README.md) | 1 – 5 |

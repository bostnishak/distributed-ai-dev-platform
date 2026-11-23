# ADR-0001: In-Process LLM Gateway and Opt-In Cloud Providers (Decision D1)

- **Status:** Accepted
- **Date:** 2026-11-23
- **Related Plan Items:** GW-01, GW-19, OPS-14, SEC-11

## Context
The instructor required removing the external LiteLLM proxy server so the platform runs locally with minimal moving parts. Meanwhile, 4B-9B local Ollama models have natural reasoning limits on complex general-world tasks, while privacy and CM6453 course rules forbid unexpected external API calls.

## Decision
1. Replace the external `litellm-gateway` container with an **in-process Python package** (`master/gateway/`).
2. Primary inference providers are **local Ollama** and **distributed team agents**.
3. Optional external cloud adapters (OpenAI/Anthropic/Gemini-compatible) are supported behind an explicit configuration flag (`CLOUD_PROVIDERS_ENABLED=false` by default) and encrypted API keys (`master/secret_store.py`).

## Consequences
- Zero outbound cloud traffic occurs by default, verified by unit and security tests.
- Simpler deployment (`docker compose --profile core up` needs no proxy sidecar).
- Teams can enable tier escalation for hard workloads without changing orchestrator code.

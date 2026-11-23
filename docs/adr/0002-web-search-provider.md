# ADR-0002: Self-Hosted SearXNG as Primary Web Search Provider (Decision D2)

- **Status:** Accepted
- **Date:** 2026-11-23
- **Related Plan Items:** RAG-18, RES-01, OPS-06, SEC-10

## Context
Deep Research (`master/studios/research.py`) requires live web sources to ground claims and eliminate parametric-memory fabrication (Audit Finding F7). Paid search APIs create key-management friction for student teammates, while direct scraping is fragile.

## Decision
Use self-hosted **SearXNG** via the optional Docker Compose profile `web-search` (`127.0.0.1:8888`), with optional Brave/Tavily adapters behind encrypted secrets. Every fetched URL passes through `safe_fetch` SSRF validation (`SEC-10`) blocking private/loopback IP ranges and respecting domain/size limits.

## Consequences
- No paid API key is needed for local development or course demonstrations.
- Offline mode gracefully skips web calls when SearXNG is unreachable and transparently informs the user.

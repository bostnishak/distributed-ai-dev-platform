# ADR-0015: Extensibility, OpenAI Portability, 5-Language i18n, Signed Marketplace & MV3 SidePanel (Wave 3E)

- **Status:** Accepted
- **Date:** 2026-11-24

## Decision
1. **EPK-11 (`master/custom_agents.py`):** Versioned custom assistants with RAG/tool bindings and rollback.
2. **EPK-12 (`master/automation/webhooks.py`):** Constant-time HMAC-SHA256 webhook signing/verification and 5-field cron validation.
3. **EPK-13 (`master/mcp_server.py`):** JSON-RPC 2.0 MCP server with mandatory `human_approved=true` gate on side-effect tools + local-first connector probe.
4. **EPK-16 & EPK-27 (`master/static/js/i18n.js`):** 5 complete locales (`tr/en/de/fr/ar`) with RTL support and CI completeness test.
5. **EPK-17 (`master/telemetry_otel.py`):** W3C `traceparent` OTLP JSON span recording and latency summary.
6. **EPK-23 (`master/openai_compat.py` + `manifest.webmanifest`):** OpenAI-compatible `/v1/models`, `/v1/chat/completions`, `/v1/embeddings` + PWA manifest.
7. **EPK-24 (`master/updater.py`), EPK-28 (`master/notifications.py`), EPK-29 (`master/marketplace.py`), EPK-34 (`extensions/browser/`):** SemVer/SHA-256 updater, quiet-hours notification router, HMAC-signed marketplace with permission preview, and MV3 sidePanel extension with explicit consent.

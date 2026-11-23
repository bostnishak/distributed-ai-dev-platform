# ADR-0007: Containerized Docker Sandbox for Code Execution (Decision D7)

- **Status:** Accepted
- **Date:** 2026-11-23
- **Related Plan Items:** SEC-13, SEC-14, DEF-15, OPS-06

## Context
Audit Finding F2 identified direct host execution via `/exec`, `/run-code`, `start-server`, and `launch-exe`. Executing LLM-generated code on the master machine exposes the host OS and local files.

## Decision
Move untrusted code execution into an ephemeral **Docker sandbox container** (`docker/sandbox/Dockerfile`, image `platform-sandbox:latest`) with `--network none`, read-only root filesystem, dropped Linux capabilities, non-root user, and CPU/memory/PID/time limits (`master/sandbox/runner.py`). When Docker or `platform-sandbox:latest` is unavailable, report `sandbox_available: false` and refuse execution instead of falling back to the host.

## Consequences
- Zero arbitrary host command execution from generated code.
- Clear degraded status in `/ready` and `/api/assistant/config` on machines without Docker.

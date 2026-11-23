# ADR-0003: Local Accounts with Session Cookies and Optional Tailscale Identity (Decision D3)

- **Status:** Accepted
- **Date:** 2026-11-23
- **Related Plan Items:** SEC-01, SEC-02, SEC-03, SEC-04, SEC-22

## Context
Audit Findings F2 and F13 revealed unauthenticated mutating endpoints and cross-user access to conversations and memory compaction. The platform is accessed locally and over a private Tailscale tailnet.

## Decision
Adopt **local user accounts with HttpOnly signed session cookies** (`master/auth/`), role-based access control (`admin` / `member`), and resource ownership enforcement (`owner_id` / `user_id`). Support optional Tailscale identity headers (`Tailscale-User-Login`) only when trusted reverse-proxy mode is explicitly enabled. Enforce route coverage via the OpenAPI security matrix (`pytest -m security`, `SEC-22`).

## Consequences
- Every mutating endpoint is authenticated or explicitly audited in `test_security_matrix.py`.
- Cross-user reads/mutations return HTTP 403.
- No external OAuth/SaaS identity provider is required to run locally.

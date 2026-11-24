# ADR-0009: Multi-User Organizations, Invites, and Session-Derived RBAC (EPK-03)

- **Status:** Accepted
- **Date:** 2026-11-24

## Context
Single-profile local usage cannot safely isolate team workspaces, enforce least-privilege roles (`owner`, `admin`, `member`, `viewer`), or prevent cross-user IDOR when multiple users share a deployment.

## Decision
1. Add normalized `orgs`, `org_members`, and `org_invites` tables (`0014_orgs_invites_rbac.sql`) in `auth.db`.
2. Store only SHA-256 hashes of invite tokens; enforce single-use redemption and TTL expiry.
3. Enforce a centralized RBAC matrix (`owner > admin > member > viewer`) via `master/auth/orgs.py`.
4. Provide `resolve_effective_user_id` so authenticated sessions cannot spoof another user's `user_id` unless holding the `admin` role.

## Consequences
- Zero external identity provider dependencies; 100% offline/Tailscale compatible.
- Automated A->B IDOR tests verify cross-tenant isolation on every CI run.

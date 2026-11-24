# Runbook: Organizations, RBAC & RTBF Cryptographic Erasure

## 1. Investigating RBAC / Invite Issues
1. Inspect active sessions via `GET /api/security/sessions`.
2. Verify role permissions via `POST /api/auth/orgs/rbac/check`.
3. Rotate compromised invites by creating a new single-use invite (`POST /api/auth/orgs/{org_id}/invites`) with short TTL.

## 2. Executing & Auditing RTBF Erasure (KVKK / GDPR)
1. Call `POST /api/privacy/rtbf/{user_id}` with admin/owner credentials.
2. Confirm `"residual_hits": 0` and archive the returned `receipt_hmac`.
3. Re-verify historical erasure proofs anytime via `GET /api/privacy/rtbf/{user_id}/proofs` (only opaque `user_hash` is retained).

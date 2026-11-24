# ADR-0010 & ADR-0011: Contract-First OpenAPI & Privacy Field Encryption / RTBF Proofs (EPK-04, EPK-25)

- **Status:** Accepted
- **Date:** 2026-11-24

## Decision
1. **Contract-First OpenAPI (`EPK-04`):** Every registered FastAPI route carries an explicit response schema component and Turkish description attached via `master/api_schemas.py`. `scripts/gen_api_types.py` generates JSDoc typedefs into `master/static/js/api_types.js` checked by `node --check`.
2. **Field-Level Encryption (`EPK-25`):** Sensitive string fields are encrypted at rest via `master/privacy/field_crypto.py` using authenticated encryption (`Fernet` when `cryptography` is installed, or authenticated HKDF + XOR-CTR + HMAC-SHA256 with versioned prefix `v1:`). Any ciphertext tampering raises `ValueError`.
3. **Cryptographic RTBF Proofs (`EPK-25`):** `POST /api/privacy/rtbf/{user_id}` wipes all owned tables/files, verifies zero residual rows, and records an HMAC-signed receipt keyed only by `SHA-256(user_id)` so no plaintext PII survives erasure.

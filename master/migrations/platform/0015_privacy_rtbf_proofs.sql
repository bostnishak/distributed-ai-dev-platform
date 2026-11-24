-- EPK-25: Privacy engineering field encryption key metadata and cryptographic RTBF erasure receipts.
CREATE TABLE IF NOT EXISTS rtbf_erasure_proofs (
    proof_id TEXT PRIMARY KEY,
    user_hash TEXT NOT NULL,
    erased_at TEXT NOT NULL,
    removed_counts_json TEXT NOT NULL,
    residual_hits INTEGER NOT NULL DEFAULT 0,
    receipt_hmac TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_rtbf_proofs_user_hash ON rtbf_erasure_proofs(user_hash);

-- DAT-05: content-addressed blob store. One physical blob per SHA-256, many owner-scoped file records.
CREATE TABLE IF NOT EXISTS blobs (
    sha256     TEXT PRIMARY KEY,
    size       INTEGER NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS files (
    id         TEXT PRIMARY KEY,
    owner_id   TEXT NOT NULL,
    name       TEXT NOT NULL,
    mime       TEXT NOT NULL DEFAULT 'application/octet-stream',
    sha256     TEXT NOT NULL REFERENCES blobs(sha256),
    size       INTEGER NOT NULL,
    created_at TEXT NOT NULL,
    expires_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_files_owner ON files(owner_id, created_at);
CREATE INDEX IF NOT EXISTS idx_files_sha ON files(sha256);

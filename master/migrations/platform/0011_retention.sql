-- DAT-06: user-controlled retention. NULL days means keep forever.
CREATE TABLE IF NOT EXISTS retention_policies (
    owner_id   TEXT PRIMARY KEY,
    chat_days  INTEGER,
    usage_days INTEGER,
    file_days  INTEGER,
    updated_at TEXT NOT NULL
);

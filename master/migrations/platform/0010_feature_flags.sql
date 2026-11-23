-- OPS-11: features stay off until evidence says otherwise; per-user overrides sit beside the global default.
CREATE TABLE IF NOT EXISTS feature_flags (
    name        TEXT PRIMARY KEY,
    enabled     INTEGER NOT NULL DEFAULT 0,
    description TEXT NOT NULL DEFAULT '',
    updated_at  TEXT NOT NULL,
    updated_by  TEXT NOT NULL DEFAULT 'system'
);
CREATE TABLE IF NOT EXISTS feature_overrides (
    name     TEXT NOT NULL REFERENCES feature_flags(name) ON DELETE CASCADE,
    owner_id TEXT NOT NULL,
    enabled  INTEGER NOT NULL,
    PRIMARY KEY (name, owner_id)
);

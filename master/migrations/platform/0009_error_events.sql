-- OPS-19: unhandled exceptions grouped by fingerprint, so one recurring bug is one row with a count.
CREATE TABLE IF NOT EXISTS error_events (
    fingerprint TEXT PRIMARY KEY,
    kind        TEXT NOT NULL,
    message     TEXT NOT NULL,
    route       TEXT,
    sample      TEXT,
    count       INTEGER NOT NULL DEFAULT 1,
    first_seen  TEXT NOT NULL,
    last_seen   TEXT NOT NULL,
    request_id  TEXT
);
CREATE INDEX IF NOT EXISTS idx_error_events_last ON error_events(last_seen);

-- Wave 3B (EPK-01, EPK-02, EPK-15): Local web archive, eval annotation studio, and memory conflict queue.
CREATE TABLE IF NOT EXISTS web_archive (
    url_hash TEXT PRIMARY KEY,
    url TEXT NOT NULL,
    host TEXT NOT NULL,
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    content_hash TEXT NOT NULL,
    credibility_score REAL NOT NULL DEFAULT 0.7,
    fetched_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS eval_datasets (
    dataset_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    language TEXT NOT NULL DEFAULT 'tr',
    item_count INTEGER NOT NULL DEFAULT 0,
    version TEXT NOT NULL DEFAULT '1.0.0',
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS eval_annotations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    dataset_id TEXT NOT NULL,
    item_id TEXT NOT NULL,
    annotator_id TEXT NOT NULL,
    label TEXT NOT NULL,
    notes TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    UNIQUE(dataset_id, item_id, annotator_id)
);

CREATE TABLE IF NOT EXISTS memory_conflicts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,
    category TEXT NOT NULL,
    fact_key TEXT NOT NULL,
    existing_value TEXT NOT NULL,
    candidate_value TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'open',
    resolution TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    resolved_at TEXT
);

CREATE INDEX IF NOT EXISTS idx_web_archive_host ON web_archive(host);
CREATE INDEX IF NOT EXISTS idx_eval_ann_ds ON eval_annotations(dataset_id, item_id);
CREATE INDEX IF NOT EXISTS idx_mem_conflicts_user ON memory_conflicts(user_id, status);

-- Wave 3C (EPK-10, EPK-30, EPK-31, EPK-32, EPK-33): HA leases, idempotency, ML promotions, usage accounting & notebooks.
CREATE TABLE IF NOT EXISTS ha_leases (
    lease_key TEXT PRIMARY KEY,
    leader_id TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    term INTEGER NOT NULL DEFAULT 1,
    draining INTEGER NOT NULL DEFAULT 0,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS idempotent_results (
    idempotency_key TEXT PRIMARY KEY,
    task_id TEXT NOT NULL,
    agent_id TEXT NOT NULL,
    result_hash TEXT NOT NULL,
    committed_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS ml_model_promotions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    model_id TEXT NOT NULL,
    eval_score REAL NOT NULL,
    min_threshold REAL NOT NULL,
    stage TEXT NOT NULL,
    canary_pct INTEGER NOT NULL DEFAULT 0,
    actor TEXT NOT NULL DEFAULT 'admin',
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS accounting_ledger (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,
    model TEXT NOT NULL,
    tokens_in INTEGER NOT NULL DEFAULT 0,
    tokens_out INTEGER NOT NULL DEFAULT 0,
    latency_ms INTEGER NOT NULL DEFAULT 0,
    energy_wh REAL NOT NULL DEFAULT 0.0,
    day_utc TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS user_quotas (
    user_id TEXT PRIMARY KEY,
    daily_token_limit INTEGER NOT NULL DEFAULT 250000,
    daily_energy_wh_limit REAL NOT NULL DEFAULT 500.0,
    hard_enforce INTEGER NOT NULL DEFAULT 1,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS notebooks (
    notebook_id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    title TEXT NOT NULL,
    cells_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_accounting_user_day ON accounting_ledger(user_id, day_utc);
CREATE INDEX IF NOT EXISTS idx_notebooks_user ON notebooks(user_id);

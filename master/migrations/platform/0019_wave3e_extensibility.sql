-- Wave 3E (EPK-11, EPK-12, EPK-28, EPK-29): Custom versioned agents, webhooks, notifications & signed marketplace.
CREATE TABLE IF NOT EXISTS custom_agents (
    agent_id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    name TEXT NOT NULL,
    current_version INTEGER NOT NULL DEFAULT 1,
    instructions TEXT NOT NULL,
    rag_collections_json TEXT NOT NULL DEFAULT '[]',
    allowed_tools_json TEXT NOT NULL DEFAULT '[]',
    model_override TEXT NOT NULL DEFAULT '',
    shared_org_id TEXT NOT NULL DEFAULT '',
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS custom_agent_versions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    agent_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    version INTEGER NOT NULL,
    instructions TEXT NOT NULL,
    allowed_tools_json TEXT NOT NULL DEFAULT '[]',
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS webhook_deliveries (
    delivery_id TEXT PRIMARY KEY,
    event_type TEXT NOT NULL,
    target_url TEXT NOT NULL,
    signature_hmac TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'queued',
    attempts INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS notification_channels (
    channel_id TEXT PRIMARY KEY,
    kind TEXT NOT NULL,
    name TEXT NOT NULL,
    config_json TEXT NOT NULL DEFAULT '{}',
    quiet_start_hour INTEGER NOT NULL DEFAULT 23,
    quiet_end_hour INTEGER NOT NULL DEFAULT 7,
    rate_limit_per_hour INTEGER NOT NULL DEFAULT 20,
    enabled INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS marketplace_packages (
    package_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    version TEXT NOT NULL,
    kind TEXT NOT NULL,
    permissions_json TEXT NOT NULL DEFAULT '[]',
    sha256_digest TEXT NOT NULL,
    signature_hmac TEXT NOT NULL,
    installed INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL
);

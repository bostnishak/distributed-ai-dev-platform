-- DAT-14 / DAT-13: operational events are filtered by time and type; keep those scans on an index.
CREATE INDEX IF NOT EXISTS idx_events_created ON events(created_at);
CREATE INDEX IF NOT EXISTS idx_events_type ON events(event_type, created_at);
CREATE INDEX IF NOT EXISTS idx_tasks_project ON tasks(project_id, status);

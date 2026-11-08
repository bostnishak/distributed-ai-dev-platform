"""Sprint 4 tests: error recovery, conflict detection, review routing, contract check (PB-40/43/44/45/46)."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from unittest.mock import patch

import pytest

import db
from conflict_detector import detect_and_save
from selection import select_agent


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_agent(agent_id: str, status: str = "idle", last_seen_delta: int = 5) -> dict:
    last_seen = (datetime.now(UTC) - timedelta(seconds=last_seen_delta)).isoformat(timespec="seconds")
    return {
        "agent_id": agent_id,
        "context_length": 8192,
        "heartbeat_status": status,
        "last_seen_at": last_seen,
    }


def _scores(coding: float = 50.0) -> dict:
    return {"coding": coding, "reasoning": 50.0, "context": 50.0, "structured_output": 50.0, "speed": 50.0}


# ---------------------------------------------------------------------------
# PB-44 — Max attempts (requeue_task)
# ---------------------------------------------------------------------------

class TestMaxAttempts:
    def test_requeue_before_max_returns_requeued(self, tmp_path, monkeypatch):
        monkeypatch.setattr("config.DB_PATH", tmp_path / "test.db")
        db.init_db()
        pid = db.create_project("test", "doc", None)
        with db.connect() as conn:
            tid = conn.execute(
                "INSERT INTO tasks (project_id, key, stage, type, title, description, details, status, attempt) "
                "VALUES (?, 'T1', 1, 'backend', 'T', 'D', '{}', 'done', 2)",
                (pid,),
            ).lastrowid

        result = db.requeue_task(tid)
        assert result == "requeued"
        task = db.get_task(tid)
        assert task["status"] == "planned"

    def test_requeue_at_max_returns_failed(self, tmp_path, monkeypatch):
        monkeypatch.setattr("config.DB_PATH", tmp_path / "test.db")
        db.init_db()
        pid = db.create_project("test", "doc", None)
        with db.connect() as conn:
            tid = conn.execute(
                "INSERT INTO tasks (project_id, key, stage, type, title, description, details, status, attempt) "
                "VALUES (?, 'T1', 1, 'backend', 'T', 'D', '{}', 'done', ?)",
                (pid, db.MAX_ATTEMPTS),
            ).lastrowid

        result = db.requeue_task(tid)
        assert result == "failed"
        task = db.get_task(tid)
        assert task["status"] == "failed"

    def test_max_attempts_constant_is_positive(self):
        assert db.MAX_ATTEMPTS >= 1


# ---------------------------------------------------------------------------
# PB-45 — Conflict detection
# ---------------------------------------------------------------------------

class TestConflictDetection:
    def _setup_project_with_tasks(self, tmp_path, monkeypatch):
        monkeypatch.setattr("config.DB_PATH", tmp_path / "test.db")
        db.init_db()
        pid = db.create_project("conflict-test", "doc", None)
        with db.connect() as conn:
            t1 = conn.execute(
                "INSERT INTO tasks (project_id, key, stage, type, title, description, details, status, files) "
                "VALUES (?, 'T1', 1, 'backend', 'T1', 'D', '{}', 'done', ?)",
                (pid, json.dumps([{"path": "backend/main.py", "content": "# v1"}])),
            ).lastrowid
            t2 = conn.execute(
                "INSERT INTO tasks (project_id, key, stage, type, title, description, details, status) "
                "VALUES (?, 'T2', 2, 'backend', 'T2', 'D', '{}', 'done')",
                (pid,),
            ).lastrowid
        return pid, t1, t2

    def test_conflict_detected_for_same_path(self, tmp_path, monkeypatch):
        pid, t1, t2 = self._setup_project_with_tasks(tmp_path, monkeypatch)
        new_files = [{"path": "backend/main.py", "content": "# v2"}]
        conflicts = detect_and_save(pid, t2, new_files)
        assert len(conflicts) == 1
        assert conflicts[0]["file_path"] == "backend/main.py"
        assert conflicts[0]["task_id_a"] == t1
        assert conflicts[0]["task_id_b"] == t2

    def test_no_conflict_for_different_paths(self, tmp_path, monkeypatch):
        pid, t1, t2 = self._setup_project_with_tasks(tmp_path, monkeypatch)
        new_files = [{"path": "frontend/index.html", "content": "<html>"}]
        conflicts = detect_and_save(pid, t2, new_files)
        assert conflicts == []

    def test_no_conflict_for_empty_files(self, tmp_path, monkeypatch):
        pid, t1, t2 = self._setup_project_with_tasks(tmp_path, monkeypatch)
        conflicts = detect_and_save(pid, t2, [])
        assert conflicts == []

    def test_conflict_saved_to_db(self, tmp_path, monkeypatch):
        pid, t1, t2 = self._setup_project_with_tasks(tmp_path, monkeypatch)
        detect_and_save(pid, t2, [{"path": "backend/main.py", "content": "# v2"}])
        rows = db.list_conflicts(pid)
        assert len(rows) >= 1
        assert rows[0]["file_path"] == "backend/main.py"

    def test_resolve_conflict(self, tmp_path, monkeypatch):
        pid, t1, t2 = self._setup_project_with_tasks(tmp_path, monkeypatch)
        detect_and_save(pid, t2, [{"path": "backend/main.py", "content": "# v2"}])
        rows = db.list_conflicts(pid)
        ok = db.resolve_conflict(rows[0]["id"], "kept_latest")
        assert ok is True
        rows2 = db.list_conflicts(pid)
        assert rows2[0]["resolution"] == "kept_latest"
        assert rows2[0]["resolved_at"] is not None


# ---------------------------------------------------------------------------
# PB-43 — Review tasks never assigned to the author
# ---------------------------------------------------------------------------

class TestReviewExclusion:
    def test_review_excludes_author(self):
        agents = [_make_agent("a1"), _make_agent("a2"), _make_agent("a3")]
        scores = {a["agent_id"]: _scores() for a in agents}
        # Run many times to verify determinism
        for _ in range(10):
            selected, _ = select_agent("review", 0, agents, scores, exclude_agent_id="a1")
            assert selected != "a1"

    def test_review_excludes_only_requested(self):
        agents = [_make_agent("a1"), _make_agent("a2")]
        scores = {a["agent_id"]: _scores() for a in agents}
        selected, _ = select_agent("review", 0, agents, scores, exclude_agent_id="a1")
        assert selected == "a2"

    def test_non_review_tasks_not_affected_by_exclude(self):
        agents = [_make_agent("a1"), _make_agent("a2")]
        scores = {"a1": _scores(coding=90), "a2": _scores(coding=10)}
        selected, _ = select_agent("backend", 0, agents, scores)
        assert selected == "a1"

    def test_exclude_all_agents_returns_none(self):
        agents = [_make_agent("a1")]
        scores = {"a1": _scores()}
        selected, reason = select_agent("review", 0, agents, scores, exclude_agent_id="a1")
        assert selected is None


# ---------------------------------------------------------------------------
# PB-40 — Contract check
# ---------------------------------------------------------------------------

class TestContractCheck:
    def test_run_check_returns_expected_keys(self):
        from contract_check import run_check

        class FakeRoute:
            def __init__(self, path):
                self.path = path

        class FakeApp:
            routes = [FakeRoute("/api/agents"), FakeRoute("/health"), FakeRoute("/api/projects")]

        result = run_check(FakeApp())
        assert "frontend_routes" in result
        assert "backend_routes" in result
        assert "missing_in_backend" in result
        assert "not_called_by_frontend" in result
        assert "ok" in result
        assert "/api/agents" in result["backend_routes"]
        assert "/health" not in result["backend_routes"]  # only /api/ routes

    def test_ok_false_when_frontend_calls_missing_endpoint(self):
        from contract_check import run_check
        from unittest.mock import patch, MagicMock
        import contract_check as cc

        class FakeApp:
            routes = []

        with patch.object(cc, "_extract_frontend_routes", return_value={"/api/missing"}):
            result = run_check(FakeApp())
        assert result["ok"] is False
        assert "/api/missing" in result["missing_in_backend"]


# ---------------------------------------------------------------------------
# PB-46 — Fake agent scheduler tests (DAG with synthetic agents)
# ---------------------------------------------------------------------------

class TestFakeAgentScheduler:
    def test_blocked_task_released_when_dep_done(self, tmp_path, monkeypatch):
        monkeypatch.setattr("config.DB_PATH", tmp_path / "test.db")
        db.init_db()
        pid = db.create_project("dag-test", "doc", None)
        with db.connect() as conn:
            t1 = conn.execute(
                "INSERT INTO tasks (project_id, key, stage, type, title, description, details, status) "
                "VALUES (?, 'T1', 1, 'database', 'T1', 'D', '{}', 'planned')", (pid,)
            ).lastrowid
            t2 = conn.execute(
                "INSERT INTO tasks (project_id, key, stage, type, title, description, details, status) "
                "VALUES (?, 'T2', 2, 'backend', 'T2', 'D', '{}', 'blocked')", (pid,)
            ).lastrowid
            conn.execute(
                "INSERT INTO task_dependencies (task_id, depends_on_task_id) VALUES (?, ?)", (t2, t1)
            )
        # Mark T1 done
        db.submit_task_result_with_files(t1, "done", "output", None, None)
        db.update_task_validation(t1, "ok", "")
        released = db.release_all_ready_tasks()
        assert released >= 1
        task2 = db.get_task(t2)
        assert task2["status"] == "planned"

    def test_blocked_task_not_released_when_dep_not_done(self, tmp_path, monkeypatch):
        monkeypatch.setattr("config.DB_PATH", tmp_path / "test.db")
        db.init_db()
        pid = db.create_project("dag-test2", "doc", None)
        with db.connect() as conn:
            t1 = conn.execute(
                "INSERT INTO tasks (project_id, key, stage, type, title, description, details, status) "
                "VALUES (?, 'T1', 1, 'database', 'T1', 'D', '{}', 'planned')", (pid,)
            ).lastrowid
            t2 = conn.execute(
                "INSERT INTO tasks (project_id, key, stage, type, title, description, details, status) "
                "VALUES (?, 'T2', 2, 'backend', 'T2', 'D', '{}', 'blocked')", (pid,)
            ).lastrowid
            conn.execute(
                "INSERT INTO task_dependencies (task_id, depends_on_task_id) VALUES (?, ?)", (t2, t1)
            )
        # T1 is still planned → T2 must stay blocked
        released = db.release_all_ready_tasks()
        assert released == 0
        task2 = db.get_task(t2)
        assert task2["status"] == "blocked"

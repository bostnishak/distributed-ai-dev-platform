"""Sprint 3 tests: DAG scheduler (PB-34), result protocol (PB-31), validation (PB-33),
zip output (PB-32), and task execution prompt building (PB-30)."""

import json
import sys
from pathlib import Path

import pytest

# agent/ lives at project root, one level above master/
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "agent"))

import db
import validation as val_module
from agent import _build_task_prompt  # type: ignore[import]


@pytest.fixture()
def db_session(isolated_settings):
    """Initialize DB for tests that call db functions directly (no HTTP client)."""
    db.init_db()


# ---------------------------------------------------------------------------
# PB-34: DAG scheduler — release_all_ready_tasks
# ---------------------------------------------------------------------------

class TestDagScheduler:
    def _setup_two_tasks(self, status_t1: str, status_t2: str) -> tuple[int, int, int]:
        """Create project with T1→T2 dependency. Returns (project_id, t1_id, t2_id)."""
        project_id = db.create_project("DAG Test", "doc", None)
        with db.connect() as conn:
            c1 = conn.execute(
                "INSERT INTO tasks (project_id, key, stage, type, title, description, details, status) "
                "VALUES (?, 'T1', 1, 'requirements', 'Req', 'desc', '{}', ?)",
                (project_id, status_t1),
            )
            t1_id = c1.lastrowid
            c2 = conn.execute(
                "INSERT INTO tasks (project_id, key, stage, type, title, description, details, status) "
                "VALUES (?, 'T2', 2, 'database', 'DB', 'desc', '{}', ?)",
                (project_id, status_t2),
            )
            t2_id = c2.lastrowid
            conn.execute(
                "INSERT INTO task_dependencies (task_id, depends_on_task_id) VALUES (?, ?)",
                (t2_id, t1_id),
            )
        return project_id, t1_id, t2_id

    def test_blocked_task_released_when_dep_done(self, db_session):
        _, _, t2_id = self._setup_two_tasks("done", "blocked")
        released = db.release_all_ready_tasks()
        assert released == 1
        task = db.get_task(t2_id)
        assert task["status"] == "planned"

    def test_blocked_task_stays_blocked_when_dep_not_done(self, db_session):
        _, _, t2_id = self._setup_two_tasks("planned", "blocked")
        released = db.release_all_ready_tasks()
        assert released == 0
        task = db.get_task(t2_id)
        assert task["status"] == "blocked"

    def test_no_release_when_nothing_blocked(self, db_session):
        self._setup_two_tasks("done", "planned")
        released = db.release_all_ready_tasks()
        assert released == 0

    def test_idempotent(self, db_session):
        self._setup_two_tasks("done", "blocked")
        db.release_all_ready_tasks()
        released_again = db.release_all_ready_tasks()
        assert released_again == 0


# ---------------------------------------------------------------------------
# PB-31: Task result protocol — files + cancel endpoint
# ---------------------------------------------------------------------------

AGENT_PAYLOAD = {
    "agent_id": "uye-s3",
    "member_name": "Sprint3 Tester",
    "model": "test-model",
    "mode": "node",
    "context_length": 8192,
    "capabilities": ["completion"],
}


def _make_task(task_type: str = "backend") -> int:
    project_id = db.create_project("S3 Project", "doc", None)
    with db.connect() as conn:
        c = conn.execute(
            "INSERT INTO tasks (project_id, key, stage, type, title, description, details, status) "
            "VALUES (?, 'T1', 1, ?, 'Test', 'desc', '{}', 'planned')",
            (project_id, task_type),
        )
        return c.lastrowid


class TestResultProtocol:
    def test_submit_result_with_files(self, client, auth_headers):
        client.post("/api/agents/register", json=AGENT_PAYLOAD, headers=auth_headers)
        task_id = _make_task()
        resp = client.post(
            f"/api/tasks/{task_id}/result",
            json={
                "status": "done",
                "output": "x" * 50,
                "files": [{"path": "backend/main.py", "content": "def foo(): pass\n"}],
            },
            headers=auth_headers,
        )
        assert resp.status_code == 200
        task = db.get_task(task_id)
        assert task["status"] == "done"
        files = json.loads(task["files"])
        assert files[0]["path"] == "backend/main.py"

    def test_cancel_task_requeues(self, client, auth_headers):
        client.post("/api/agents/register", json=AGENT_PAYLOAD, headers=auth_headers)
        task_id = _make_task()
        resp = client.post(
            f"/api/tasks/{task_id}/cancel",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        task = db.get_task(task_id)
        assert task["status"] == "planned"
        assert task["assigned_to"] is None

    def test_submit_failed_task_requeues_on_validation_failure(self, client, auth_headers):
        client.post("/api/agents/register", json=AGENT_PAYLOAD, headers=auth_headers)
        task_id = _make_task("backend")
        resp = client.post(
            f"/api/tasks/{task_id}/result",
            json={"status": "done", "output": "x"},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        # Validation fails → task is requeued back to planned with validation_status reset
        task = db.get_task(task_id)
        assert task["status"] == "planned"
        assert task["assigned_to"] is None


# ---------------------------------------------------------------------------
# PB-33: Validation
# ---------------------------------------------------------------------------

class TestValidation:
    def test_empty_output_fails(self):
        ok, msg = val_module.validate_result("backend", "")
        assert not ok
        assert msg

    def test_short_output_fails(self):
        ok, _msg = val_module.validate_result("backend", "hi")
        assert not ok

    def test_valid_python_passes(self):
        code = "```python\ndef foo(x):\n    return x + 1\n```"
        ok, _ = val_module.validate_result("backend", code)
        assert ok

    def test_invalid_python_fails(self):
        code = "```python\ndef foo(\n```"
        ok, msg = val_module.validate_result("backend", code)
        assert not ok
        assert "sözdizimi" in msg.lower() or "syntax" in msg.lower()

    def test_non_code_task_passes_with_text(self):
        ok, _ = val_module.validate_result("documentation", "x" * 50)
        assert ok

    def test_extract_python_file(self):
        output = "Here is the code:\n```backend/app.py\nprint('hello')\n```"
        files = val_module.extract_files_from_output("backend", output)
        assert any(f["path"] == "backend/app.py" for f in files)

    def test_extract_fallback_python(self):
        output = "```python\ndef hello(): pass\n```"
        files = val_module.extract_files_from_output("backend", output)
        assert any("py" in f["path"] for f in files)


# ---------------------------------------------------------------------------
# PB-30: Task execution prompt building
# ---------------------------------------------------------------------------

class TestTaskPromptBuilding:
    def _task(self, task_type: str, details: dict | None = None) -> dict:
        return {
            "type": task_type,
            "title": f"{task_type} görevi",
            "description": "test açıklaması",
            "details": details or {},
        }

    def test_database_prompt_mentions_create_table(self):
        prompt = _build_task_prompt(self._task("database", {"entities": [{"name": "User"}]}))
        assert "CREATE TABLE" in prompt or "SQLite" in prompt

    def test_backend_prompt_mentions_fastapi(self):
        prompt = _build_task_prompt(self._task("backend"))
        assert "FastAPI" in prompt

    def test_frontend_prompt_mentions_html(self):
        prompt = _build_task_prompt(self._task("frontend"))
        assert "HTML" in prompt

    def test_testing_prompt_mentions_pytest(self):
        prompt = _build_task_prompt(self._task("testing"))
        assert "pytest" in prompt

    def test_unknown_type_returns_fallback(self):
        prompt = _build_task_prompt(self._task("unknown_type"))
        assert "unknown_type görevi" in prompt


# ---------------------------------------------------------------------------
# PB-32: ZIP output
# ---------------------------------------------------------------------------

class TestZipOutput:
    def test_zip_404_when_no_done_tasks(self, client):
        project_id = db.create_project("Zip Test", "doc", None)
        resp = client.get(f"/api/projects/{project_id}/output.zip")
        assert resp.status_code == 404

    def test_zip_returns_zip_with_done_tasks(self, client, auth_headers):
        project_id = db.create_project("Zip Project", "doc", None)
        with db.connect() as conn:
            conn.execute(
                "INSERT INTO tasks (project_id, key, stage, type, title, description, details, "
                "status, result, result_at) VALUES (?, 'T1', 1, 'backend', 'Test', 'desc', '{}', "
                "'done', 'def hello(): pass', datetime('now'))",
                (project_id,),
            )
        resp = client.get(f"/api/projects/${project_id}/output.zip")
        # The URL uses f-string interpolation bug above; test the correct URL:
        resp = client.get(f"/api/projects/{project_id}/output.zip")
        assert resp.status_code == 200
        assert resp.headers["content-type"] == "application/zip"

    def test_output_summary(self, client):
        project_id = db.create_project("Summary Test", "doc", None)
        resp = client.get(f"/api/projects/{project_id}/output")
        assert resp.status_code == 200
        data = resp.json()
        assert data["tasks_done"] == 0
        assert not data["has_output"]

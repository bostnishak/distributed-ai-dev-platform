"""Tests for PB-25: Task distribution queue API."""

import db

AGENT_PAYLOAD = {
    "agent_id": "uye-task1",
    "member_name": "Task Test Member",
    "model": "llama3:8b",
    "mode": "node",
    "context_length": 32768,
    "capabilities": ["completion"],
}


def _register_agent(client, auth_headers, payload=None):
    p = payload or AGENT_PAYLOAD
    resp = client.post("/api/agents/register", json=p, headers=auth_headers)
    assert resp.status_code == 200
    # Send fresh heartbeat so agent is online
    client.post(
        f"/api/agents/{p['agent_id']}/heartbeat",
        json={"status": "idle"},
        headers=auth_headers,
    )
    return resp.json()


def _create_project_and_task(task_type="backend"):
    """Insert a project and a planned task directly into the db."""
    project_id = db.create_project("Test Project", "test doc", None)
    import json
    with db.connect() as conn:
        cursor = conn.execute(
            "INSERT INTO tasks (project_id, key, stage, type, title, description, details, status) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (project_id, "T1", 1, task_type, "Test Task", "A test task", json.dumps({}), "planned"),
        )
        task_id = cursor.lastrowid
    return project_id, task_id


class TestNextTask:
    def test_returns_204_when_no_tasks(self, client, auth_headers):
        _register_agent(client, auth_headers)
        resp = client.get(
            f"/api/agents/{AGENT_PAYLOAD['agent_id']}/tasks/next",
            headers=auth_headers,
        )
        assert resp.status_code == 204

    def test_requires_auth(self, client):
        resp = client.get("/api/agents/uye-task1/tasks/next")
        assert resp.status_code == 401

    def test_unknown_agent_returns_404(self, client, auth_headers):
        resp = client.get(
            "/api/agents/nonexistent/tasks/next",
            headers=auth_headers,
        )
        assert resp.status_code == 404

    def test_returns_assigned_task(self, client, auth_headers):
        agent = _register_agent(client, auth_headers)
        project_id, task_id = _create_project_and_task()
        # Manually assign task to this agent
        db.assign_task(task_id, agent["agent_id"], {"reason": "test"})

        resp = client.get(
            f"/api/agents/{agent['agent_id']}/tasks/next",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == task_id


class TestSubmitResult:
    def test_submit_result_done(self, client, auth_headers):
        agent = _register_agent(client, auth_headers)
        project_id, task_id = _create_project_and_task()
        db.assign_task(task_id, agent["agent_id"], {"reason": "test"})

        resp = client.post(
            f"/api/tasks/{task_id}/result",
            json={"status": "done", "output": "Hello world", "tokens_per_second": 25.0},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["ok"] is True

        task = db.get_task(task_id)
        assert task["status"] == "done"
        assert task["result"] == "Hello world"
        assert task["tokens_per_second"] == 25.0

    def test_submit_result_requires_auth(self, client, auth_headers):
        project_id, task_id = _create_project_and_task()
        resp = client.post(
            f"/api/tasks/{task_id}/result",
            json={"status": "done", "output": "x"},
        )
        assert resp.status_code == 401

    def test_submit_result_unknown_task_returns_404(self, client, auth_headers):
        resp = client.post(
            "/api/tasks/99999/result",
            json={"status": "done", "output": "x"},
            headers=auth_headers,
        )
        assert resp.status_code == 404

    def test_submit_result_failed(self, client, auth_headers):
        agent = _register_agent(client, auth_headers)
        project_id, task_id = _create_project_and_task()
        db.assign_task(task_id, agent["agent_id"], {"reason": "test"})

        resp = client.post(
            f"/api/tasks/{task_id}/result",
            json={"status": "failed", "output": "Error occurred", "tokens_per_second": None},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        task = db.get_task(task_id)
        assert task["status"] == "failed"


class TestEvalStart:
    def test_eval_start_no_online_agents_returns_400(self, client, auth_headers):
        # Register agent then set last_seen_at to old timestamp → offline
        client.post("/api/agents/register", json=AGENT_PAYLOAD, headers=auth_headers)
        from datetime import UTC, datetime, timedelta
        stale = (datetime.now(UTC) - timedelta(minutes=5)).isoformat(timespec="seconds")
        with db.connect() as conn:
            conn.execute(
                "UPDATE agents SET last_seen_at = ? WHERE agent_id = ?",
                (stale, AGENT_PAYLOAD["agent_id"]),
            )
        resp = client.post("/api/eval/start", json={})
        assert resp.status_code == 400

    def test_eval_start_creates_tasks_for_online_agent(self, client, auth_headers):
        _register_agent(client, auth_headers)
        resp = client.post("/api/eval/start", json={})
        assert resp.status_code == 200
        data = resp.json()
        assert "eval_session_id" in data
        assert data["tasks_created"] > 0
        assert AGENT_PAYLOAD["agent_id"] in data["agents"]

    def test_eval_start_specific_agent(self, client, auth_headers):
        _register_agent(client, auth_headers)
        resp = client.post("/api/eval/start", json={"agent_id": AGENT_PAYLOAD["agent_id"]})
        assert resp.status_code == 200
        assert AGENT_PAYLOAD["agent_id"] in resp.json()["agents"]

    def test_eval_start_unknown_agent_returns_404(self, client, auth_headers):
        resp = client.post("/api/eval/start", json={"agent_id": "doesnotexist"})
        assert resp.status_code == 404


class TestLeaseExpiry:
    def test_expire_stale_leases(self, client, auth_headers):
        """Stale leases are reset by expire_stale_leases()."""
        from datetime import UTC, datetime, timedelta
        # Register an agent first so FK constraint is satisfied
        agent = _register_agent(client, auth_headers)
        project_id, task_id = _create_project_and_task()
        # Assign with an already-expired lease
        import json
        stale_expires = (datetime.now(UTC) - timedelta(minutes=10)).isoformat(timespec="seconds")
        with db.connect() as conn:
            conn.execute(
                "UPDATE tasks SET assigned_to = ?, assigned_at = ?, lease_expires_at = ?, "
                "assignment_reason = ? WHERE id = ?",
                (
                    agent["agent_id"],
                    datetime.now(UTC).isoformat(timespec="seconds"),
                    stale_expires,
                    json.dumps({"reason": "test"}),
                    task_id,
                ),
            )

        expired = db.expire_stale_leases()
        assert expired >= 1
        task = db.get_task(task_id)
        assert task["assigned_to"] is None
        assert task["lease_expires_at"] is None

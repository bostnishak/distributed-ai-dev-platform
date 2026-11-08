"""Sprint 5 tests: dashboard, perf metrics, security, e2e hardening (PB-50..56)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

_AGENT_PAYLOAD = {
    "agent_id": "s5-a1",
    "member_name": "Sprint5 Tester",
    "model": "qwen2.5:4b",
    "capabilities": ["coding", "documentation"],
}


# ---------------------------------------------------------------------------
# TestDashboardAPI  (PB-51)
# ---------------------------------------------------------------------------

class TestDashboardAPI:
    def test_dashboard_returns_expected_keys(self, client):
        resp = client.get("/api/dashboard")
        assert resp.status_code == 200
        body = resp.json()
        assert "agents" in body
        assert "projects" in body
        assert "recent_events" in body
        assert "perf" in body

    def test_dashboard_agents_counts_zero_before_register(self, client):
        resp = client.get("/api/dashboard")
        assert resp.status_code == 200
        data = resp.json()
        assert data["agents"]["total"] == 0

    def test_dashboard_agents_counts_after_register(self, client, auth_headers):
        client.post("/api/agents/register", json=_AGENT_PAYLOAD, headers=auth_headers)
        resp = client.get("/api/dashboard")
        assert resp.status_code == 200
        data = resp.json()
        assert data["agents"]["total"] == 1

    def test_events_endpoint_returns_list(self, client):
        resp = client.get("/api/events")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)


# ---------------------------------------------------------------------------
# TestPerfStats  (PB-52)
# ---------------------------------------------------------------------------

class TestPerfStats:
    def test_perf_stats_shape(self, client):
        resp = client.get("/api/perf/stats")
        assert resp.status_code == 200
        body = resp.json()
        assert isinstance(body, dict)

    def test_perf_stats_with_project_filter(self, client):
        resp = client.get("/api/perf/stats?project_id=999")
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# TestConflictsAPI  (PB-45 / PB-51)
# ---------------------------------------------------------------------------

class TestConflictsAPI:
    def _create_project(self, client, auth_headers):
        resp = client.post(
            "/api/projects",
            data={"name": "conflict-proj", "text": "Build a library system with book management and user auth."},
            headers=auth_headers,
        )
        assert resp.status_code == 202
        return resp.json()["id"]

    def test_list_conflicts_empty(self, client, auth_headers):
        project_id = self._create_project(client, auth_headers)
        resp2 = client.get(f"/api/projects/{project_id}/conflicts")
        assert resp2.status_code == 200
        assert resp2.json() == []

    def test_resolve_nonexistent_conflict(self, client, auth_headers):
        project_id = self._create_project(client, auth_headers)
        resp2 = client.post(
            f"/api/projects/{project_id}/conflicts/9999/resolve?resolution=manual"
        )
        assert resp2.status_code == 200
        assert resp2.json()["ok"] is False


# ---------------------------------------------------------------------------
# TestSecurityHardening  (PB-56)
# ---------------------------------------------------------------------------

class TestSecurityHardening:
    def test_missing_token_rejected(self, client):
        resp = client.post("/api/agents/register", json=_AGENT_PAYLOAD)
        assert resp.status_code == 401

    def test_wrong_token_rejected(self, client):
        resp = client.post(
            "/api/agents/register",
            json=_AGENT_PAYLOAD,
            headers={"Authorization": "Bearer wrong-token"},
        )
        assert resp.status_code == 401

    def test_valid_token_accepted(self, client, auth_headers):
        resp = client.post("/api/agents/register", json=_AGENT_PAYLOAD, headers=auth_headers)
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# TestE2EHardening  (PB-50)
# ---------------------------------------------------------------------------

class TestE2EHardening:
    def test_project_creation_returns_id(self, client, auth_headers):
        resp = client.post(
            "/api/projects",
            data={"name": "e2e-proj", "text": "Build a library system with book and user management."},
            headers=auth_headers,
        )
        assert resp.status_code == 202
        body = resp.json()
        assert "id" in body
        assert body["status"] == "analyzing"

    def test_project_appears_in_list(self, client, auth_headers):
        client.post(
            "/api/projects",
            data={"name": "e2e-list-proj", "text": "A system for managing library books and members."},
            headers=auth_headers,
        )
        resp = client.get("/api/projects")
        assert resp.status_code == 200
        projects = resp.json()
        assert any(p["name"] == "e2e-list-proj" for p in projects)

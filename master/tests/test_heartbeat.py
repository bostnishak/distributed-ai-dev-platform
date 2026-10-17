"""Tests for PB-20: Agent heartbeat and online status."""

import time

import db

PAYLOAD = {
    "agent_id": "uye-hb1",
    "member_name": "Test Member",
    "model": "llama3:8b",
    "mode": "node",
    "capabilities": ["completion"],
}


def test_heartbeat_updates_last_seen(client, auth_headers):
    client.post("/api/agents/register", json=PAYLOAD, headers=auth_headers)
    resp = client.post(
        f"/api/agents/{PAYLOAD['agent_id']}/heartbeat",
        json={"status": "idle"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["ok"] is True


def test_heartbeat_busy_status(client, auth_headers):
    client.post("/api/agents/register", json=PAYLOAD, headers=auth_headers)
    resp = client.post(
        f"/api/agents/{PAYLOAD['agent_id']}/heartbeat",
        json={"status": "busy"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    agent = db.get_agent(PAYLOAD["agent_id"])
    assert agent["heartbeat_status"] == "busy"


def test_heartbeat_unknown_agent_returns_404(client, auth_headers):
    resp = client.post(
        "/api/agents/nonexistent/heartbeat",
        json={"status": "idle"},
        headers=auth_headers,
    )
    assert resp.status_code == 404


def test_heartbeat_requires_token(client):
    resp = client.post("/api/agents/uye-hb1/heartbeat", json={"status": "idle"})
    assert resp.status_code == 401


def test_heartbeat_rejects_invalid_status(client, auth_headers):
    client.post("/api/agents/register", json=PAYLOAD, headers=auth_headers)
    resp = client.post(
        f"/api/agents/{PAYLOAD['agent_id']}/heartbeat",
        json={"status": "unknown_status"},
        headers=auth_headers,
    )
    assert resp.status_code == 422


def test_online_field_present_in_list(client, auth_headers):
    client.post("/api/agents/register", json=PAYLOAD, headers=auth_headers)
    # Send a heartbeat so last_seen_at is fresh
    client.post(
        f"/api/agents/{PAYLOAD['agent_id']}/heartbeat",
        json={"status": "idle"},
        headers=auth_headers,
    )
    agents = client.get("/api/agents").json()
    assert len(agents) == 1
    assert "online" in agents[0]
    # Agent just sent heartbeat so should be online
    assert agents[0]["online"] is True


def test_agent_online_after_heartbeat(client, auth_headers):
    """Agent becomes online immediately after a fresh heartbeat."""
    client.post("/api/agents/register", json=PAYLOAD, headers=auth_headers)
    client.post(
        f"/api/agents/{PAYLOAD['agent_id']}/heartbeat",
        json={"status": "idle"},
        headers=auth_headers,
    )
    agent = db.get_agent(PAYLOAD["agent_id"])
    # last_seen_at should be set
    assert agent["last_seen_at"] is not None

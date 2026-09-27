import config

PAYLOAD = {
    "agent_id": "uye4",
    "member_name": "Semih Sarıca",
    "model": "gemma4:e4b",
    "mode": "staging",
    "runtime": "docker",
    "hostname": "abc123",
    "os": "Linux 6.6",
    "cpu_count": 16,
    "ram_gb": 15.5,
    "model_family": "gemma4",
    "parameter_size": "8.0B",
    "quantization": "Q4_K_M",
    "context_length": 131072,
    "capabilities": ["completion", "vision", "audio", "thinking"],
    "agent_version": "0.1.0",
}


def test_register_requires_token(client):
    assert client.post("/api/agents/register", json=PAYLOAD).status_code == 401


def test_register_rejects_wrong_token(client):
    resp = client.post("/api/agents/register", json=PAYLOAD, headers={"Authorization": "Bearer nope"})
    assert resp.status_code == 401


def test_register_unavailable_without_configured_token(client, monkeypatch, auth_headers):
    monkeypatch.setattr(config, "AGENT_TOKEN", "")
    assert client.post("/api/agents/register", json=PAYLOAD, headers=auth_headers).status_code == 503


def test_register_validates_payload(client, auth_headers):
    bad = {**PAYLOAD, "agent_id": "Bad Id!"}
    assert client.post("/api/agents/register", json=bad, headers=auth_headers).status_code == 422


def test_register_and_list(client, auth_headers):
    resp = client.post("/api/agents/register", json=PAYLOAD, headers=auth_headers)
    assert resp.status_code == 200
    agent = resp.json()
    assert agent["agent_id"] == "uye4"
    assert agent["runtime"] == "docker"
    assert agent["capabilities"] == ["completion", "vision", "audio", "thinking"]
    assert agent["registered_at"] == agent["last_seen_at"]

    listed = client.get("/api/agents").json()
    assert [a["agent_id"] for a in listed] == ["uye4"]


def test_reregistration_updates_but_keeps_first_registration(client, auth_headers):
    first = client.post("/api/agents/register", json=PAYLOAD, headers=auth_headers).json()
    updated = client.post(
        "/api/agents/register", json={**PAYLOAD, "mode": "node", "ram_gb": 31.7}, headers=auth_headers
    ).json()
    assert updated["registered_at"] == first["registered_at"]
    assert updated["mode"] == "node"
    assert updated["ram_gb"] == 31.7
    assert len(client.get("/api/agents").json()) == 1

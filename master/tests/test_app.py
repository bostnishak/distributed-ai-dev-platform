import llm


def test_health_ok(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_ui_served_and_revalidated(client):
    resp = client.get("/")
    assert resp.status_code == 200
    assert "text/html" in resp.headers["content-type"]
    assert resp.headers["cache-control"] == "no-cache"


def test_static_assets_served(client):
    resp = client.get("/static/js/app.js")
    assert resp.status_code == 200
    assert resp.headers["cache-control"] == "no-cache"


def test_master_status_reports_model(client, monkeypatch):
    async def fake_status():
        return {"model": "qwen3.5:4b", "reachable": True, "model_available": True}

    monkeypatch.setattr(llm, "status", fake_status)
    resp = client.get("/api/master/status")
    assert resp.status_code == 200
    assert resp.json()["model_available"] is True

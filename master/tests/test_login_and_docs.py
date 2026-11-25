"""REQUIRE_LOGIN protects the API for multi-user installs; the interactive docs are off unless enabled."""

import pytest
from fastapi.testclient import TestClient

import app as master_app
import config

pytestmark = pytest.mark.unit


def test_api_requires_session_when_enabled(monkeypatch):
    monkeypatch.setattr(config, "REQUIRE_LOGIN", True)
    client = TestClient(master_app.app)
    assert client.get("/api/zzz-not-a-route").status_code == 401
    assert client.get("/api/auth/zzz").status_code != 401  # auth endpoints stay reachable


def test_api_open_by_default(monkeypatch):
    monkeypatch.setattr(config, "REQUIRE_LOGIN", False)
    assert TestClient(master_app.app).get("/api/zzz-not-a-route").status_code != 401


def test_docs_disabled_by_default():
    if config.ENABLE_DOCS:
        pytest.skip("docs enabled in this environment")
    assert TestClient(master_app.app).get("/docs").status_code == 404

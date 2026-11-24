"""Endpoints that run code, read secrets or delete data refuse remote callers without the admin token."""

import pytest
from fastapi.testclient import TestClient

import config

pytestmark = pytest.mark.security

REMOTE = ("100.84.159.80", 50000)

GUARDED = [
    ("POST", "/api/studio/workspaces/ws1/exec", {"command": "python --version"}),
    ("POST", "/api/studio/workspaces/ws1/launch-exe", None),
    ("POST", "/api/studio/workspaces/ws1/start-server", None),
    ("POST", "/api/studio/workspaces/ws1/build-exe", {}),
    ("POST", "/api/studio/workspaces/ws1/git", {"action": "status"}),
    ("DELETE", "/api/studio/workspaces/ws1", None),
    ("POST", "/api/assistant/run-code", {"code": "print(1)"}),
    ("GET", "/api/admin/backup.zip", None),
    ("GET", "/api/user/default/export", None),
    ("DELETE", "/api/user/default/data", None),
    ("DELETE", "/api/user/default", None),
    ("POST", "/api/mcp/connectors", {"name": "x", "url": "http://example.com"}),
    ("POST", "/api/mcp/connectors/abc/call", {"tool_name": "t", "arguments": {}}),
    ("DELETE", "/api/mcp/connectors/abc", None),
]


@pytest.fixture
def remote_client():
    import app as app_module

    with TestClient(app_module.app, client=REMOTE) as c:
        yield c


@pytest.mark.parametrize(("method", "path", "body"), GUARDED)
def test_remote_caller_without_token_is_refused(remote_client, method, path, body):
    resp = remote_client.request(method, path, json=body)
    assert resp.status_code == 403


@pytest.mark.parametrize(("method", "path", "body"), GUARDED)
def test_remote_caller_with_wrong_token_is_refused(remote_client, monkeypatch, method, path, body):
    monkeypatch.setattr(config, "ADMIN_TOKEN", "right-token")
    resp = remote_client.request(method, path, json=body, headers={"X-Admin-Token": "wrong-token"})
    assert resp.status_code == 403


def test_remote_caller_with_admin_token_passes_the_guard(remote_client, monkeypatch):
    monkeypatch.setattr(config, "ADMIN_TOKEN", "right-token")
    resp = remote_client.get("/api/admin/backup.zip", headers={"X-Admin-Token": "right-token"})
    assert resp.status_code == 200


def test_master_machine_itself_needs_no_token(client):
    assert client.get("/api/admin/backup.zip").status_code == 200


def test_unset_admin_token_never_matches_an_empty_header(remote_client, monkeypatch):
    monkeypatch.setattr(config, "ADMIN_TOKEN", "")
    resp = remote_client.get("/api/admin/backup.zip", headers={"X-Admin-Token": ""})
    assert resp.status_code == 403


def test_remote_caller_can_still_read_ordinary_pages(remote_client):
    assert remote_client.get("/health").status_code == 200
    assert remote_client.get("/api/agents").status_code == 200

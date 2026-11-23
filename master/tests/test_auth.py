"""SEC-01 & SEC-02: Authentication, Signed HttpOnly Sessions, RBAC, Revocation, Rate Limit & Tailscale Proxy SSO (12 scenarios)."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import app as master_app
import config
from auth import service as auth_service

pytestmark = pytest.mark.security


@pytest.fixture(autouse=True)
def isolated_auth_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(config, "DB_PATH", tmp_path / "platform.db")
    auth_service._LOGIN_FAILURES.clear()
    auth_service.init_auth_db()
    yield
    auth_service._LOGIN_FAILURES.clear()


def _client() -> TestClient:
    return TestClient(master_app.app)


def test_01_unauthenticated_me_returns_401():
    c = _client()
    assert c.get("/api/auth/me").status_code == 401


def test_02_initial_setup_creates_admin_and_sets_httponly_cookie():
    c = _client()
    assert c.get("/api/auth/status").json()["initialized"] is False
    r = c.post("/api/auth/setup", json={"username": "admin1", "password": "StrongPassword123!", "email": "admin@team6.local"})
    assert r.status_code == 200
    assert r.json()["user"]["role"] == "admin"
    set_cookie = r.headers.get("set-cookie", "").lower()
    assert "httponly" in set_cookie and "samesite=lax" in set_cookie
    assert c.get("/api/auth/me").json()["user"]["username"] == "admin1"


def test_03_second_setup_is_rejected_with_409():
    c = _client()
    assert c.post("/api/auth/setup", json={"username": "admin1", "password": "StrongPassword123!"}).status_code == 200
    assert c.post("/api/auth/setup", json={"username": "admin2", "password": "StrongPassword123!"}).status_code == 409


def test_04_login_and_logout_invalidate_session():
    c = _client()
    c.post("/api/auth/setup", json={"username": "admin1", "password": "StrongPassword123!"})
    assert c.post("/api/auth/logout").status_code == 200
    assert c.get("/api/auth/me").status_code == 401
    r = c.post("/api/auth/login", json={"username": "admin1", "password": "StrongPassword123!"})
    assert r.status_code == 200
    assert c.get("/api/auth/me").status_code == 200


def test_05_stolen_revoked_cookie_is_rejected():
    c = _client()
    c.post("/api/auth/setup", json={"username": "admin1", "password": "StrongPassword123!"})
    stolen_cookie = c.cookies.get(auth_service.SESSION_COOKIE_NAME)
    assert stolen_cookie
    c.post("/api/auth/logout")

    c2 = _client()
    c2.cookies.set(auth_service.SESSION_COOKIE_NAME, stolen_cookie)
    assert c2.get("/api/auth/me").status_code == 401


def test_06_tampered_cookie_signature_is_rejected():
    c = _client()
    c.post("/api/auth/setup", json={"username": "admin1", "password": "StrongPassword123!"})
    orig = c.cookies.get(auth_service.SESSION_COOKIE_NAME)
    assert orig
    c2 = _client()
    c2.cookies.set(auth_service.SESSION_COOKIE_NAME, orig[:-4] + "0000")
    assert c2.get("/api/auth/me").status_code == 401


def test_07_expired_session_is_rejected():
    user = auth_service.create_user("expired_u", "StrongPassword123!")
    _, signed = auth_service.create_session(user["id"], ttl_seconds=-10)
    c = _client()
    c.cookies.set(auth_service.SESSION_COOKIE_NAME, signed)
    assert c.get("/api/auth/me").status_code == 401


def test_08_login_rate_limiting_returns_429():
    c = _client()
    c.post("/api/auth/setup", json={"username": "admin1", "password": "StrongPassword123!"})
    c.post("/api/auth/logout")
    for _ in range(5):
        assert c.post("/api/auth/login", json={"username": "admin1", "password": "WrongPassword!"}).status_code == 401
    assert c.post("/api/auth/login", json={"username": "admin1", "password": "WrongPassword!"}).status_code == 429


def test_09_rbac_blocks_member_from_admin_user_creation():
    c = _client()
    c.post("/api/auth/setup", json={"username": "admin1", "password": "StrongPassword123!"})
    r_create = c.post("/api/auth/users", json={"username": "member1", "password": "MemberPass123!", "role": "member"})
    assert r_create.status_code == 200

    c_mem = _client()
    assert c_mem.post("/api/auth/login", json={"username": "member1", "password": "MemberPass123!"}).status_code == 200
    assert c_mem.post("/api/auth/users", json={"username": "member2", "password": "MemberPass123!"}).status_code == 403


def test_10_admin_password_reset_revokes_existing_sessions():
    c_admin = _client()
    c_admin.post("/api/auth/setup", json={"username": "admin1", "password": "StrongPassword123!"})
    c_admin.post("/api/auth/users", json={"username": "member1", "password": "OldPassword123!", "role": "member"})

    c_mem = _client()
    assert c_mem.post("/api/auth/login", json={"username": "member1", "password": "OldPassword123!"}).status_code == 200
    assert c_mem.get("/api/auth/me").status_code == 200

    assert c_admin.post("/api/auth/reset-password", json={"username": "member1", "new_password": "NewPassword456!"}).status_code == 200
    assert c_mem.get("/api/auth/me").status_code == 401
    assert c_mem.post("/api/auth/login", json={"username": "member1", "password": "NewPassword456!"}).status_code == 200


def test_11_tailscale_header_spoofing_rejected_when_untrusted(monkeypatch: pytest.MonkeyPatch):
    auth_service.create_user("ishak", "StrongPassword123!", email="ishak@team6.ts.net")
    monkeypatch.setenv("TRUSTED_TAILSCALE_PROXY", "false")
    c = _client()
    assert c.get("/api/auth/tailscale-me", headers={"Tailscale-User-Login": "ishak@team6.ts.net"}).status_code == 403
    # Even if trusted proxy is enabled, non-loopback client host is rejected directly
    assert auth_service.resolve_tailscale_user("ishak@team6.ts.net", client_host="100.64.0.9", trusted_proxy=True) is None


def test_12_tailscale_trusted_loopback_proxy_maps_user():
    auth_service.create_user("ishak", "StrongPassword123!", email="ishak@team6.ts.net")
    resolved = auth_service.resolve_tailscale_user("ishak@team6.ts.net", client_host="127.0.0.1", trusted_proxy=True)
    assert resolved is not None
    assert resolved["username"] == "ishak"
    assert resolved["via"] == "tailscale"

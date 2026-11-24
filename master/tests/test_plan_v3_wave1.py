"""Plan v3 Wave 1 verification tests: HDR-01..06, ARY-01..07, ALT-01..15."""

from __future__ import annotations

import pathlib
import time

import pytest
from fastapi.testclient import TestClient

import app as master_app
import config
import security_middleware
from auth import service as auth_service

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
STATIC_DIR = REPO_ROOT / "master" / "static"


@pytest.fixture()
def isolated_client(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DATA_DIR", tmp_path)
    security_middleware._API_RATE_LIMITER._state.clear()
    with TestClient(master_app.app) as c:
        yield c


@pytest.mark.security
def test_hdr01_to_hdr06_security_headers_csp_cache_and_rate_limit(isolated_client):
    """HDR-01..06: HSTS, COOP, CORP, strict CSP without unsafe-inline, Cache-Control: no-store, and 429 rate limit."""
    r = isolated_client.get("/")
    assert r.status_code == 200
    h = {k.lower(): v for k, v in r.headers.items()}
    assert "strict-transport-security" in h
    assert h.get("cross-origin-opener-policy") == "same-origin"
    assert h.get("cross-origin-resource-policy") == "same-origin"
    assert "unsafe-inline" not in h.get("content-security-policy", "")

    api_r = isolated_client.get("/api/agents")
    assert api_r.headers.get("cache-control") == "no-store"

    # Trigger rate limit burst (> 80 rapid requests to the same API path)
    codes = [isolated_client.get("/api/agents").status_code for _ in range(95)]
    assert 429 in codes


@pytest.mark.security
def test_alt07_alt08_alt14_user_idor_and_role_enforcement(isolated_client):
    """ALT-07, ALT-08, ALT-14: Nonexistent PUT profile -> 404; once auth is active, unauth -> 401 and A->B -> 403."""
    # Even before auth setup, PUT to nonexistent arbitrary ID must NOT create it
    r_missing = isolated_client.put("/api/user/zzz-nonexistent/profile", json={"display_name": "Evil"})
    assert r_missing.status_code == 404

    # Initialize admin + regular viewer user
    auth_service.init_auth_db()
    auth_service.create_user("alice", "AlicePass123!", role="developer")
    auth_service.create_user("bob", "BobPass12345!", role="viewer")

    # Unauthenticated calls to all /api/user/* routes return 401
    for path in (
        "/api/user/profiles",
        "/api/user/alice/profile",
        "/api/user/alice/stats",
        "/api/user/alice/memories",
        "/api/user/alice/conversations",
        "/api/user/alice/history/search?q=x",
        "/api/user/alice/personalization-preview",
    ):
        assert isolated_client.get(path).status_code == 401, path

    # Login as viewer bob
    login = isolated_client.post("/api/auth/login", json={"username": "bob", "password": "BobPass12345!"})
    assert login.status_code == 200
    # Cross-user A->B read is 403, listing all profiles is 403, mutating with viewer role is 403
    assert isolated_client.get("/api/user/alice/profile").status_code == 403
    assert isolated_client.get("/api/user/profiles").status_code == 403
    assert isolated_client.post("/api/projects", json={"title": "blocked"}).status_code == 403


@pytest.mark.unit
def test_alt09_alt10_alt01_alt02_alt03_system_fixes(isolated_client):
    """ALT-01..03, ALT-09, ALT-10: No absolute path leak, cached gateway models <100ms, OCR & local badge in health wizard."""
    es = isolated_client.get("/api/assistant/enterprise-status")
    assert es.status_code == 200
    dpo_file = str((es.json().get("llmops") or {}).get("dpo_file") or "")
    assert ":\\" not in dpo_file and not dpo_file.startswith("/")

    # Second cached call to /api/gateway/models must be < 100 ms
    isolated_client.get("/api/gateway/models")
    t0 = time.perf_counter()
    m2 = isolated_client.get("/api/gateway/models")
    elapsed_ms = (time.perf_counter() - t0) * 1000
    assert m2.status_code == 200
    assert m2.json().get("cached") is True
    assert elapsed_ms < 100.0

    hw = isolated_client.get("/api/ux/health-wizard")
    assert hw.status_code == 200
    body = hw.json()
    check_ids = {c["id"] for c in body["checks"]}
    assert {"ocr", "web_search", "agents"}.issubset(check_ids)
    assert body["execution_mode"] in ("local_only", "distributed")


@pytest.mark.unit
def test_ary01_to_ary07_and_alt05_alt06_alt12_alt15_static_guarantees():
    """ARY-01..07, ALT-05, ALT-06, ALT-12, ALT-15: Accessibility hooks, reduced motion, titles, labels, and tool configs."""
    html = (STATIC_DIR / "index.html").read_text(encoding="utf-8")
    assert "<script>" not in html  # HDR-04: no inline script
    assert 'aria-label="Mesajınızı yazın"' in html  # ARY-04
    assert 'id="fileInput"' in html and 'aria-label="Sohbet dosyası yükle"' in html  # ARY-05
    assert 'id="main" tabindex="-1"' in html  # ARY-07

    app_js = (STATIC_DIR / "js" / "app.js").read_text(encoding="utf-8")
    assert "document.title =" in app_js  # ARY-01
    assert "syncHeroHeadingLevel" in app_js  # ARY-02
    assert "mainEl.focus" in app_js  # ARY-07

    hub_js = (STATIC_DIR / "js" / "hub.js").read_text(encoding="utf-8")
    assert "for: fid" in hub_js and "'aria-label': labelText" in hub_js  # ARY-03

    theme_css = (STATIC_DIR / "css" / "theme.css").read_text(encoding="utf-8")
    assert "@media (prefers-reduced-motion: reduce)" in theme_css  # ALT-12
    assert "min-height: 40px" in theme_css  # ARY-06

    pkg = (REPO_ROOT / "frontend" / "package.json").read_text(encoding="utf-8")
    assert '"node --test tests/"' in pkg  # ALT-05

    req_dev = (REPO_ROOT / "master" / "requirements-dev.txt").read_text(encoding="utf-8")
    assert "pytest-cov" in req_dev and "diff-cover" in req_dev  # ALT-06

    pytest_ini = (REPO_ROOT / "pytest.ini").read_text(encoding="utf-8")
    for marker in ("unit:", "contract:", "integration:", "e2e:", "slow:", "security:"):
        assert marker in pytest_ini  # ALT-15

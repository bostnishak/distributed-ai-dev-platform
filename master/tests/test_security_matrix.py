"""SEC-22: Automated OpenAPI Unauthorized Access Matrix & Threat Model Verification (`pytest -m security`).

Inspects every mutating route (`POST`, `PUT`, `DELETE`, `PATCH`) registered on `master/app.py`.
Any new mutating route that lacks an explicit auth dependency (`require_local_or_admin`,
`require_agent_auth`, `require_agent_token`) AND is not explicitly reviewed in the
documented user-session allowlist immediately fails CI.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.routing import APIRoute

import app as master_app

REPO_ROOT = Path(__file__).resolve().parents[2]
MASTER_DIR = REPO_ROOT / "master"

pytestmark = pytest.mark.security

_AUTH_DEP_NAMES = frozenset({
    "require_local_or_admin",
    "require_agent_auth",
    "require_agent_token",
    "require_authenticated_user",
    "require_admin_session",
})

# Explicitly audited same-origin interactive user routes (protected by SEC-16 CSRF + Same-Origin middleware).
# Any NEW mutating route added without an auth dependency will FAIL test_no_unprotected_mutating_routes!
_AUDITED_USER_SESSION_MUTATIONS = frozenset({
    ("POST", "/api/auth/setup"),
    ("POST", "/api/auth/login"),
    ("POST", "/api/auth/logout"),
    ("POST", "/api/projects"),
    ("POST", "/api/projects/{project_id}/reanalyze"),
    ("DELETE", "/api/projects/{project_id}"),
    ("POST", "/api/eval/start"),
    ("POST", "/api/assistant/chat"),
    ("POST", "/api/assistant/chat/stream"),
    ("POST", "/api/assistant/transcribe"),
    ("POST", "/api/cnc/analyze"),
    ("POST", "/api/cnc/jobs/{job_id}/balloons"),
    ("DELETE", "/api/cnc/jobs/{job_id}/balloons/{balloon_no}"),
    ("PUT", "/api/cnc/jobs/{job_id}/balloons/{balloon_no}"),
    ("POST", "/api/studio/generate"),
    ("POST", "/api/studio/workspaces/{id}/iterate"),
    ("PUT", "/api/studio/workspaces/{id}/file"),
    ("DELETE", "/api/studio/workspaces/{id}/file"),
    ("POST", "/api/studio/workspaces/{id}/restore/{version}"),
    ("POST", "/api/user/profiles"),
    ("PUT", "/api/user/{user_id}/profile"),
    ("DELETE", "/api/user/{user_id}"),
    ("POST", "/api/user/{user_id}/memories"),
    ("DELETE", "/api/user/{user_id}/memories/{fact_id}"),
    ("PUT", "/api/user/{user_id}/chats/{chat_id}"),
    ("DELETE", "/api/user/{user_id}/chats/{chat_id}"),
    ("DELETE", "/api/user/{user_id}/data"),
    ("POST", "/api/memory/facts"),
    ("DELETE", "/api/memory/facts/{fact_id}"),
})


def _route_dep_names(route: APIRoute) -> set[str]:
    names: set[str] = set()
    for dep in route.dependant.dependencies:
        if dep.call is not None:
            names.add(getattr(dep.call, "__name__", ""))
    return names


def test_sec22_no_unprotected_mutating_routes():
    """Every mutating route in OpenAPI must carry an auth guard or be explicitly audited."""
    unclassified: list[tuple[str, str]] = []
    for route in master_app.app.routes:
        if not isinstance(route, APIRoute):
            continue
        dep_names = _route_dep_names(route)
        has_auth = bool(dep_names & _AUTH_DEP_NAMES)
        for method in sorted(route.methods or set()):
            if method not in {"POST", "PUT", "DELETE", "PATCH"}:
                continue
            if not has_auth and (method, route.path) not in _AUDITED_USER_SESSION_MUTATIONS:
                unclassified.append((method, route.path))
    assert unclassified == [], f"Unprotected/unaudited mutating routes detected (SEC-22): {unclassified}"


def test_sec22_threat_model_covers_all_six_trust_boundaries():
    tm = (REPO_ROOT / "docs" / "security" / "threat-model.md").read_text(encoding="utf-8")
    for boundary in (
        "Güven Sınırı 1: Tarayıcı",
        "Güven Sınırı 2: Master API",
        "Güven Sınırı 3: Master <-> Dağıtık Ajan",
        "Güven Sınırı 4: Master <-> Yerel Ollama",
        "Güven Sınırı 5: Master <-> Kod Çalıştırma Sandbox",
        "Güven Sınırı 6: Master <-> Harici Ağ",
    ):
        assert boundary in tm, f"Missing trust boundary in threat-model.md: {boundary}"

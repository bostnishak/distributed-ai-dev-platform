"""Role-to-action matrix in one file (SEC-04).

Every API route is classified into one action by its method and path; each action lists the roles
allowed to perform it. A route that matches no rule fails the policy test, so a new route cannot be
added without a decision about who may call it.
"""

from __future__ import annotations

import re

from fastapi import HTTPException, Request

from auth import service

ROLES = ("admin", "developer", "analyst", "viewer", "agent")

# action -> roles allowed
MATRIX: dict[str, frozenset[str]] = {
    "public": frozenset(ROLES),
    "read": frozenset({"admin", "developer", "analyst", "viewer"}),
    "write": frozenset({"admin", "developer", "analyst"}),
    "generate": frozenset({"admin", "developer", "analyst"}),
    "execute": frozenset({"admin", "developer"}),
    "delete": frozenset({"admin", "developer"}),
    "admin": frozenset({"admin"}),
    "agent": frozenset({"agent", "admin"}),
}

# (method regex, path regex, action); first match wins.
_RULES: tuple[tuple[str, str, str], ...] = (
    (".*", r"^/(health|ready|metrics|docs|openapi\.json|redoc)$", "public"),
    (".*", r"^/api/auth/", "public"),
    (".*", r"^/api/agents/(register|heartbeat|tasks|results|poll|telemetry)", "agent"),
    (".*", r"^/api/(admin|backup|audit|features|ops)", "admin"),
    (".*", r"^/api/(mcp|connectors)", "admin"),
    (".*", r".*/(exec|run-code|launch-exe|start-server|build-exe|git)(/|$)", "execute"),
    ("DELETE", r".*", "delete"),
    ("GET|HEAD|OPTIONS", r".*", "read"),
    ("POST|PUT|PATCH", r"^/api/(assistant|projects|studio|studios|research|presentations|documents|games|domains|orchestrator|rag|memory|ux|ml|hallucination|eval|cnc|dist|tasks|output|perf|user|agents|security|tools|productivity)", "write"),
)
_COMPILED = tuple((re.compile(m), re.compile(p), a) for m, p, a in _RULES)


def action_for(method: str, path: str) -> str | None:
    for method_re, path_re, action in _COMPILED:
        if method_re.fullmatch(method.upper()) and path_re.match(path):
            return action
    return None


def can(role: str, method: str, path: str) -> bool:
    normalized = "developer" if role == "member" else role
    action = action_for(method, path)
    return action is not None and normalized in MATRIX[action]


def require_role(*roles: str):
    """FastAPI dependency: the signed-in user must hold one of `roles` (or be admin)."""
    def dependency(request: Request) -> dict:
        user = service.get_session_user(request.cookies.get(service.SESSION_COOKIE_NAME))
        if not user:
            raise HTTPException(status_code=401, detail="Oturum gerekli.")
        if user["role"] != "admin" and user["role"] not in roles:
            raise HTTPException(status_code=403, detail="Bu işlem için rolünüz yetmiyor.")
        return user

    return dependency

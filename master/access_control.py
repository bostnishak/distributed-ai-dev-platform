"""Access guard for endpoints that run code, read secrets or delete shared data.

The web UI has no login yet, and the master listens on all interfaces so teammates can reach it
over Tailscale. These routes therefore work from the master's own machine, while a remote caller
must send the ``X-Admin-Token`` header matching ``ADMIN_TOKEN``. With no token configured, remote
callers are always refused.
"""

import hmac

from fastapi import HTTPException, Request

import config

# "testclient" is the peer name Starlette's TestClient reports.
LOCAL_HOSTS = frozenset({"127.0.0.1", "::1", "localhost", "testclient"})


def _session_is_admin(request: Request) -> bool:
    """A signed-in user whose role is admin may use these routes from any address (SEC-05)."""
    try:
        from auth import service

        user = service.get_session_user(request.cookies.get(service.SESSION_COOKIE_NAME))
    except Exception:  # an unreadable auth store must never grant access
        return False
    return bool(user and user.get("role") == "admin")


def require_local_or_admin(request: Request) -> None:
    host = request.client.host if request.client else ""
    if _session_is_admin(request):
        return
    if host in LOCAL_HOSTS and config.LOOPBACK_PRIVILEGE:
        return
    expected = config.ADMIN_TOKEN
    supplied = request.headers.get("x-admin-token", "")
    if expected and hmac.compare_digest(supplied.encode(), expected.encode()):
        return
    try:
        from audit_log import AuditTrail

        AuditTrail().append_event(
            actor=host or "unknown",
            action="ACCESS_DENIED",
            payload={"path": str(request.url.path), "method": request.method},
        )
    except Exception as _exc:
        import logging

        logging.getLogger(__name__).debug("Recoverable error suppressed: %s", _exc)
    raise HTTPException(
        status_code=403,
        detail="Bu işlem yalnızca sunucu bilgisayarından veya yönetici anahtarıyla (X-Admin-Token) yapılabilir.",
    )

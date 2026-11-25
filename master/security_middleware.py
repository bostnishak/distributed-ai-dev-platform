"""SEC-16: Strict Security Headers, Same-Origin Enforcement, and Double-Submit CSRF Middleware.

- Adds strict CSP (no external CDN), `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`,
  `Referrer-Policy: strict-origin-when-cross-origin`, and `Permissions-Policy`.
- Enforces Same-Origin policy on mutating requests (`POST`, `PUT`, `DELETE`, `PATCH`):
  any cross-origin `Origin` header is rejected with `HTTP 403`.
- Issues `cm6453_csrf` SameSite=Strict cookie on `GET /` and enforces double-submit
  `X-CSRF-Token` verification whenever browser cookies are presented (exempting
  non-cookie API/agent requests authenticated via `Authorization` or `X-Admin-Token`).
"""

from __future__ import annotations

import hmac
import secrets
from urllib.parse import urlparse

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

import config
import ratelimit
from auth import policy as auth_policy
from auth import service as auth_service

CSRF_COOKIE_NAME = "cm6453_csrf"
CSRF_HEADER_NAME = "x-csrf-token"
_PUBLIC_API = ("/api/auth/", "/api/health")
_MUTATING_METHODS = frozenset({"POST", "PUT", "DELETE", "PATCH"})
_API_RATE_LIMITER = ratelimit.TokenBucket(capacity=80.0, refill_per_second=10.0)

APP_CSP = (
    "default-src 'self'; "
    "script-src 'self'; "
    "style-src 'self'; "
    "img-src 'self' data: blob:; "
    "font-src 'self' data:; "
    "connect-src 'self'; "
    "media-src 'self' blob:; "
    "frame-src 'self' http://127.0.0.1:* http://localhost:*; "
    "frame-ancestors 'none'; "
    "base-uri 'self'; "
    "form-action 'self'"
)

PREVIEW_CSP = (
    "sandbox allow-scripts; "
    "default-src 'self' 'unsafe-inline' data: blob:; "
    "connect-src 'none'; "
    "frame-ancestors 'self'"
)


def _is_same_origin(origin: str, request: Request) -> bool:
    try:
        parsed_o = urlparse(origin)
        req_host = (request.headers.get("host") or "").lower()
        origin_host = (parsed_o.netloc or "").lower()
        if not origin_host or not req_host:
            return False
        return origin_host == req_host
    except (ValueError, TypeError, AttributeError):
        return False


def _check_mutating_guards(request: Request) -> JSONResponse | None:
    if request.method not in _MUTATING_METHODS:
        return None
    origin = (request.headers.get("origin") or "").strip()
    if origin and not _is_same_origin(origin, request):
        return JSONResponse(
            status_code=403,
            content={"detail": "Farklı kaynak (cross-origin) mutasyon isteği engellendi."},
        )
    cookie_tok = request.cookies.get(CSRF_COOKIE_NAME, "")
    has_api_auth = bool(
        request.headers.get("authorization")
        or request.headers.get("x-admin-token")
        or request.headers.get("x-agent-key")
    )
    if cookie_tok and not has_api_auth:
        header_tok = request.headers.get(CSRF_HEADER_NAME, "")
        if not header_tok or not hmac.compare_digest(cookie_tok.encode(), header_tok.encode()):
            return JSONResponse(
                status_code=403,
                content={"detail": "CSRF doğrulaması başarısız (X-CSRF-Token eksik veya geçersiz)."},
            )
    return None


def _check_api_guards(request: Request, path: str) -> JSONResponse | None:
    if not path.startswith("/api/"):
        return None
    client_ip = request.client.host if request.client else "unknown"
    allowed, retry_after = _API_RATE_LIMITER.take(f"{client_ip}:{request.method}:{path}")
    if not allowed:
        return JSONResponse(
            status_code=429,
            headers={"Retry-After": str(max(1, int(retry_after) + 1))},
            content={"detail": "İstek hız sınırı aşıldı. Lütfen kısa süre sonra tekrar deneyin."},
        )
    session_cookie = request.cookies.get(auth_service.SESSION_COOKIE_NAME)
    if config.REQUIRE_LOGIN and not path.startswith(_PUBLIC_API) and not auth_service.get_session_user(session_cookie):
        return JSONResponse(status_code=401, content={"detail": "Bu işlem için giriş yapmalısın."})
    if session_cookie:
        session_user = auth_service.get_session_user(session_cookie)
        if session_user and not auth_policy.can(str(session_user.get("role") or "viewer"), request.method, path):
            return JSONResponse(status_code=403, content={"detail": "Bu işlem için rolünüz yetmiyor."})
    return None


def _apply_security_headers(response, request: Request, path: str, is_preview: bool) -> None:
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    response.headers.setdefault("Permissions-Policy", "camera=(), geolocation=(), microphone=(self)")
    response.headers.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
    response.headers.setdefault("Cross-Origin-Opener-Policy", "same-origin")
    response.headers.setdefault("Cross-Origin-Resource-Policy", "same-origin")
    if path.startswith("/api/"):
        response.headers.setdefault("Cache-Control", "no-store")
    if is_preview:
        response.headers["Content-Security-Policy"] = PREVIEW_CSP
        response.headers["X-Frame-Options"] = "SAMEORIGIN"
    else:
        response.headers.setdefault("Content-Security-Policy", APP_CSP)
        response.headers.setdefault("X-Frame-Options", "DENY")
    if path == "/" and CSRF_COOKIE_NAME not in request.cookies:
        response.set_cookie(
            key=CSRF_COOKIE_NAME,
            value=secrets.token_urlsafe(24),
            httponly=False,
            samesite="strict",
            secure=request.url.scheme == "https",
            path="/",
        )


class SecurityHeadersAndCSRFMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        is_preview = "/preview/" in path and path.startswith("/api/studio/workspaces/")
        blocked = _check_mutating_guards(request) or _check_api_guards(request, path)
        if blocked is not None:
            return blocked
        response = await call_next(request)
        _apply_security_headers(response, request, path, is_preview)
        return response

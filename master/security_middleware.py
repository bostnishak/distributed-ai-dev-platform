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

CSRF_COOKIE_NAME = "cm6453_csrf"
CSRF_HEADER_NAME = "x-csrf-token"
_MUTATING_METHODS = frozenset({"POST", "PUT", "DELETE", "PATCH"})

APP_CSP = (
    "default-src 'self'; "
    "script-src 'self' 'unsafe-inline'; "
    "style-src 'self' 'unsafe-inline'; "
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
    except Exception:
        return False


class SecurityHeadersAndCSRFMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        is_preview = "/preview/" in path and path.startswith("/api/studio/workspaces/")

        # 1. Cross-Origin rejection on all mutating endpoints (CORS disabled -> same-origin only)
        if request.method in _MUTATING_METHODS:
            origin = (request.headers.get("origin") or "").strip()
            if origin and not _is_same_origin(origin, request):
                return JSONResponse(
                    status_code=403,
                    content={"detail": "Farklı kaynak (cross-origin) mutasyon isteği engellendi."},
                )

            # 2. Double-submit CSRF verification when a browser session cookie is present
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

        response = await call_next(request)

        # 3. Security headers
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault("Permissions-Policy", "camera=(), geolocation=(), microphone=(self)")
        if is_preview:
            # SEC-17: Force opaque null origin sandbox on preview responses; never send cookies
            response.headers["Content-Security-Policy"] = PREVIEW_CSP
            response.headers["X-Frame-Options"] = "SAMEORIGIN"
        else:
            response.headers.setdefault("Content-Security-Policy", APP_CSP)
            response.headers.setdefault("X-Frame-Options", "DENY")

        # 4. Issue CSRF double-submit cookie on root UI load
        if path == "/" and CSRF_COOKIE_NAME not in request.cookies:
            token = secrets.token_urlsafe(24)
            response.set_cookie(
                key=CSRF_COOKIE_NAME,
                value=token,
                httponly=False,  # JS reads cookie and mirrors into X-CSRF-Token header (double-submit pattern)
                samesite="strict",
                secure=request.url.scheme == "https",
                path="/",
            )
        return response

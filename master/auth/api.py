"""SEC-01 & SEC-02: FastAPI Auth Router (setup, login, logout, me, RBAC user management, Tailscale proxy SSO)."""

from __future__ import annotations

import os
import sqlite3
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field

from auth import service

router = APIRouter(prefix="/api/auth", tags=["auth"])


class SetupRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=48)
    password: str = Field(..., min_length=8, max_length=128)
    email: str | None = None


class LoginRequest(BaseModel):
    username: str = Field(..., min_length=1, max_length=64)
    password: str = Field(..., min_length=1, max_length=128)


class CreateUserRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=48)
    password: str = Field(..., min_length=8, max_length=128)
    role: str = Field(default="member")
    email: str | None = None


class ResetPasswordRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=48)
    new_password: str = Field(..., min_length=8, max_length=128)


def require_authenticated_user(request: Request) -> dict[str, Any]:
    token = request.cookies.get(service.SESSION_COOKIE_NAME)
    user = service.get_session_user(token)
    if not user:
        raise HTTPException(status_code=401, detail="Oturum açmanız gerekiyor.")
    return user


def require_admin_session(user: dict[str, Any] = Depends(require_authenticated_user)) -> dict[str, Any]:  # noqa: B008
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Bu işlem için yönetici rolü gerekir.")
    return user


def _set_cookie(response: Response, signed_token: str, request: Request) -> None:
    is_https = request.url.scheme == "https" or request.headers.get("x-forwarded-proto", "").lower() == "https"
    response.set_cookie(
        key=service.SESSION_COOKIE_NAME,
        value=signed_token,
        httponly=True,
        samesite="lax",
        secure=is_https,
        max_age=service.SESSION_TTL_SECONDS,
        path="/",
    )


@router.get("/status")
async def auth_status(request: Request):
    user = service.get_session_user(request.cookies.get(service.SESSION_COOKIE_NAME))
    return {
        "initialized": service.has_any_user(),
        "authenticated": user is not None,
        "user": {k: user[k] for k in ("id", "username", "email", "role")} if user else None,
    }


@router.post("/setup")
async def initial_admin_setup(body: SetupRequest, request: Request, response: Response):
    if service.has_any_user():
        raise HTTPException(status_code=409, detail="İlk yönetici hesabı zaten oluşturuldu.")
    try:
        user = service.create_user(body.username, body.password, role="admin", email=body.email)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    client_ip = request.client.host if request.client else ""
    _, signed = service.create_session(user["id"], client_ip=client_ip)
    _set_cookie(response, signed, request)
    return {"ok": True, "user": user}


@router.post("/login")
async def login(body: LoginRequest, request: Request, response: Response):
    client_ip = request.client.host if request.client else "unknown"
    rate_key = f"{client_ip}:{body.username.strip().lower()}"
    if not service.check_login_rate_limit(rate_key):
        raise HTTPException(status_code=429, detail="Çok fazla başarısız giriş denemesi; lütfen bekleyin.")
    user = service.authenticate_user(body.username, body.password)
    if not user:
        service.record_login_failure(rate_key)
        raise HTTPException(status_code=401, detail="Kullanıcı adı veya parola hatalı.")
    service.clear_login_failures(rate_key)
    _, signed = service.create_session(user["id"], client_ip=client_ip)
    _set_cookie(response, signed, request)
    return {"ok": True, "user": user}


@router.post("/logout")
async def logout(request: Request, response: Response):
    user = service.get_session_user(request.cookies.get(service.SESSION_COOKIE_NAME))
    if user:
        service.revoke_session(user["session_id"])
    response.delete_cookie(key=service.SESSION_COOKIE_NAME, path="/")
    return {"ok": True}


@router.get("/me")
async def auth_me(user: dict[str, Any] = Depends(require_authenticated_user)):  # noqa: B008
    return {"authenticated": True, "user": {k: user[k] for k in ("id", "username", "email", "role")}}


@router.post("/users", dependencies=[Depends(require_admin_session)])
async def admin_create_user(body: CreateUserRequest):
    try:
        user = service.create_user(body.username, body.password, role=body.role, email=body.email)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except sqlite3.IntegrityError as exc:
        raise HTTPException(status_code=409, detail="Bu kullanıcı adı veya e-posta zaten kayıtlı.") from exc
    return {"ok": True, "user": user}


@router.post("/reset-password", dependencies=[Depends(require_admin_session)])
async def admin_reset_password(body: ResetPasswordRequest):
    try:
        ok = service.reset_user_password(body.username, body.new_password)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if not ok:
        raise HTTPException(status_code=404, detail="Kullanıcı bulunamadı.")
    return {"ok": True}


@router.get("/tailscale-me")
async def tailscale_sso_me(request: Request):
    trusted = os.environ.get("TRUSTED_TAILSCALE_PROXY", "false").strip().lower() in ("1", "true", "yes")
    client_host = request.client.host if request.client else ""
    ts_header = request.headers.get("tailscale-user-login", "")
    user = service.resolve_tailscale_user(ts_header, client_host=client_host, trusted_proxy=trusted)
    if not user:
        raise HTTPException(status_code=403, detail="Tailscale kimliği doğrulanamadı veya güvenilir proxy kapalı.")
    return {"authenticated": True, "user": user}

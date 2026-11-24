"""EPK-03: Multi-user Organizations, Signed Single-Use Invites, and RBAC Enforcement."""

from __future__ import annotations

import hashlib
import re
import secrets
import sqlite3
from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

import dbconn
from auth import service as auth_service

router = APIRouter(prefix="/api/auth/orgs", tags=["auth-orgs"])

VALID_ROLES: tuple[str, ...] = ("owner", "admin", "member", "viewer")
_SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9-]{1,40}$")

RBAC_MATRIX: dict[str, set[str]] = {
    "owner": {"read", "write", "invite", "manage_members", "manage_settings", "delete_org", "admin"},
    "admin": {"read", "write", "invite", "manage_members", "manage_settings", "admin"},
    "member": {"read", "write"},
    "viewer": {"read"},
}


def _connect() -> sqlite3.Connection:
    return dbconn.open_db(dbconn.database_file("auth.db"))


def init_orgs_db() -> None:
    """Create orgs, org_members, and org_invites tables idempotently."""
    with _connect() as conn:
        conn.execute(
            "CREATE TABLE IF NOT EXISTS orgs ("
            "id TEXT PRIMARY KEY, slug TEXT NOT NULL UNIQUE, name TEXT NOT NULL, "
            "owner_id TEXT NOT NULL, created_at TEXT NOT NULL)"
        )
        conn.execute(
            "CREATE TABLE IF NOT EXISTS org_members ("
            "org_id TEXT NOT NULL, user_id TEXT NOT NULL, role TEXT NOT NULL DEFAULT 'member', "
            "joined_at TEXT NOT NULL, PRIMARY KEY (org_id, user_id))"
        )
        conn.execute(
            "CREATE TABLE IF NOT EXISTS org_invites ("
            "token_hash TEXT PRIMARY KEY, org_id TEXT NOT NULL, invited_by TEXT NOT NULL, "
            "role TEXT NOT NULL DEFAULT 'member', email TEXT NOT NULL DEFAULT '', "
            "expires_at TEXT NOT NULL, used_by TEXT, used_at TEXT, created_at TEXT NOT NULL)"
        )


def _hash_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def _sanitize_slug(raw: str) -> str:
    cleaned = re.sub(r"[^a-z0-9-]+", "-", raw.strip().lower()).strip("-")[:40]
    if not _SLUG_RE.match(cleaned):
        raise ValueError("Geçersiz organizasyon kısa adı (en az 2 küçük harf/rakam).")
    return cleaned


def resolve_effective_user_id(request: Request, requested_user_id: str | None = None) -> str:
    """Derive effective user_id from authenticated session and reject cross-user IDOR spoofing."""
    session_user = auth_service.get_session_user(request.cookies.get(auth_service.SESSION_COOKIE_NAME))
    if session_user:
        sid = str(session_user["username"])
        if requested_user_id and requested_user_id != sid and session_user.get("role") != "admin":
            raise HTTPException(status_code=403, detail="Başka bir kullanıcının verisine erişim yetkiniz yok (IDOR koruması).")
        return requested_user_id or sid
    return (requested_user_id or "default").strip() or "default"


def check_rbac_permission(role: str, action: str) -> bool:
    """Return True if role permits the requested action according to RBAC_MATRIX."""
    return action.strip().lower() in RBAC_MATRIX.get(role.strip().lower(), set())


def create_org(owner_id: str, name: str, slug: str | None = None) -> dict[str, Any]:
    """Create a new organization and register owner_id with the owner role."""
    init_orgs_db()
    clean_name = name.strip()
    if len(clean_name) < 2:
        raise ValueError("Organizasyon adı en az 2 karakter olmalıdır.")
    clean_slug = _sanitize_slug(slug or clean_name)
    org_id = f"org_{secrets.token_hex(6)}"
    now = datetime.now(UTC).isoformat()
    with _connect() as conn:
        try:
            conn.execute(
                "INSERT INTO orgs (id, slug, name, owner_id, created_at) VALUES (?, ?, ?, ?, ?)",
                (org_id, clean_slug, clean_name, owner_id, now),
            )
        except sqlite3.IntegrityError as exc:
            raise ValueError(f"Bu organizasyon kısa adı zaten kullanımda: {clean_slug}") from exc
        conn.execute(
            "INSERT INTO org_members (org_id, user_id, role, joined_at) VALUES (?, ?, 'owner', ?)",
            (org_id, owner_id, now),
        )
    return {"id": org_id, "slug": clean_slug, "name": clean_name, "owner_id": owner_id, "role": "owner", "created_at": now}


def list_user_orgs(user_id: str) -> list[dict[str, Any]]:
    init_orgs_db()
    with _connect() as conn:
        rows = conn.execute(
            "SELECT o.id, o.slug, o.name, o.owner_id, o.created_at, m.role "
            "FROM orgs o JOIN org_members m ON o.id = m.org_id WHERE m.user_id = ? ORDER BY o.created_at DESC",
            (user_id,),
        ).fetchall()
    return [dict(r) for r in rows]


def get_member_role(org_id: str, user_id: str) -> str | None:
    init_orgs_db()
    with _connect() as conn:
        row = conn.execute(
            "SELECT role FROM org_members WHERE org_id = ? AND user_id = ?",
            (org_id, user_id),
        ).fetchone()
    return str(row["role"]) if row else None


def list_org_members(org_id: str, requester_id: str) -> list[dict[str, Any]]:
    init_orgs_db()
    role = get_member_role(org_id, requester_id)
    if not role:
        raise PermissionError("Bu organizasyonun üyesi değilsiniz.")
    with _connect() as conn:
        rows = conn.execute(
            "SELECT org_id, user_id, role, joined_at FROM org_members WHERE org_id = ? ORDER BY joined_at ASC",
            (org_id,),
        ).fetchall()
    return [dict(r) for r in rows]


def create_invite(org_id: str, invited_by: str, role: str = "member", email: str = "", ttl_hours: int = 48) -> dict[str, Any]:
    init_orgs_db()
    caller_role = get_member_role(org_id, invited_by)
    if not caller_role or not check_rbac_permission(caller_role, "invite"):
        raise PermissionError("Davet oluşturmak için yönetici veya sahip rolü gerekir.")
    if role not in VALID_ROLES or role == "owner":
        raise ValueError("Davet rolü admin, member veya viewer olmalıdır.")
    raw_token = f"inv_{secrets.token_urlsafe(24)}"
    now = datetime.now(UTC)
    expires_at = (now + timedelta(hours=max(1, min(ttl_hours, 720)))).isoformat()
    with _connect() as conn:
        conn.execute(
            "INSERT INTO org_invites (token_hash, org_id, invited_by, role, email, expires_at, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (_hash_token(raw_token), org_id, invited_by, role, email.strip()[:120], expires_at, now.isoformat()),
        )
    return {"org_id": org_id, "role": role, "email": email.strip(), "invite_token": raw_token, "expires_at": expires_at}


def accept_invite(raw_token: str, user_id: str) -> dict[str, Any]:
    init_orgs_db()
    th = _hash_token(raw_token.strip())
    now = datetime.now(UTC)
    with _connect() as conn:
        row = conn.execute(
            "SELECT org_id, role, expires_at, used_by FROM org_invites WHERE token_hash = ?",
            (th,),
        ).fetchone()
        if not row:
            raise ValueError("Davet anahtarı geçersiz.")
        if row["used_by"]:
            raise ValueError("Bu davet anahtarı daha önce kullanılmış.")
        if datetime.fromisoformat(row["expires_at"]) < now:
            raise ValueError("Bu davet anahtarının süresi dolmuş.")
        conn.execute(
            "UPDATE org_invites SET used_by = ?, used_at = ? WHERE token_hash = ?",
            (user_id, now.isoformat(), th),
        )
        conn.execute(
            "INSERT OR REPLACE INTO org_members (org_id, user_id, role, joined_at) VALUES (?, ?, ?, ?)",
            (row["org_id"], user_id, row["role"], now.isoformat()),
        )
    return {"ok": True, "org_id": row["org_id"], "user_id": user_id, "role": row["role"]}


class CreateOrgRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=80)
    slug: str | None = Field(default=None, max_length=48)
    owner_id: str | None = Field(default=None, max_length=64)


class CreateInviteRequest(BaseModel):
    role: str = Field(default="member")
    email: str = Field(default="", max_length=120)
    ttl_hours: int = Field(default=48, ge=1, le=720)
    invited_by: str | None = Field(default=None, max_length=64)


class AcceptInviteRequest(BaseModel):
    invite_token: str = Field(..., min_length=8, max_length=128)
    user_id: str | None = Field(default=None, max_length=64)


class RbacCheckRequest(BaseModel):
    role: str = Field(..., min_length=2, max_length=32)
    action: str = Field(..., min_length=2, max_length=64)


@router.get("")
async def api_list_orgs(request: Request, user_id: str | None = None):
    """List organizations belonging to the authenticated or requested user."""
    uid = resolve_effective_user_id(request, user_id)
    return {"ok": True, "user_id": uid, "orgs": list_user_orgs(uid)}


@router.post("")
async def api_create_org(body: CreateOrgRequest, request: Request):
    """Create a new organization owned by the active user."""
    uid = resolve_effective_user_id(request, body.owner_id)
    try:
        org = create_org(uid, body.name, body.slug)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"ok": True, "org": org}


@router.get("/{org_id}/members")
async def api_list_org_members(org_id: str, request: Request, user_id: str | None = None):
    """List members of an organization after checking membership."""
    uid = resolve_effective_user_id(request, user_id)
    try:
        members = list_org_members(org_id, uid)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    return {"ok": True, "org_id": org_id, "members": members}


@router.post("/{org_id}/invites")
async def api_create_invite(org_id: str, body: CreateInviteRequest, request: Request):
    """Issue a signed single-use organization invite token."""
    uid = resolve_effective_user_id(request, body.invited_by)
    try:
        inv = create_invite(org_id, uid, role=body.role, email=body.email, ttl_hours=body.ttl_hours)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"ok": True, "invite": inv}


@router.post("/invites/accept")
async def api_accept_invite(body: AcceptInviteRequest, request: Request):
    """Redeem a single-use organization invite token."""
    uid = resolve_effective_user_id(request, body.user_id)
    try:
        return accept_invite(body.invite_token, uid)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/rbac/check")
async def api_rbac_check(body: RbacCheckRequest):
    """Check whether a role permits an action in the canonical RBAC matrix."""
    allowed = check_rbac_permission(body.role, body.action)
    return {"ok": True, "role": body.role, "action": body.action, "allowed": allowed}

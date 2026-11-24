"""SEC-01 & SEC-02: Password hashing, SQLite users/sessions, HMAC cookie signing, rate limiting, Tailscale proxy check."""

from __future__ import annotations

import base64
import hashlib
import hmac
import os
import secrets
import sqlite3
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import config
import dbconn

SESSION_COOKIE_NAME = "dadp_session"
SESSION_TTL_SECONDS = 8 * 3600
_PBKDF2_ITERS = 200_000
_LOGIN_FAILURES: dict[str, list[float]] = {}
_MAX_FAILURES = 5
_WINDOW_SECONDS = 60.0


def _auth_db_path() -> Path:
    p = config.data_dir() / "auth.db"
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def _conn() -> sqlite3.Connection:
    return dbconn.open_db(_auth_db_path())


def _signing_secret() -> bytes:
    raw = (getattr(config, "SECRET_KEY", "") or os.environ.get("SECRET_KEY") or "dadp-local-dev-session-secret").encode("utf-8")
    return hashlib.sha256(raw).digest()


def init_auth_db() -> None:
    with _conn() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS auth_users (
                id TEXT PRIMARY KEY,
                username TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'member',
                is_active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS auth_sessions (
                session_id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL REFERENCES auth_users(id) ON DELETE CASCADE,
                created_at TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                revoked INTEGER NOT NULL DEFAULT 0,
                client_ip TEXT NOT NULL DEFAULT ''
            );
            CREATE INDEX IF NOT EXISTS idx_auth_sessions_user ON auth_sessions(user_id);
            """
        )


def hash_password(password: str) -> str:
    if len(password or "") < 8:
        raise ValueError("Parola en az 8 karakter olmalıdır.")
    try:
        from argon2 import PasswordHasher  # type: ignore[import-not-found]

        return PasswordHasher().hash(password)
    except ImportError:
        salt = secrets.token_bytes(16)
        dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, _PBKDF2_ITERS)
        return f"pbkdf2_sha256${_PBKDF2_ITERS}${base64.b64encode(salt).decode()}${base64.b64encode(dk).decode()}"


def verify_password(password: str, stored_hash: str) -> bool:
    if not password or not stored_hash:
        return False
    if stored_hash.startswith("$argon2"):
        try:
            from argon2 import PasswordHasher  # type: ignore[import-not-found]

            return bool(PasswordHasher().verify(stored_hash, password))
        except Exception:
            return False
    if stored_hash.startswith("pbkdf2_sha256$"):
        try:
            _, iters_s, salt_b64, dk_b64 = stored_hash.split("$", 3)
            salt = base64.b64decode(salt_b64)
            expected = base64.b64decode(dk_b64)
            actual = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, int(iters_s))
            return hmac.compare_digest(actual, expected)
        except Exception:
            return False
    return False


def sign_session_token(session_id: str) -> str:
    sig = hmac.new(_signing_secret(), session_id.encode("utf-8"), hashlib.sha256).hexdigest()
    return f"{session_id}.{sig}"


def verify_session_token(token: str) -> str | None:
    if not token or "." not in token:
        return None
    session_id, sig = token.rsplit(".", 1)
    expected = hmac.new(_signing_secret(), session_id.encode("utf-8"), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(sig, expected):
        return None
    return session_id


def check_login_rate_limit(key: str) -> bool:
    now = time.monotonic()
    bucket = [ts for ts in _LOGIN_FAILURES.get(key, []) if now - ts < _WINDOW_SECONDS]
    _LOGIN_FAILURES[key] = bucket
    return len(bucket) < _MAX_FAILURES


def record_login_failure(key: str) -> None:
    now = time.monotonic()
    bucket = [ts for ts in _LOGIN_FAILURES.get(key, []) if now - ts < _WINDOW_SECONDS]
    bucket.append(now)
    _LOGIN_FAILURES[key] = bucket


def clear_login_failures(key: str) -> None:
    _LOGIN_FAILURES.pop(key, None)


def has_any_user() -> bool:
    init_auth_db()
    with _conn() as conn:
        row = conn.execute("SELECT COUNT(*) FROM auth_users").fetchone()
    return bool(row and row[0] > 0)


def create_user(username: str, password: str, *, role: str = "member", email: str | None = None) -> dict[str, Any]:
    init_auth_db()
    uname = (username or "").strip().lower()
    if len(uname) < 3 or len(uname) > 48:
        raise ValueError("Kullanıcı adı 3-48 karakter olmalıdır.")
    if role not in ("admin", "member", "developer", "analyst", "viewer"):
        raise ValueError("Geçersiz rol.")
    pw_hash = hash_password(password)
    uid = f"usr_{secrets.token_hex(8)}"
    now = datetime.now(UTC).isoformat()
    norm_email = (email or "").strip().lower() or None
    with _conn() as conn:
        conn.execute(
            """
            INSERT INTO auth_users (id, username, email, password_hash, role, is_active, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, 1, ?, ?)
            """,
            (uid, uname, norm_email, pw_hash, role, now, now),
        )
    return {"id": uid, "username": uname, "email": norm_email, "role": role, "is_active": True}


def authenticate_user(username: str, password: str) -> dict[str, Any] | None:
    init_auth_db()
    uname = (username or "").strip().lower()
    with _conn() as conn:
        row = conn.execute(
            "SELECT id, username, email, password_hash, role, is_active FROM auth_users WHERE username = ?",
            (uname,),
        ).fetchone()
    if not row or not row["is_active"]:
        return None
    if not verify_password(password, row["password_hash"]):
        return None
    return {"id": row["id"], "username": row["username"], "email": row["email"], "role": row["role"]}


def create_session(user_id: str, *, client_ip: str = "", ttl_seconds: int = SESSION_TTL_SECONDS) -> tuple[str, str]:
    init_auth_db()
    sid = secrets.token_urlsafe(24)
    now = datetime.now(UTC)
    exp = now + timedelta(seconds=ttl_seconds)
    with _conn() as conn:
        conn.execute(
            """
            INSERT INTO auth_sessions (session_id, user_id, created_at, expires_at, revoked, client_ip)
            VALUES (?, ?, ?, ?, 0, ?)
            """,
            (sid, user_id, now.isoformat(), exp.isoformat(), client_ip[:64]),
        )
    return sid, sign_session_token(sid)


def get_session_user(cookie_token: str | None) -> dict[str, Any] | None:
    sid = verify_session_token(cookie_token or "")
    if not sid:
        return None
    init_auth_db()
    now_iso = datetime.now(UTC).isoformat()
    with _conn() as conn:
        row = conn.execute(
            """
            SELECT s.session_id, s.expires_at, s.revoked, u.id, u.username, u.email, u.role, u.is_active
            FROM auth_sessions s
            JOIN auth_users u ON u.id = s.user_id
            WHERE s.session_id = ?
            """,
            (sid,),
        ).fetchone()
    if not row or row["revoked"] or not row["is_active"]:
        return None
    if str(row["expires_at"]) <= now_iso:
        return None
    return {
        "session_id": row["session_id"],
        "id": row["id"],
        "username": row["username"],
        "email": row["email"],
        "role": row["role"],
    }


def revoke_session(session_id: str) -> None:
    init_auth_db()
    with _conn() as conn:
        conn.execute("UPDATE auth_sessions SET revoked = 1 WHERE session_id = ?", (session_id,))


def reset_user_password(username: str, new_password: str) -> bool:
    init_auth_db()
    uname = (username or "").strip().lower()
    pw_hash = hash_password(new_password)
    now = datetime.now(UTC).isoformat()
    with _conn() as conn:
        row = conn.execute("SELECT id FROM auth_users WHERE username = ?", (uname,)).fetchone()
        if not row:
            return False
        conn.execute(
            "UPDATE auth_users SET password_hash = ?, updated_at = ? WHERE id = ?",
            (pw_hash, now, row["id"]),
        )
        conn.execute("UPDATE auth_sessions SET revoked = 1 WHERE user_id = ?", (row["id"],))
    return True


def resolve_tailscale_user(tailscale_login: str, *, client_host: str, trusted_proxy: bool) -> dict[str, Any] | None:
    """SEC-02: Accept Tailscale-User-Login strictly from loopback when trusted_proxy mode is enabled."""
    if not trusted_proxy or client_host not in ("127.0.0.1", "::1", "localhost"):
        return None
    login = (tailscale_login or "").strip().lower()
    if not login or "@" not in login:
        return None
    init_auth_db()
    with _conn() as conn:
        row = conn.execute(
            "SELECT id, username, email, role, is_active FROM auth_users WHERE email = ? OR username = ?",
            (login, login.split("@", 1)[0]),
        ).fetchone()
    if not row or not row["is_active"]:
        return None
    return {"id": row["id"], "username": row["username"], "email": row["email"], "role": row["role"], "via": "tailscale"}

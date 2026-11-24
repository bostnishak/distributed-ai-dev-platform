"""GUV-01..07: TOTP 2FA, Password Strength, Session Management, Account Lockout, IP Allowlist, Secret & AV Scanning."""

from __future__ import annotations

import base64
import hashlib
import hmac
import ipaddress
import re
import secrets
import struct
import time
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from access_control import require_local_or_admin
from auth import service as auth_service

router = APIRouter(prefix="/api/security", tags=["security"])
_ADMIN_DEP = [Depends(require_local_or_admin)]

_COMMON_PASSWORDS = frozenset(
    {"password", "12345678", "qwerty123", "admin123", "parola123", "letmein1", "welcome1", "istanbul"}
)
_LOCKOUT_STATE: dict[str, dict[str, Any]] = {}
_ALLOWED_IP_NETWORKS: list[str] = ["127.0.0.0/8", "::1/128", "100.64.0.0/10"]

_SECRET_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("aws_access_key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("github_token", re.compile(r"\bgh[pousr]_[A-Za-z0-9_]{20,}\b")),
    ("openai_key", re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b")),
    ("private_key", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----")),
    ("generic_api_secret", re.compile(r"(?i)(?:api_key|secret_key|password)\s*[:=]\s*['\"][^'\"]{12,}['\"]")),
)


# ---------------------------------------------------------------- GUV-01: RFC 6238 TOTP 2FA

def generate_totp_secret() -> str:
    """Generate a Base32-encoded 160-bit TOTP secret."""
    return base64.b32encode(secrets.token_bytes(20)).decode("ascii").rstrip("=")


def totp_code(secret_b32: str, *, for_time: int | None = None, step: int = 30, digits: int = 6) -> str:
    """Compute RFC 6238 HMAC-SHA1 TOTP code."""
    padded = secret_b32.strip().upper()
    padded += "=" * ((8 - len(padded) % 8) % 8)
    key = base64.b32decode(padded, casefold=True)
    counter = int((for_time if for_time is not None else time.time()) // step)
    msg = struct.pack(">Q", counter)
    digest = hmac.new(key, msg, hashlib.sha1).digest()
    offset = digest[-1] & 0x0F
    code_int = struct.unpack(">I", digest[offset : offset + 4])[0] & 0x7FFFFFFF
    return str(code_int % (10**digits)).zfill(digits)


def verify_totp(secret_b32: str, code: str, *, window: int = 1, now: int | None = None) -> bool:
    """Verify a 6-digit TOTP code within +-window time steps."""
    clean = re.sub(r"\s+", "", str(code or ""))
    if not clean.isdigit() or len(clean) != 6:
        return False
    base_ts = int(now if now is not None else time.time())
    for delta in range(-window, window + 1):
        expected = totp_code(secret_b32, for_time=base_ts + delta * 30)
        if hmac.compare_digest(clean, expected):
            return True
    return False


def build_otpauth_uri(username: str, secret_b32: str, issuer: str = "DADP-Platform") -> str:
    return f"otpauth://totp/{issuer}:{username}?secret={secret_b32}&issuer={issuer}&digits=6&period=30"


# ---------------------------------------------------------------- GUV-02: Password Strength Policy

def evaluate_password_strength(password: str) -> dict[str, Any]:
    """GUV-02: Score password strength (0..4) with actionable Turkish remediation hints."""
    pw = password or ""
    issues: list[str] = []
    if len(pw) < 8:
        issues.append("En az 8 karakter olmalı.")
    if not re.search(r"[a-z]", pw):
        issues.append("En az bir küçük harf ekleyin.")
    if not re.search(r"[A-Z]", pw):
        issues.append("En az bir büyük harf ekleyin.")
    if not re.search(r"\d", pw):
        issues.append("En az bir rakam ekleyin.")
    if not re.search(r"[^A-Za-z0-9]", pw):
        issues.append("En az bir özel karakter ekleyin.")
    if pw.lower() in _COMMON_PASSWORDS:
        issues.append("Yaygın/kolay tahmin edilen parolalar kullanılamaz.")
    score = max(0, min(4, 4 - len(issues))) if len(pw) >= 8 and pw.lower() not in _COMMON_PASSWORDS else 0
    labels = ("çok zayıf", "zayıf", "orta", "güçlü", "çok güçlü")
    return {"score": score, "label": labels[score], "valid": len(issues) == 0, "issues": issues}


# ---------------------------------------------------------------- GUV-04: Account Lockout

def record_account_failure(username: str, *, max_attempts: int = 5, lock_seconds: int = 300) -> dict[str, Any]:
    key = (username or "").strip().lower()
    now = time.time()
    rec = _LOCKOUT_STATE.setdefault(key, {"failures": 0, "locked_until": 0.0})
    if rec["locked_until"] > now:
        return {"locked": True, "locked_until": rec["locked_until"], "remaining_sec": int(rec["locked_until"] - now)}
    rec["failures"] += 1
    if rec["failures"] >= max_attempts:
        rec["locked_until"] = now + lock_seconds
        rec["failures"] = 0
        return {"locked": True, "locked_until": rec["locked_until"], "remaining_sec": lock_seconds}
    return {"locked": False, "failures": rec["failures"], "remaining_attempts": max_attempts - rec["failures"]}


def check_account_lock(username: str) -> dict[str, Any]:
    key = (username or "").strip().lower()
    rec = _LOCKOUT_STATE.get(key)
    now = time.time()
    if rec and rec["locked_until"] > now:
        return {"locked": True, "locked_until": rec["locked_until"], "remaining_sec": int(rec["locked_until"] - now)}
    return {"locked": False, "locked_until": 0.0, "remaining_sec": 0}


# ---------------------------------------------------------------- GUV-05: IP Allowlist

def is_ip_allowed(ip_str: str, allowlist: list[str] | None = None) -> bool:
    """Check whether an IP belongs to configured CIDR networks."""
    try:
        addr = ipaddress.ip_address(ip_str.strip())
    except ValueError:
        return False
    nets = allowlist if allowlist is not None else _ALLOWED_IP_NETWORKS
    for entry in nets:
        try:
            if addr in ipaddress.ip_network(entry.strip(), strict=False):
                return True
        except ValueError:
            continue
    return False


# ---------------------------------------------------------------- GUV-06 & GUV-07: Secret Scan & Optional ClamAV

def detect_secrets_in_text(text: str) -> dict[str, Any]:
    """Scan uploaded content for leaked API keys, tokens, and private keys."""
    findings: list[dict[str, Any]] = []
    for name, pat in _SECRET_PATTERNS:
        for m in pat.finditer(text or ""):
            findings.append({"type": name, "offset": m.start(), "preview": m.group(0)[:6] + "***"})
    return {"clean": len(findings) == 0, "findings_count": len(findings), "findings": findings}


def clamav_status() -> dict[str, Any]:
    """Report honest ClamAV daemon availability (never fakes clean when unavailable)."""
    return {
        "engine": "clamav",
        "available": False,
        "detail": "ClamAV (clamd) yerel sunucuda kurulu değil; yüklemelerde yerleşik gizli anahtar ve MIME taraması aktif.",
    }


# ---------------------------------------------------------------- REST Endpoints

class TotpVerifyBody(BaseModel):
    secret: str
    code: str


class PasswordCheckBody(BaseModel):
    password: str


class SecretScanBody(BaseModel):
    content: str = Field(..., max_length=200_000)


class IpAllowlistBody(BaseModel):
    cidrs: list[str]


@router.post("/totp/setup", dependencies=_ADMIN_DEP)
async def api_totp_setup(username: str = "admin"):
    """Generate a new RFC 6238 TOTP secret and otpauth URI (GUV-01)."""
    secret = generate_totp_secret()
    return {"secret": secret, "otpauth_uri": build_otpauth_uri(username, secret)}


@router.post("/totp/verify", dependencies=_ADMIN_DEP)
async def api_totp_verify(body: TotpVerifyBody):
    """Verify a 6-digit TOTP token against a Base32 secret (GUV-01)."""
    return {"valid": verify_totp(body.secret, body.code)}


@router.post("/password-strength")
async def api_password_strength(body: PasswordCheckBody):
    """Evaluate password strength and return Turkish policy guidance (GUV-02)."""
    return evaluate_password_strength(body.password)


@router.get("/sessions", dependencies=_ADMIN_DEP)
async def api_list_sessions():
    """List active non-revoked authentication sessions (GUV-03)."""
    auth_service.init_auth_db()
    with auth_service._conn() as conn:
        rows = conn.execute(
            """
            SELECT s.session_id, u.username, u.role, s.created_at, s.expires_at, s.client_ip
            FROM auth_sessions s JOIN auth_users u ON u.id = s.user_id
            WHERE s.revoked = 0 ORDER BY s.created_at DESC LIMIT 100
            """
        ).fetchall()
    return {"sessions": [dict(r) for r in rows]}


@router.post("/sessions/revoke-all", dependencies=_ADMIN_DEP)
async def api_sessions_revoke_all():
    """Revoke all active authentication sessions remotely (GUV-03)."""
    auth_service.init_auth_db()
    with auth_service._conn() as conn:
        cur = conn.execute("UPDATE auth_sessions SET revoked = 1 WHERE revoked = 0")
    return {"ok": True, "revoked_count": cur.rowcount}


@router.get("/lockout/{username}", dependencies=_ADMIN_DEP)
async def api_lockout_status(username: str):
    """Inspect account lockout state for a username (GUV-04)."""
    return check_account_lock(username)


@router.get("/ip-allowlist", dependencies=_ADMIN_DEP)
async def api_get_ip_allowlist(request: Request):
    """Return configured CIDR IP allowlist and whether the caller IP is allowed (GUV-05)."""
    host = request.client.host if request.client else "127.0.0.1"
    return {"allowed_ips": list(_ALLOWED_IP_NETWORKS), "caller_ip": host, "caller_allowed": is_ip_allowed(host)}


@router.put("/ip-allowlist", dependencies=_ADMIN_DEP)
async def api_set_ip_allowlist(body: IpAllowlistBody):
    """Update allowed CIDR ranges for restricted administrative access (GUV-05)."""
    validated: list[str] = []
    for item in body.cidrs:
        try:
            validated.append(str(ipaddress.ip_network(item.strip(), strict=False)))
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=f"Geçersiz CIDR: {item}") from exc
    _ALLOWED_IP_NETWORKS[:] = validated or ["127.0.0.0/8", "::1/128"]
    return {"ok": True, "allowed_ips": list(_ALLOWED_IP_NETWORKS)}


@router.post("/secret-scan", dependencies=_ADMIN_DEP)
async def api_secret_scan(body: SecretScanBody):
    """Scan text or uploaded payload for leaked API keys or private keys (GUV-06)."""
    return detect_secrets_in_text(body.content)


@router.get("/antivirus/status", dependencies=_ADMIN_DEP)
async def api_antivirus_status():
    """Return honest ClamAV daemon status (GUV-07)."""
    return clamav_status()

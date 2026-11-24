"""RFC 6238 TOTP primitives (GUV-01), shared by the login flow and the /api/security helpers."""

from __future__ import annotations

import base64
import hashlib
import hmac
import re
import secrets
import struct
import time


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

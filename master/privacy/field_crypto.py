"""EPK-25: Authenticated Field-Level Encryption at Rest, Malware Scanner Hook & Cryptographic RTBF Erasure Proof."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import secrets
import sqlite3
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

import dbconn
import user_profile as up

router = APIRouter(prefix="/api/privacy", tags=["privacy"])

_EICAR_SIG = b"X5O!P%@AP[4\\PZX54(P^)7CC)7}$EICAR-STANDARD-ANTIVIRUS-TEST-FILE!$H+H*"
_DANGEROUS_MAGICS: tuple[tuple[str, bytes], ...] = (
    ("windows_pe_executable", b"MZ\x90\x00"),
    ("linux_elf_executable", b"\x7fELF"),
    ("macro_script_tag", b"<script"),
)


def _master_key_bytes() -> bytes:
    seed = os.environ.get("DADP_FIELD_KEY", "").strip()
    if not seed:
        seed = os.environ.get("ADMIN_TOKEN", "").strip() or "dadp-local-dev-field-key-v1"
    return hashlib.sha256(f"dadp-field-crypto:{seed}".encode()).digest()


def _keystream(key: bytes, nonce: bytes, length: int) -> bytes:
    blocks: list[bytes] = []
    counter = 0
    produced = 0
    while produced < length:
        blk = hashlib.sha256(key + nonce + counter.to_bytes(4, "big")).digest()
        blocks.append(blk)
        produced += len(blk)
        counter += 1
    return b"".join(blocks)[:length]


def encrypt_field(plaintext: str, *, key_override: bytes | None = None) -> str:
    """Encrypt a UTF-8 field using authenticated SHA-256 CTR + HMAC-SHA256 with random 16-byte nonce."""
    key = key_override or _master_key_bytes()
    enc_key = hashlib.sha256(key + b":enc").digest()
    mac_key = hashlib.sha256(key + b":mac").digest()
    nonce = secrets.token_bytes(16)
    pt_bytes = plaintext.encode("utf-8")
    ks = _keystream(enc_key, nonce, len(pt_bytes))
    ct = bytes(a ^ b for a, b in zip(pt_bytes, ks, strict=True))
    tag = hmac.new(mac_key, b"v1:" + nonce + ct, hashlib.sha256).digest()
    packed = base64.urlsafe_b64encode(nonce + tag + ct).decode("ascii")
    return f"v1:{packed}"


def decrypt_field(token: str, *, key_override: bytes | None = None) -> str:
    """Verify HMAC tag and decrypt a `v1:` field ciphertext; raises ValueError on tampering or bad key."""
    if not token.startswith("v1:"):
        raise ValueError("Desteklenmeyen şifreli alan biçimi.")
    try:
        raw = base64.urlsafe_b64decode(token[3:].encode("ascii"))
    except (ValueError, TypeError) as exc:
        raise ValueError("Şifreli veri çözülemedi (bozuk Base64).") from exc
    if len(raw) < 48:
        raise ValueError("Şifreli veri eksik veya bozuk.")
    nonce, tag, ct = raw[:16], raw[16:48], raw[48:]
    key = key_override or _master_key_bytes()
    enc_key = hashlib.sha256(key + b":enc").digest()
    mac_key = hashlib.sha256(key + b":mac").digest()
    expected = hmac.new(mac_key, b"v1:" + nonce + ct, hashlib.sha256).digest()
    if not hmac.compare_digest(tag, expected):
        raise ValueError("Şifreli alan bütünlük doğrulaması başarısız (kurcalama veya yanlış anahtar).")
    ks = _keystream(enc_key, nonce, len(ct))
    pt = bytes(a ^ b for a, b in zip(ct, ks, strict=True))
    return pt.decode("utf-8")


def scan_payload_malware(raw: bytes, filename: str = "upload.bin") -> dict[str, Any]:
    """Scan bytes against EICAR test signature and executable/script magic headers."""
    findings: list[str] = []
    if _EICAR_SIG in raw:
        findings.append("eicar_test_virus_signature")
    low = raw[:4096].lower()
    for label, sig in _DANGEROUS_MAGICS:
        if sig.lower() in low:
            findings.append(label)
    return {
        "filename": filename,
        "size_bytes": len(raw),
        "clean": len(findings) == 0,
        "findings": findings,
        "engine": "dadp-builtin-signature-scanner",
    }


def _privacy_conn() -> sqlite3.Connection:
    return dbconn.open_db(dbconn.database_file("platform.db"))


def init_privacy_db() -> None:
    with _privacy_conn() as conn:
        conn.execute(
            "CREATE TABLE IF NOT EXISTS rtbf_erasure_proofs ("
            "proof_id TEXT PRIMARY KEY, user_hash TEXT NOT NULL, erased_at TEXT NOT NULL, "
            "removed_counts_json TEXT NOT NULL, residual_hits INTEGER NOT NULL DEFAULT 0, "
            "receipt_hmac TEXT NOT NULL)"
        )


_USER_PROFILE_COUNT_QUERIES: tuple[str, ...] = (
    "SELECT COUNT(*) FROM usage_events WHERE user_id = ?",
    "SELECT COUNT(*) FROM saved_chats WHERE user_id = ?",
)
_MEMORY_COUNT_QUERIES: tuple[str, ...] = (
    "SELECT COUNT(*) FROM semantic_memories WHERE user_id = ?",
    "SELECT COUNT(*) FROM conversations WHERE user_id = ?",
)


def _count_residual_user_rows(uid: str) -> int:
    hits = 0
    up.init_db()
    with dbconn.open_db(dbconn.database_file("user_profile.db")) as uconn:
        for sql in _USER_PROFILE_COUNT_QUERIES:
            row = uconn.execute(sql, (uid,)).fetchone()
            hits += int(row[0]) if row else 0
    with dbconn.open_db(dbconn.database_file("cognitive_memory.db")) as mconn:
        for sql in _MEMORY_COUNT_QUERIES:
            try:
                row = mconn.execute(sql, (uid,)).fetchone()
                hits += int(row[0]) if row else 0
            except sqlite3.OperationalError:
                continue
    return hits


def generate_rtbf_erasure_proof(user_id: str) -> dict[str, Any]:
    """Execute Right-to-Be-Forgotten full wipe, verify zero residual records, and store HMAC proof."""
    init_privacy_db()
    uid = up.valid_user_id(user_id)
    removed = up.wipe_data(uid, "all")
    residual = _count_residual_user_rows(uid)
    user_hash = hashlib.sha256(f"rtbf:{uid}".encode()).hexdigest()
    erased_at = datetime.now(UTC).isoformat()
    proof_id = f"rtbf_{secrets.token_hex(8)}"
    removed_json = json.dumps(removed, sort_keys=True, ensure_ascii=False)
    receipt_hmac = hmac.new(
        _master_key_bytes(),
        f"{proof_id}|{user_hash}|{erased_at}|{removed_json}|{residual}".encode(),
        hashlib.sha256,
    ).hexdigest()
    with _privacy_conn() as conn:
        conn.execute(
            "INSERT INTO rtbf_erasure_proofs "
            "(proof_id, user_hash, erased_at, removed_counts_json, residual_hits, receipt_hmac) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (proof_id, user_hash, erased_at, removed_json, residual, receipt_hmac),
        )
    return {
        "ok": residual == 0,
        "proof_id": proof_id,
        "user_hash": user_hash,
        "erased_at": erased_at,
        "removed": removed,
        "residual_hits": residual,
        "receipt_hmac": receipt_hmac,
    }


def list_rtbf_proofs(user_id: str) -> list[dict[str, Any]]:
    init_privacy_db()
    uid = up.valid_user_id(user_id)
    user_hash = hashlib.sha256(f"rtbf:{uid}".encode()).hexdigest()
    with _privacy_conn() as conn:
        rows = conn.execute(
            "SELECT proof_id, user_hash, erased_at, removed_counts_json, residual_hits, receipt_hmac "
            "FROM rtbf_erasure_proofs WHERE user_hash = ? ORDER BY erased_at DESC",
            (user_hash,),
        ).fetchall()
    return [
        {**dict(r), "removed": json.loads(r["removed_counts_json"])}
        for r in rows
    ]


class EncryptRequest(BaseModel):
    plaintext: str = Field(..., min_length=1, max_length=16000)


class DecryptRequest(BaseModel):
    ciphertext: str = Field(..., min_length=8, max_length=32000)


class ScanPayloadRequest(BaseModel):
    filename: str = Field(default="upload.txt", max_length=128)
    content: str = Field(default="", max_length=64000)
    is_base64: bool = False


@router.post("/encrypt")
async def api_encrypt_field(body: EncryptRequest):
    """Encrypt a sensitive text field at rest using authenticated v1 encryption."""
    return {"ok": True, "algorithm": "v1-sha256-ctr-hmac", "ciphertext": encrypt_field(body.plaintext)}


@router.post("/decrypt")
async def api_decrypt_field(body: DecryptRequest):
    """Verify MAC and decrypt a v1 encrypted field."""
    try:
        pt = decrypt_field(body.ciphertext)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"ok": True, "verified": True, "plaintext": pt}


@router.post("/scan-file")
async def api_scan_file(body: ScanPayloadRequest):
    """Scan uploaded text or base64 content for EICAR/executable malware indicators."""
    try:
        raw = base64.b64decode(body.content) if body.is_base64 else body.content.encode("utf-8")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"Geçersiz base64: {exc}") from exc
    return {"ok": True, **scan_payload_malware(raw, body.filename)}


@router.post("/rtbf/{user_id}")
async def api_rtbf_wipe(user_id: str):
    """Execute Right-to-Be-Forgotten erasure and issue a signed cryptographic proof receipt."""
    try:
        return generate_rtbf_erasure_proof(user_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/rtbf/{user_id}/proofs")
async def api_rtbf_proofs(user_id: str):
    """List cryptographic RTBF erasure proof receipts for a user hash."""
    try:
        return {"ok": True, "proofs": list_rtbf_proofs(user_id)}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

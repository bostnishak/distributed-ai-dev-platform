"""Content-addressed file storage (DAT-05).

Bytes are stored once per SHA-256 under ``data/blobs/ab/cd/<sha>``; what users see are ``files`` rows (owner,
name, mime) pointing at a blob. Uploading the same content twice costs no extra disk, a file can only be read
by its owner, and a blob nobody references is removed by ``collect_garbage``.
"""

from __future__ import annotations

import hashlib
import hmac
import os
import secrets
import sqlite3
import time
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import BinaryIO

import config
import dbconn

CHUNK = 1024 * 1024


class BlobError(RuntimeError):
    pass


class FileNotAvailable(LookupError):
    """Raised for a missing file and for someone else's file alike, so ids cannot be probed."""


def blob_root() -> Path:
    return dbconn.data_dir() / "blobs"


def blob_path(sha256: str) -> Path:
    return blob_root() / sha256[:2] / sha256[2:4] / sha256


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def _write_stream(source: bytes | BinaryIO, limit: int) -> tuple[str, int, Path]:
    """Stream into a temp file while hashing; refuse content above ``limit`` without keeping it."""
    root = blob_root()
    root.mkdir(parents=True, exist_ok=True)
    tmp = root / f".incoming-{uuid.uuid4().hex}"
    digest = hashlib.sha256()
    size = 0
    stream = [source] if isinstance(source, bytes) else iter(lambda: source.read(CHUNK), b"")
    try:
        with open(tmp, "wb") as out:
            for chunk in stream:
                size += len(chunk)
                if size > limit:
                    raise BlobError(f"dosya {limit} bayt sınırını aşıyor")
                digest.update(chunk)
                out.write(chunk)
    except BaseException:
        tmp.unlink(missing_ok=True)
        raise
    return digest.hexdigest(), size, tmp


def store(
    conn: sqlite3.Connection,
    owner: str,
    name: str,
    data: bytes | BinaryIO,
    mime: str = "application/octet-stream",
    expires_at: str | None = None,
    limit: int | None = None,
) -> dict:
    sha, size, tmp = _write_stream(data, limit or config.MAX_UPLOAD_BYTES)
    target = blob_path(sha)
    if target.is_file():
        tmp.unlink()
    else:
        target.parent.mkdir(parents=True, exist_ok=True)
        os.replace(tmp, target)
    conn.execute("INSERT OR IGNORE INTO blobs (sha256, size, created_at) VALUES (?, ?, ?)", (sha, size, _now()))
    file_id = uuid.uuid4().hex
    conn.execute(
        "INSERT INTO files (id, owner_id, name, mime, sha256, size, created_at, expires_at) VALUES (?,?,?,?,?,?,?,?)",
        (file_id, owner, Path(name).name or "dosya", mime, sha, size, _now(), expires_at),
    )
    return {"id": file_id, "sha256": sha, "size": size, "name": Path(name).name, "mime": mime}


def _row(conn: sqlite3.Connection, file_id: str, owner: str) -> sqlite3.Row:
    row = conn.execute("SELECT * FROM files WHERE id = ? AND owner_id = ?", (file_id, owner)).fetchone()
    if row is None or (row["expires_at"] and row["expires_at"] <= _now()):
        raise FileNotAvailable(file_id)
    return row


def read(conn: sqlite3.Connection, file_id: str, owner: str) -> bytes:
    row = _row(conn, file_id, owner)
    path = blob_path(row["sha256"])
    if not path.is_file():
        raise BlobError(f"blob diskte yok: {row['sha256']}")
    return path.read_bytes()


def delete(conn: sqlite3.Connection, file_id: str, owner: str) -> None:
    _row(conn, file_id, owner)
    conn.execute("DELETE FROM files WHERE id = ? AND owner_id = ?", (file_id, owner))


def collect_garbage(conn: sqlite3.Connection) -> dict[str, int]:
    """Drop expired file rows, then every blob no file references, and any stray file left on disk."""
    removed = {"expired_files": 0, "blobs": 0, "stray_files": 0}
    removed["expired_files"] = conn.execute(
        "DELETE FROM files WHERE expires_at IS NOT NULL AND expires_at <= ?", (_now(),)
    ).rowcount
    for (sha,) in conn.execute("SELECT sha256 FROM blobs WHERE sha256 NOT IN (SELECT sha256 FROM files)").fetchall():
        blob_path(sha).unlink(missing_ok=True)
        conn.execute("DELETE FROM blobs WHERE sha256 = ?", (sha,))
        removed["blobs"] += 1
    known = {r[0] for r in conn.execute("SELECT sha256 FROM blobs")}
    root = blob_root()
    if root.is_dir():
        for path in root.rglob("*"):
            if path.is_file() and (path.name.startswith(".incoming-") or path.name not in known):
                path.unlink(missing_ok=True)
                removed["stray_files"] += 1
    return removed


def verify(conn: sqlite3.Connection) -> list[str]:
    """Blobs whose bytes are missing or no longer match their hash."""
    problems = []
    for (sha,) in conn.execute("SELECT sha256 FROM blobs").fetchall():
        path = blob_path(sha)
        if not path.is_file():
            problems.append(f"{sha}: dosya yok")
        elif hashlib.sha256(path.read_bytes()).hexdigest() != sha:
            problems.append(f"{sha}: içerik özeti uyuşmuyor")
    return problems


# --- signed, expiring URLs (MM-14) -----------------------------------------------------------


def _signing_key() -> bytes:
    if config.SECRET_KEY:
        return config.SECRET_KEY.encode()
    key_file = dbconn.data_dir() / ".blob_signing_key"
    if not key_file.is_file():
        key_file.parent.mkdir(parents=True, exist_ok=True)
        key_file.write_bytes(secrets.token_bytes(32))
    return key_file.read_bytes()


def sign(file_id: str, owner: str, ttl_seconds: int = 300) -> str:
    expires = int(time.time()) + ttl_seconds
    mac = hmac.new(_signing_key(), f"{file_id}|{owner}|{expires}".encode(), hashlib.sha256).hexdigest()
    return f"{expires}.{mac}"


def check_signature(file_id: str, owner: str, token: str) -> bool:
    try:
        expires_text, mac = token.split(".", 1)
        expires = int(expires_text)
    except ValueError:
        return False
    if expires < time.time():
        return False
    good = hmac.new(_signing_key(), f"{file_id}|{owner}|{expires}".encode(), hashlib.sha256).hexdigest()
    return hmac.compare_digest(good, mac)

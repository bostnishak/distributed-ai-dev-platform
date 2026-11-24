"""SEC-11: Encrypted Secrets Store using Fernet + OS Keyring / SECRET_KEY env.

Stores sensitive credentials (e.g. MCP connector API keys) encrypted with Fernet in a
dedicated SQLite database (`config.DATA_DIR / "secrets.db"`) excluded from backups and exports.
Supports master key rotation (`rotate_master_key`) and CLI invocation:
    python -m secret_store rotate --new-key <NEW_KEY>
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import os
import sqlite3
import sys
from datetime import UTC, datetime
from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken
from keyring.errors import KeyringError

import config
import dbconn

KEYRING_SERVICE = "cm6453-distributed-ai-platform"
KEYRING_ACCOUNT = "master_secret_key"


def secrets_db_path() -> Path:
    return Path(config.DATA_DIR) / "secrets.db"


def _local_key_file() -> Path:
    return Path(config.DATA_DIR) / ".master.key"


def _normalize_fernet_key(raw: str) -> bytes:
    """Convert any non-empty secret string or valid Fernet key into a 32-byte URL-safe base64 Fernet key."""
    candidate = (raw or "").strip().encode("utf-8")
    try:
        decoded = base64.urlsafe_b64decode(candidate)
        if len(decoded) == 32:
            Fernet(candidate)
            return candidate
    except (ValueError, TypeError) as _exc:
        import logging

        logging.getLogger(__name__).debug("Recoverable error suppressed: %s", _exc)
    digest = hashlib.sha256(candidate).digest()
    return base64.urlsafe_b64encode(digest)


def _get_master_key_bytes() -> bytes:
    # 1. Explicit environment / config SECRET_KEY (highest priority, great for CI & servers)
    env_key = (config.SECRET_KEY or os.environ.get("SECRET_KEY") or "").strip()
    if env_key:
        return _normalize_fernet_key(env_key)

    # 2. OS Keyring (Windows Credential Manager / macOS Keychain / Linux SecretService)
    try:
        import keyring

        stored = keyring.get_password(KEYRING_SERVICE, KEYRING_ACCOUNT)
        if stored:
            return _normalize_fernet_key(stored)
        generated = Fernet.generate_key().decode("ascii")
        keyring.set_password(KEYRING_SERVICE, KEYRING_ACCOUNT, generated)
        return generated.encode("ascii")
    except (ImportError, KeyringError, RuntimeError, OSError, ValueError, TypeError) as _exc:
        import logging

        logging.getLogger(__name__).debug("Recoverable error suppressed: %s", _exc)
    # 3. Fallback restricted key file inside DATA_DIR (excluded from backups)
    kf = _local_key_file()
    kf.parent.mkdir(parents=True, exist_ok=True)
    if kf.is_file():
        return _normalize_fernet_key(kf.read_text(encoding="utf-8").strip())
    generated = Fernet.generate_key().decode("ascii")
    kf.write_text(generated, encoding="utf-8")
    if sys.platform != "win32":
        os.chmod(kf, 0o600)
    return generated.encode("ascii")


def _fernet(key_override: str | None = None) -> Fernet:
    key = _normalize_fernet_key(key_override) if key_override else _get_master_key_bytes()
    return Fernet(key)


def _connect() -> sqlite3.Connection:
    p = secrets_db_path()
    return dbconn.open_db(p)


def init_secrets_db() -> None:
    with _connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS secrets (
                name TEXT PRIMARY KEY,
                ciphertext BLOB NOT NULL,
                key_version INTEGER NOT NULL DEFAULT 1,
                updated_at TEXT NOT NULL
            )
            """
        )


def mask_secret(raw: str) -> str:
    k = (raw or "").strip()
    if not k:
        return ""
    if len(k) <= 8:
        return "*" * len(k)
    return f"{k[:4]}...{k[-4:]}"


def set_secret(name: str, plaintext: str) -> None:
    """Encrypt and store a secret under `name` using Fernet."""
    init_secrets_db()
    clean_name = (name or "").strip()[:120]
    if not clean_name:
        raise ValueError("Secret name cannot be empty.")
    token = _fernet().encrypt((plaintext or "").encode("utf-8"))
    now = datetime.now(UTC).isoformat()
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO secrets (name, ciphertext, key_version, updated_at)
            VALUES (?, ?, 1, ?)
            ON CONFLICT(name) DO UPDATE SET
                ciphertext = excluded.ciphertext,
                updated_at = excluded.updated_at
            """,
            (clean_name, token, now),
        )


def get_secret(name: str) -> str:
    """Decrypt and return the plaintext secret for `name`, or empty string if absent."""
    init_secrets_db()
    with _connect() as conn:
        row = conn.execute("SELECT ciphertext FROM secrets WHERE name = ?", ((name or "").strip(),)).fetchone()
    if not row:
        return ""
    try:
        return _fernet().decrypt(bytes(row["ciphertext"])).decode("utf-8")
    except InvalidToken:
        return ""


def delete_secret(name: str) -> bool:
    init_secrets_db()
    with _connect() as conn:
        cur = conn.execute("DELETE FROM secrets WHERE name = ?", ((name or "").strip(),))
    return cur.rowcount > 0


def rotate_master_key(new_secret_key: str, old_secret_key: str | None = None) -> int:
    """Re-encrypt all stored secrets from the current/old master key to `new_secret_key`."""
    if not (new_secret_key or "").strip():
        raise ValueError("New secret key cannot be empty.")
    init_secrets_db()
    old_f = _fernet(old_secret_key)
    new_f = _fernet(new_secret_key)
    now = datetime.now(UTC).isoformat()
    rotated = 0
    with _connect() as conn:
        rows = conn.execute("SELECT name, ciphertext, key_version FROM secrets").fetchall()
        for row in rows:
            plain = old_f.decrypt(bytes(row["ciphertext"]))
            new_ct = new_f.encrypt(plain)
            conn.execute(
                "UPDATE secrets SET ciphertext = ?, key_version = ?, updated_at = ? WHERE name = ?",
                (new_ct, int(row["key_version"]) + 1, now, row["name"]),
            )
            rotated += 1

    # Persist rotated master key into config + keyring / fallback key file
    config.SECRET_KEY = new_secret_key.strip()
    os.environ["SECRET_KEY"] = config.SECRET_KEY
    try:
        import keyring

        keyring.set_password(KEYRING_SERVICE, KEYRING_ACCOUNT, config.SECRET_KEY)
    except (ImportError, KeyringError, RuntimeError, OSError, ValueError, TypeError):
        kf = _local_key_file()
        if kf.is_file():
            kf.write_text(config.SECRET_KEY, encoding="utf-8")
    return rotated


def _cli() -> None:
    parser = argparse.ArgumentParser(description="CM6453 Encrypted Secret Store CLI")
    sub = parser.add_subparsers(dest="cmd", required=True)
    rot = sub.add_parser("rotate", help="Rotate master key and re-encrypt all secrets")
    rot.add_argument("--new-key", required=True, help="New master key string or Fernet key")
    rot.add_argument("--old-key", default=None, help="Optional previous master key")
    args = parser.parse_args()
    if args.cmd == "rotate":
        count = rotate_master_key(args.new_key, old_secret_key=args.old_key)
        print(f"Rotated {count} secret(s) successfully.")


if __name__ == "__main__":
    _cli()

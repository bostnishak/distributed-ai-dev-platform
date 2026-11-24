"""SEC-12: Password-Encrypted & Verifiable Enterprise Backup & Restore (`master/backup_manager.py`).

- Produces AES-256 encrypted ZIP archives (`pyzipper.AESZipFile`) with a SHA-256 integrity
  manifest (`backup/BACKUP_MANIFEST.json`).
- Strictly excludes secrets (`secrets.db`, `.master.key`) so encrypted backups never carry
  plaintext or master secret key material (SEC-11).
- Provides `GET /api/admin/backup.zip` and `POST /api/admin/backup/restore` with full
  password verification (HTTP 400 on wrong password) and SHA-256 checksum verification.
"""

from __future__ import annotations

import hashlib
import io
import json
import zipfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pyzipper
from fastapi import APIRouter, Depends, File, Form, Header, HTTPException, Query, UploadFile
from fastapi.responses import Response

import config
import secret_store
from access_control import require_local_or_admin
from audit_log import AuditTrail

router = APIRouter(prefix="/api/admin", tags=["admin"])

_SKIP_DIRS = {".git", "__pycache__", "node_modules", "build", ".venv", "venv"}
_EXCLUDED_SECRET_FILES = {"secrets.db", "secrets.db-wal", "secrets.db-shm", ".master.key"}


def _default_backup_password() -> str:
    if (config.BACKUP_PASSWORD or "").strip():
        return config.BACKUP_PASSWORD.strip()
    # Derive a stable local fallback passphrase from the master key so archives are ALWAYS AES-256 encrypted
    raw = secret_store._get_master_key_bytes()
    return hashlib.sha256(b"backup-aes:" + raw).hexdigest()[:32]


def create_enterprise_backup_zip(
    data_dir: Path | None = None,
    password: str | None = None,
) -> bytes:
    """Create an AES-256 password-encrypted ZIP archive with SHA-256 manifest, excluding secret files."""
    base = Path(data_dir) if data_dir is not None else Path(config.DATA_DIR)
    pwd = (password or "").strip() or _default_backup_password()
    buf = io.BytesIO()
    manifest_files: dict[str, dict[str, Any]] = {}

    with pyzipper.AESZipFile(
        buf,
        "w",
        compression=pyzipper.ZIP_DEFLATED,
        encryption=pyzipper.WZ_AES,
    ) as zf:
        zf.setpassword(pwd.encode("utf-8"))
        if base.is_dir():
            for path in sorted(base.rglob("*")):
                if any(part in _SKIP_DIRS for part in path.parts):
                    continue
                if not path.is_file():
                    continue
                if path.name.lower() in _EXCLUDED_SECRET_FILES:
                    continue
                if path.suffix.lower() in (".exe", ".dll", ".tmp"):
                    continue
                rel = path.relative_to(base).as_posix()
                try:
                    raw_bytes = path.read_bytes()
                except OSError:
                    continue
                arcname = f"backup/{rel}"
                zf.writestr(arcname, raw_bytes)
                manifest_files[rel] = {
                    "size": len(raw_bytes),
                    "sha256": hashlib.sha256(raw_bytes).hexdigest(),
                }

        manifest = {
            "format": "cm6453-encrypted-backup-v2",
            "encryption": "AES-256",
            "generated_utc": datetime.now(UTC).isoformat(),
            "file_count": len(manifest_files),
            "files": manifest_files,
        }
        zf.writestr("backup/BACKUP_MANIFEST.json", json.dumps(manifest, ensure_ascii=False, indent=2).encode("utf-8"))

    return buf.getvalue()


def _read_backup_manifest(zf: pyzipper.AESZipFile) -> dict[str, Any]:
    try:
        manifest_bytes = zf.read("backup/BACKUP_MANIFEST.json")
    except KeyError as exc:
        raise ValueError("Yedek arşivinde bütünlük manifesti (BACKUP_MANIFEST.json) eksik.") from exc
    except RuntimeError as exc:
        raise ValueError("Yanlış yedek parolası veya bozuk şifreli arşiv.") from exc
    return json.loads(manifest_bytes.decode("utf-8"))


def _stage_verified_files(
    zf: pyzipper.AESZipFile,
    expected_files: dict[str, dict[str, Any]],
    dest_root: Path,
) -> list[tuple[Path, bytes, str]]:
    staged: list[tuple[Path, bytes, str]] = []
    for rel, meta in expected_files.items():
        clean_rel = rel.replace("\\", "/").lstrip("/")
        if Path(clean_rel).name.lower() in _EXCLUDED_SECRET_FILES:
            continue
        target = (dest_root / clean_rel).resolve()
        if dest_root != target and dest_root not in target.parents:
            raise ValueError(f"Güvenlik ihlali: geçersiz arşiv yolu ({rel}).")
        try:
            content = zf.read(f"backup/{clean_rel}")
        except RuntimeError as exc:
            raise ValueError("Yanlış yedek parolası veya şifre çözme hatası.") from exc
        except KeyError as exc:
            raise ValueError(f"Manifestte kayıtlı dosya arşivde eksik: {rel}") from exc

        actual_sha = hashlib.sha256(content).hexdigest()
        if actual_sha != meta.get("sha256"):
            raise ValueError(f"Bütünlük doğrulaması başarısız (SHA-256 uyuşmuyor): {rel}")
        staged.append((target, content, clean_rel))
    return staged


def restore_enterprise_backup_zip(
    raw_zip: bytes,
    password: str,
    target_dir: Path | None = None,
) -> dict[str, Any]:
    """Decrypt an AES-256 backup archive, verify every SHA-256 digest, and restore into `target_dir`."""
    pwd = (password or "").strip()
    if not pwd:
        raise ValueError("Geri yükleme parolası zorunludur.")

    dest_root = (Path(target_dir) if target_dir is not None else Path(config.DATA_DIR)).resolve()
    dest_root.mkdir(parents=True, exist_ok=True)

    try:
        zf = pyzipper.AESZipFile(io.BytesIO(raw_zip), "r")
    except (zipfile.BadZipFile, OSError) as exc:
        raise ValueError("Geçersiz veya bozuk ZIP arşivi.") from exc

    restored_files: list[str] = []
    with zf:
        zf.setpassword(pwd.encode("utf-8"))
        manifest = _read_backup_manifest(zf)
        expected_files: dict[str, dict[str, Any]] = manifest.get("files") or {}
        staged = _stage_verified_files(zf, expected_files, dest_root)
        for target, content, clean_rel in staged:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(content)
            restored_files.append(clean_rel)

    return {
        "ok": True,
        "restored_count": len(restored_files),
        "verified_sha256": True,
        "files": restored_files,
        "generated_utc": manifest.get("generated_utc", ""),
    }


@router.get("/backup.zip", dependencies=[Depends(require_local_or_admin)])
async def download_enterprise_backup(
    password: str = Query("", max_length=128),
    x_backup_password: str = Header(default=""),
):
    """Download an AES-256 password-encrypted enterprise backup ZIP archive (secrets excluded)."""
    chosen_pwd = (password or x_backup_password or "").strip() or None
    raw_zip = create_enterprise_backup_zip(password=chosen_pwd)
    AuditTrail().append_event(
        actor="admin",
        action="BACKUP_CREATED",
        payload={"encrypted": True, "size_bytes": len(raw_zip), "custom_password": bool(chosen_pwd)},
    )
    ts = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
    return Response(
        content=raw_zip,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="platform-backup-{ts}.zip"'},
    )


@router.post("/backup/restore", dependencies=[Depends(require_local_or_admin)])
async def restore_enterprise_backup(
    file: UploadFile = File(...),  # noqa: B008
    password: str = Form(...),
):
    """Verify AES-256 password & SHA-256 manifest and restore an encrypted enterprise backup."""
    raw = await file.read()
    try:
        res = restore_enterprise_backup_zip(raw, password=password)
    except ValueError as exc:
        AuditTrail().append_event(
            actor="admin",
            action="BACKUP_RESTORE_FAILED",
            payload={"filename": file.filename or "", "reason": str(exc)},
        )
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    AuditTrail().append_event(
        actor="admin",
        action="BACKUP_RESTORED",
        payload={"filename": file.filename or "", "restored_count": res["restored_count"]},
    )
    return res

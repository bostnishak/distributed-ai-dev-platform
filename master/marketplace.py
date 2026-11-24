"""EPK-29: Signed Marketplace Registry (SHA-256 + HMAC Signature, Permission Preview & Install Lifecycle)."""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import sqlite3
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

import dbconn

router = APIRouter(prefix="/api/marketplace", tags=["marketplace"])


def _connect() -> sqlite3.Connection:
    return dbconn.open_db(dbconn.database_file("platform.db"))


def _signing_key() -> bytes:
    seed = os.environ.get("DADP_MARKETPLACE_KEY", "").strip() or os.environ.get("ADMIN_TOKEN", "").strip() or "dadp-marketplace-dev-key"
    return hashlib.sha256(seed.encode("utf-8")).digest()


def init_marketplace_db() -> None:
    with _connect() as conn:
        conn.execute(
            "CREATE TABLE IF NOT EXISTS marketplace_packages ("
            "package_id TEXT PRIMARY KEY, name TEXT NOT NULL, version TEXT NOT NULL, kind TEXT NOT NULL, "
            "permissions_json TEXT NOT NULL DEFAULT '[]', sha256_digest TEXT NOT NULL, "
            "signature_hmac TEXT NOT NULL, installed INTEGER NOT NULL DEFAULT 0, created_at TEXT NOT NULL)"
        )


def sign_package_manifest(package_id: str, version: str, permissions: list[str]) -> tuple[str, str]:
    canonical = json.dumps({"package_id": package_id, "version": version, "permissions": sorted(permissions)}, sort_keys=True)
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    sig = hmac.new(_signing_key(), digest.encode("utf-8"), hashlib.sha256).hexdigest()
    return digest, sig


def publish_package(package_id: str, name: str, version: str, kind: str, permissions: list[str]) -> dict[str, Any]:
    init_marketplace_db()
    digest, sig = sign_package_manifest(package_id, version, permissions)
    now = datetime.now(UTC).isoformat()
    with _connect() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO marketplace_packages "
            "(package_id, name, version, kind, permissions_json, sha256_digest, signature_hmac, installed, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, 0, ?)",
            (package_id, name.strip(), version.strip(), kind.strip(), json.dumps(sorted(permissions)), digest, sig, now),
        )
    return {"ok": True, "package_id": package_id, "sha256_digest": digest, "signature_hmac": sig, "permissions": sorted(permissions)}


def install_package(package_id: str, *, approved_permissions: bool = False) -> dict[str, Any]:
    init_marketplace_db()
    with _connect() as conn:
        row = conn.execute("SELECT * FROM marketplace_packages WHERE package_id = ?", (package_id,)).fetchone()
        if not row:
            raise KeyError(f"Paket bulunamadı: {package_id}")
        perms: list[str] = json.loads(row["permissions_json"])
        _, expected_sig = sign_package_manifest(str(row["package_id"]), str(row["version"]), perms)
        if not hmac.compare_digest(str(row["signature_hmac"]), expected_sig):
            raise ValueError("Paket kriptografik imza doğrulaması başarısız.")
        if perms and not approved_permissions:
            raise PermissionError(f"Kurulum için izin onayı gerekir: {', '.join(perms)}")
        conn.execute("UPDATE marketplace_packages SET installed = 1 WHERE package_id = ?", (package_id,))
    return {"ok": True, "package_id": package_id, "installed": True, "verified_signature": True, "permissions": perms}


def uninstall_package(package_id: str) -> dict[str, Any]:
    init_marketplace_db()
    with _connect() as conn:
        cnt = conn.execute("UPDATE marketplace_packages SET installed = 0 WHERE package_id = ?", (package_id,)).rowcount
    if not cnt:
        raise KeyError(f"Paket bulunamadı: {package_id}")
    return {"ok": True, "package_id": package_id, "installed": False}


def list_packages() -> list[dict[str, Any]]:
    init_marketplace_db()
    with _connect() as conn:
        rows = conn.execute("SELECT * FROM marketplace_packages ORDER BY created_at DESC").fetchall()
    return [{**dict(r), "permissions": json.loads(r["permissions_json"]), "installed": bool(r["installed"])} for r in rows]


class PublishPackageRequest(BaseModel):
    package_id: str = Field(..., min_length=2, max_length=64)
    name: str = Field(..., min_length=2, max_length=80)
    version: str = Field(default="1.0.0", max_length=24)
    kind: str = Field(default="template", pattern="^(template|tool|agent)$")
    permissions: list[str] = Field(default_factory=list)


class InstallPackageRequest(BaseModel):
    package_id: str = Field(..., min_length=2, max_length=64)
    approved_permissions: bool = False


@router.get("/items")
async def api_list_marketplace():
    """List signed templates, tools, and agent packages in the local marketplace."""
    items = list_packages()
    return {"ok": True, "count": len(items), "items": items}


@router.post("/publish")
async def api_publish_package(body: PublishPackageRequest):
    """Sign and publish a template, tool, or agent package manifest."""
    return publish_package(body.package_id, body.name, body.version, body.kind, body.permissions)


@router.post("/install")
async def api_install_package(body: InstallPackageRequest):
    """Verify package HMAC signature and explicit permission approval before installation."""
    try:
        return install_package(body.package_id, approved_permissions=body.approved_permissions)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.delete("/items/{package_id}")
async def api_uninstall_package(package_id: str):
    """Uninstall an active marketplace package."""
    try:
        return uninstall_package(package_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

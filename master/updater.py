"""EPK-24: Platform Version Check, SemVer Comparison, Signed Release Checksum & Rollback Info."""

from __future__ import annotations

import hashlib
from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/admin/update", tags=["admin-updater"])

CURRENT_PLATFORM_VERSION = "2.5.0"


def _parse_semver(v: str) -> tuple[int, int, int]:
    parts = [int(x) for x in v.strip().lstrip("v").split(".")[:3] if x.isdigit()]
    while len(parts) < 3:
        parts.append(0)
    return parts[0], parts[1], parts[2]


def check_update_status(available_version: str = CURRENT_PLATFORM_VERSION) -> dict[str, Any]:
    cur = _parse_semver(CURRENT_PLATFORM_VERSION)
    avail = _parse_semver(available_version)
    return {
        "ok": True,
        "current_version": CURRENT_PLATFORM_VERSION,
        "available_version": available_version,
        "update_available": avail > cur,
        "rollback_supported": True,
        "installer_script": "scripts/install_windows.ps1",
    }


def verify_release_artifact(payload: str, expected_sha256: str) -> dict[str, Any]:
    actual = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    return {"ok": True, "verified": actual.lower() == expected_sha256.strip().lower(), "actual_sha256": actual}


class VerifyReleaseRequest(BaseModel):
    payload: str = Field(..., min_length=1, max_length=64000)
    expected_sha256: str = Field(..., min_length=64, max_length=64)


@router.get("/status")
async def api_update_status(available_version: str = CURRENT_PLATFORM_VERSION):
    """Return platform version, SemVer update availability, and rollback capability status."""
    return check_update_status(available_version)


@router.post("/verify-release")
async def api_verify_release(body: VerifyReleaseRequest):
    """Verify SHA-256 integrity of a release manifest/package before applying an update."""
    return verify_release_artifact(body.payload, body.expected_sha256)

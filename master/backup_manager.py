"""Section 5.3: One-Click Enterprise Backup & Portability Archive (`master/backup_manager.py`).

Provides `GET /api/admin/backup.zip` exporting SQLite databases (`platform.db`, `user_profile.db`,
`cognitive_memory.db`, `graph_rag.db`, `cmm_quality.db`), `cnc_jobs/`, and `workspaces/` into a
single timestamped ZIP archive.
"""

from __future__ import annotations

import io
import zipfile
from datetime import UTC, datetime
from pathlib import Path

from fastapi import APIRouter, Depends
from fastapi.responses import Response

import config
from access_control import require_local_or_admin

router = APIRouter(prefix="/api/admin", tags=["admin"])

_SKIP_DIRS = {".git", "__pycache__", "node_modules", "build", ".venv", "venv"}


def create_enterprise_backup_zip(data_dir: Path | None = None) -> bytes:
    """Create an in-memory ZIP archive containing all platform SQLite DBs, CNC jobs, and workspaces."""
    base = Path(data_dir) if data_dir is not None else Path(config.DATA_DIR)
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        if base.is_dir():
            for path in sorted(base.rglob("*")):
                if any(part in _SKIP_DIRS for part in path.parts):
                    continue
                if not path.is_file():
                    continue
                if path.suffix.lower() in (".exe", ".dll", ".tmp"):
                    continue
                rel = path.relative_to(base).as_posix()
                try:
                    zf.write(path, arcname=f"backup/{rel}")
                except OSError:
                    continue
        zf.writestr(
            "backup/BACKUP_MANIFEST.txt",
            f"Distributed AI Software Development Platform Backup\nGenerated UTC: {datetime.now(UTC).isoformat()}\n",
        )
    return buf.getvalue()


@router.get("/backup.zip", dependencies=[Depends(require_local_or_admin)])
async def download_enterprise_backup():
    """Download a full timestamped enterprise backup ZIP archive."""
    raw_zip = create_enterprise_backup_zip()
    ts = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
    return Response(
        content=raw_zip,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="platform-backup-{ts}.zip"'},
    )

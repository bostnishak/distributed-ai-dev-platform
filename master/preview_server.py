"""SEC-17: Isolated Second-Origin Preview Server for Generated Web Workspaces.

Serves ONLY static workspace preview files on a dedicated separate origin (`127.0.0.1:8001`
by default, configurable via `config.PREVIEW_PORT`):
- Zero `/api/*` endpoints mounted -> generated scripts cannot call master APIs on this origin.
- No session/CSRF cookies ever issued or accepted on this origin.
- Enforces sandbox CSP allowing interactive web apps (`localStorage`, forms, modals, Canvas,
  and same-origin static `fetch('./data/...')`) strictly inside the isolated preview origin.
"""

from __future__ import annotations

import logging
import mimetypes
import threading
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse

import config
import workspace_builder as wb

preview_app = FastAPI(title="CM6453 Isolated Workspace Preview Origin", docs_url=None, redoc_url=None, openapi_url=None)

_PREVIEW_CSP = (
    "sandbox allow-scripts allow-same-origin allow-forms allow-modals; "
    "default-src 'self' 'unsafe-inline' data: blob:; "
    "connect-src 'self' data: blob:; "
    "frame-ancestors 'self' http://127.0.0.1:* http://localhost:*"
)


def _resolve_preview_target(ws_dir: Path, rel: str) -> Path | None:
    """Resolve a preview file inside ws_dir, checking root, public/, and frontend/ safely."""
    for candidate in (rel, f"public/{rel}", f"frontend/{rel}"):
        try:
            path = wb.safe_file_path(ws_dir, candidate)
        except ValueError:
            continue
        if path.is_file():
            return path
    return None


@preview_app.get("/preview/{ws_id}/{filepath:path}")
async def serve_isolated_preview(ws_id: str, filepath: str):
    """Serve static files from a generated workspace on an isolated origin without cookies or API access."""
    try:
        ws_dir = wb.safe_workspace_dir(ws_id)
        rel = filepath or "index.html"
        wb.safe_file_path(ws_dir, rel)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    target = _resolve_preview_target(ws_dir, rel)
    if target is None:
        raise HTTPException(status_code=404, detail="Önizleme dosyası bulunamadı.")
    media, _ = mimetypes.guess_type(str(target))
    return FileResponse(
        target,
        media_type=media or "application/octet-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Content-Type-Options": "nosniff",
            "Content-Security-Policy": _PREVIEW_CSP,
        },
    )


_STATE: dict[str, bool] = {"preview_started": False}


def get_preview_origin() -> str:
    return f"http://127.0.0.1:{config.PREVIEW_PORT}"


def start_preview_server_background() -> None:
    """Start the isolated second-origin preview server in a daemon thread (idempotent & port-safe)."""
    if _STATE["preview_started"]:
        return
    import socket

    # If port is already listening (e.g. another worker or existing preview server), skip cleanly
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        if sock.connect_ex(("127.0.0.1", config.PREVIEW_PORT)) == 0:
            _STATE["preview_started"] = True
            return
    _STATE["preview_started"] = True

    def _run() -> None:
        try:
            import uvicorn

            uvicorn.run(
                preview_app,
                host="127.0.0.1",
                port=config.PREVIEW_PORT,
                log_level="warning",
                access_log=False,
            )
        except (SystemExit, ImportError, OSError, RuntimeError, ValueError) as exc:
            logging.getLogger(__name__).debug("preview origin server stopped: %s", exc)

    threading.Thread(target=_run, name="preview-origin-server", daemon=True).start()

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

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse

import asset_vault
import config
import process_registry
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


@preview_app.get("/vendor/{filepath:path}")
async def serve_vault(filepath: str):
    """The local asset vault, read-only, so a page can use a library or font without the internet."""
    root = asset_vault.source().resolve()
    target = (root / filepath).resolve()
    if root not in target.parents or not target.is_file():
        raise HTTPException(status_code=404, detail="Kasada yok.")
    media, _ = mimetypes.guess_type(str(target))
    return FileResponse(target, media_type=media or "application/octet-stream", headers={"X-Content-Type-Options": "nosniff", "Cache-Control": "max-age=86400"})


_STATE: dict[str, int] = {"port": 0}
_MARK = "cm6453-preview"


@preview_app.get("/preview-identity")
async def preview_identity():
    return {"service": _MARK}


def _is_preview(port: int) -> bool:
    """Whether what listens there is really our preview origin, not just any program on the usual port."""
    try:
        return httpx.get(f"http://127.0.0.1:{port}/preview-identity", timeout=2).json().get("service") == _MARK
    except (httpx.HTTPError, ValueError, AttributeError):
        return False


def get_preview_origin() -> str:
    return f"http://127.0.0.1:{_STATE['port'] or config.PREVIEW_PORT}"


def start_preview_server_background() -> None:
    """Start the preview origin (idempotent). A foreign program on the usual port gets a neighbour port, never our previews."""
    if _STATE["port"]:
        return
    wanted = config.PREVIEW_PORT
    if not process_registry.free_port(wanted):
        if _is_preview(wanted):
            _STATE["port"] = wanted  # another worker already serves it
            return
        wanted = process_registry.lease_port(range(config.PREVIEW_PORT + 1, config.PREVIEW_PORT + 40))
        logging.getLogger(__name__).warning("önizleme portu %s başka bir programda; %s kullanılıyor", config.PREVIEW_PORT, wanted)
    _STATE["port"] = wanted

    def _run() -> None:
        try:
            import uvicorn

            uvicorn.run(preview_app, host="127.0.0.1", port=wanted, log_level="warning", access_log=False)
        except (SystemExit, ImportError, OSError, RuntimeError, ValueError) as exc:
            logging.getLogger(__name__).warning("preview origin server stopped: %s", exc)

    threading.Thread(target=_run, name="preview-origin-server", daemon=True).start()

"""The glass box: what the machine is doing, what was proved, one-click undo and what was left unfinished.

  GET  /api/glass/hardware              video memory, temperature, loaded model, CPU, RAM, isolation, gear
  GET  /api/glass/unfinished            builds that stopped before they were done (they continue with "devam et")
  GET  /api/glass/proof/{ws_id}         delivery proofs as green and red marks, live preview and screenshots
  GET  /api/glass/film/{ws_id}/{name}   one screenshot of the proof
  POST /api/glass/undo/{ws_id}          the project as it was before the last change
"""

from __future__ import annotations

import re
import time
from pathlib import Path
from typing import Any

import psutil
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse

import checkpoint
import cluster_telemetry
import filmstrip
import gpu_watch
import run_evidence
import workspace_builder as wb
from access_control import require_local_or_admin

router = APIRouter(prefix="/api/glass", tags=["glass-box"])
BEFORE = "önce: "
_ISOLATION: dict[str, Any] = {"at": -1e9, "text": ""}
_STAGES = {"A": "Statik denetim (sözdizimi, güvenlik, kaçamak)", "B": "Kod testleri ve mutasyon", "C": "Canlı çalıştırma ve tarayıcı", "D": "İmzalı kayıt"}
_FILM_RE = re.compile(r"^[\w-]{1,80}\.png$")
GEAR: dict[str, str] = {"last": "-"}


def snapshot_before(ws_dir: Path, instruction: str) -> None:
    """Taken before a change, so the change can be taken back with one click."""
    wb.create_snapshot(ws_dir, BEFORE + instruction[:60])


def _isolation() -> str:
    if time.monotonic() - _ISOLATION["at"] > 30:
        _ISOLATION.update(at=time.monotonic(), text=run_evidence.isolation_tier())
    return _ISOLATION["text"]


@router.get("/hardware", dependencies=[Depends(require_local_or_admin)])
def hardware() -> dict[str, Any]:
    card = gpu_watch.read()
    memory = psutil.virtual_memory()
    return {
        "vram_used_gb": round(card.used_mb / 1024, 1) if card else None,
        "vram_total_gb": round(card.total_mb / 1024, 1) if card else None,
        "temperature_c": card.temperature if card else None,
        "models": [m["name"] for m in cluster_telemetry._query_ollama_warm_models()],
        "cpu_percent": psutil.cpu_percent(interval=None),
        "ram_used_gb": round((memory.total - memory.available) / 2**30, 1),
        "ram_total_gb": round(memory.total / 2**30, 1),
        "isolation": _isolation(),
        "gear": GEAR["last"],
        "waiting": gpu_watch.hold_reason(),
    }


@router.get("/unfinished", dependencies=[Depends(require_local_or_admin)])
def unfinished() -> dict[str, Any]:
    found = []
    for workspace in wb.list_workspaces():
        ws_id = str(workspace.get("id", ""))
        try:
            data = checkpoint.load(wb.safe_workspace_dir(ws_id))
        except (ValueError, OSError):
            continue
        if data:
            found.append({"id": ws_id, "name": str(workspace.get("name") or ws_id), "done": len(data.get("done", [])), "total": len(data["files"]), "request": data.get("request", "")[:200]})
    return {"unfinished": found[:5]}


def _folder(ws_id: str) -> Path:
    try:
        ws_dir = wb.safe_workspace_dir(ws_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if not ws_dir.is_dir():
        raise HTTPException(status_code=404, detail="Proje bulunamadı.")
    return ws_dir


@router.get("/proof/{ws_id}", dependencies=[Depends(require_local_or_admin)])
def proof(ws_id: str) -> dict[str, Any]:
    ws_dir = _folder(ws_id)
    known = run_evidence.proofs(ws_id)
    marks = [{"name": _STAGES.get(stage, stage), "state": str(result[0]), "detail": str(result[1])[:400]} for stage, result in sorted(known["stages"].items())]
    return {
        "marks": marks,
        "evidence": known["evidence"],
        "open": known["open"],
        "preview": f"/api/studio/workspaces/{ws_id}/preview/index.html" if (ws_dir / "index.html").is_file() else "",
        "film": filmstrip.names(ws_dir),
        "versions": len(wb.list_snapshots(ws_dir)),
    }


@router.get("/film/{ws_id}/{name}", dependencies=[Depends(require_local_or_admin)])
def film(ws_id: str, name: str) -> FileResponse:
    path = _folder(ws_id) / filmstrip.FOLDER / name
    if not _FILM_RE.match(name) or not path.is_file():
        raise HTTPException(status_code=404, detail="Görüntü yok.")
    return FileResponse(path, media_type="image/png")


@router.post("/undo/{ws_id}", dependencies=[Depends(require_local_or_admin)])
def undo(ws_id: str) -> dict[str, Any]:
    """Restores the newest "before the change" snapshot that differs from the files as they are now."""
    ws_dir = _folder(ws_id)
    started = time.perf_counter()
    for snapshot in wb.list_snapshots(ws_dir):
        label = str(snapshot.get("label", ""))
        if label.startswith(BEFORE) and _differs(ws_dir, ws_dir / ".history" / snapshot["version"]):
            wb.restore_snapshot(ws_id, snapshot["version"])
            return {"restored": snapshot["version"], "undone": label[len(BEFORE) :], "ms": round((time.perf_counter() - started) * 1000)}
    raise HTTPException(status_code=409, detail="Geri alınacak bir değişiklik yok.")


def _differs(ws_dir: Path, snapshot: Path) -> bool:
    now = {rel: (ws_dir / rel).read_bytes() for rel in wb.list_relative_files(ws_dir) if not rel.startswith("dist/")}
    then = {p.relative_to(snapshot).as_posix(): p.read_bytes() for p in snapshot.rglob("*") if p.is_file() and p.name != ".snapshot.json"}
    return now != then

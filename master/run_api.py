"""War room API: watch runs live over a WebSocket, pause, resume, steer, edit waiting steps, branch from a version."""

from __future__ import annotations

import asyncio
import json
import re
import shutil
from datetime import UTC, datetime
from typing import Any
from urllib.parse import urlsplit

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field

import config
import run_control
import run_evidence
import workspace_builder as wb
from access_control import LOCAL_HOSTS, require_local_or_admin

router = APIRouter(prefix="/api/runs", tags=["runs"])
_VERSION_RE = re.compile(r"^v\d{1,5}$")
_PUSH_S = 0.4


class Note(BaseModel):
    note: str = Field(min_length=2, max_length=400)


class NodeEdit(BaseModel):
    node: str = Field(max_length=300)
    purpose: str = Field(default="", max_length=600)
    skip: bool = False


class Branch(BaseModel):
    version: str = Field(max_length=8)


def _live(run_id: str) -> run_control.Run:
    run = run_control.get(run_id)
    if run is None or run.state not in ("running", "paused"):
        raise HTTPException(status_code=404, detail="Çalışan bir iş bulunamadı.")
    return run


@router.get("", dependencies=[Depends(require_local_or_admin)])
def runs() -> dict[str, Any]:
    return {"runs": run_control.recent()}


@router.get("/{run_id}/events", dependencies=[Depends(require_local_or_admin)])
def events(run_id: str) -> dict[str, Any]:
    return {"events": run_control.events_of(run_id)}


@router.post("/{run_id}/pause", dependencies=[Depends(require_local_or_admin)])
async def pause(run_id: str) -> dict[str, Any]:
    run = _live(run_id)
    run.pause()
    return run.summary()


@router.post("/{run_id}/resume", dependencies=[Depends(require_local_or_admin)])
async def resume(run_id: str) -> dict[str, Any]:
    run = _live(run_id)
    run.resume()
    return run.summary()


@router.post("/{run_id}/steer", dependencies=[Depends(require_local_or_admin)])
async def steer(run_id: str, body: Note) -> dict[str, Any]:
    run = _live(run_id)
    run.steer(body.note)
    return run.summary()


@router.post("/{run_id}/node", dependencies=[Depends(require_local_or_admin)])
async def node(run_id: str, body: NodeEdit) -> dict[str, Any]:
    run = _live(run_id)
    if not run.edit(body.node, body.purpose, body.skip):
        raise HTTPException(status_code=409, detail="Yalnız henüz başlamamış adımlar değiştirilebilir.")
    return run.summary()


def branch_workspace(ws_id: str, version: str) -> dict[str, Any]:
    """A new workspace holding exactly the files of one saved version; the original is not touched."""
    source = wb.safe_workspace_dir(ws_id)
    snapshot = source / ".history" / version
    if not _VERSION_RE.match(version) or not snapshot.is_dir():
        raise ValueError("Böyle bir sürüm yok.")
    meta = wb.load_workspace_meta(source)
    name = f"{meta.get('name', ws_id)} ({version} dalı)"
    new_id = wb.make_workspace_id(name)
    target = wb.safe_workspace_dir(new_id)
    shutil.copytree(snapshot, target, ignore=shutil.ignore_patterns(".snapshot.json"))
    now = datetime.now(UTC).isoformat()
    meta.update(id=new_id, name=name, created_at=now, updated_at=now, branched_from={"workspace": ws_id, "version": version})
    wb.create_snapshot(target, f"{ws_id} {version} sürümünden dallandı")
    meta["versions"] = wb.list_snapshots(target)
    wb.save_workspace_meta(target, meta)
    return meta


@router.get("/versions/{ws_id}", dependencies=[Depends(require_local_or_admin)])
def versions(ws_id: str) -> dict[str, Any]:
    try:
        return {"versions": wb.list_snapshots(wb.safe_workspace_dir(ws_id))}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/compare/{ws_id}", dependencies=[Depends(require_local_or_admin)])
def compare(ws_id: str) -> dict[str, Any]:
    try:
        return run_evidence.compare_with_origin(ws_id)
    except (ValueError, OSError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/proof/{ws_id}", dependencies=[Depends(require_local_or_admin)])
def proof(ws_id: str) -> dict[str, Any]:
    try:
        return run_evidence.proofs(ws_id)
    except (ValueError, OSError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/branch/{ws_id}", dependencies=[Depends(require_local_or_admin)])
def branch(ws_id: str, body: Branch) -> dict[str, Any]:
    try:
        return {"workspace": branch_workspace(ws_id, body.version)}
    except (ValueError, OSError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


def _same_origin_local(socket: WebSocket) -> bool:
    """A WebSocket is not covered by the HTTP same-origin checks, so it is checked here."""
    host = socket.client.host if socket.client else ""
    origin = socket.headers.get("origin", "")
    if origin and urlsplit(origin).netloc != socket.headers.get("host", ""):
        return False
    return host in LOCAL_HOSTS and config.LOOPBACK_PRIVILEGE


async def _push(socket: WebSocket, watch: dict[str, Any]) -> None:
    listing = ""
    while True:
        current = [{k: v for k, v in r.items() if k != "nodes"} for r in run_control.recent()]
        message: dict[str, Any] = {}
        if (encoded := json.dumps(current)) != listing:
            listing, message["runs"] = encoded, current
        if run_id := watch["id"]:
            fresh = run_control.events_of(run_id)[watch["sent"] :]
            if fresh:
                watch["sent"] += len(fresh)
                message.update(run=run_id, events=fresh)
        if message:
            await socket.send_json(message)
        await asyncio.sleep(_PUSH_S)


@router.websocket("/ws")
async def live(socket: WebSocket) -> None:
    if not _same_origin_local(socket):
        await socket.close(code=1008)
        return
    await socket.accept()
    watch: dict[str, Any] = {"id": "", "sent": 0}
    sender = asyncio.create_task(_push(socket, watch))
    try:
        while True:
            asked = await socket.receive_json()
            if isinstance(asked, dict):
                watch.update(id=str(asked.get("watch", ""))[:12], sent=0)
    except (WebSocketDisconnect, ValueError):
        pass
    finally:
        sender.cancel()

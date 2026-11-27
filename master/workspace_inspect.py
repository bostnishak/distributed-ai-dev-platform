"""What the IDE shows about a delivered project: its signed proof record and a console for its API.

Console requests run inside the offline Docker sandbox against a fresh copy of the project, in one session, so a
POST followed by a GET sees the stored row and nothing touches the user's files.
"""

from __future__ import annotations

import asyncio
import json
import re
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

import event_log
import ledger
import memory_engine
import preferences
import provenance
import workspace_builder as wb
import workspace_docker
import workspace_smoke
from access_control import require_local_or_admin
from prompt_loader import load_prompt

router = APIRouter(prefix="/api/studio", tags=["studio"])
_LINE_RE = re.compile(r"^\s*(GET|POST|PUT|PATCH|DELETE)\s+(/\S*)\s*(.*)$", re.IGNORECASE)
_MAX_REQUESTS = 10


class ConsoleRequest(BaseModel):
    requests: str = Field(max_length=6000)


def parse_requests(text: str) -> list[dict[str, Any]]:
    """One request per line: METHOD /path [JSON body]. ValueError names the bad line."""
    out: list[dict[str, Any]] = []
    for number, line in enumerate((x for x in text.splitlines() if x.strip()), start=1):
        match = _LINE_RE.match(line)
        if not match:
            raise ValueError(f"{number}. satır 'GET /yol' ya da 'POST /yol {{json}}' biçiminde olmalı")
        body = match.group(3).strip()
        try:
            parsed = json.loads(body) if body else None
        except ValueError as exc:
            raise ValueError(f"{number}. satırdaki JSON geçersiz: {exc}") from exc
        out.append({"method": match.group(1).upper(), "path": match.group(2), "json": parsed})
    if not out or len(out) > _MAX_REQUESTS:
        raise ValueError(f"1 ile {_MAX_REQUESTS} arasında istek yazın")
    return out


def run_console(ws_dir: Path, requests: list[dict[str, Any]]) -> list[dict[str, Any]]:
    entry = workspace_smoke._find_entry(ws_dir)
    if entry is None:
        raise ValueError("Projede çalıştırılacak Python giriş dosyası yok")
    if not workspace_docker.available():
        raise ValueError("Docker çalışmıyor; istekler yalnız yalıtılmış kutuda çalıştırılır")
    pkgs = sorted({*workspace_smoke._safe_requirements(ws_dir), "httpx"})
    with tempfile.TemporaryDirectory(prefix="cm6453_api_") as tmp:
        stage = Path(tmp) / "ws"
        workspace_docker._stage(ws_dir, pkgs, stage)
        command = ["python", "-c", load_prompt("api_console.py.txt"), f"/sandbox/{entry.relative_to(ws_dir).as_posix()}", json.dumps(requests)]
        res = workspace_docker.runner.run_workspace_command(stage, workspace_docker._sandbox_command(command), read_only_mount=False, timeout_s=40)
    found = re.search(r"^RESULT=(.*)$", res["stdout"], re.MULTILINE)
    if not found:
        reason = (res["stderr"] or res["stdout"] or "uygulama başlatılamadı").strip().splitlines()[-1]
        raise ValueError(f"Uygulama isteği yanıtlayamadı: {reason[:300]}")
    return json.loads(found.group(1))


def run_load(ws_dir: Path, total: int = 300, workers: int = 10) -> dict[str, Any]:
    """Concurrent GET requests against the project's API inside the offline sandbox; latency percentiles and errors."""
    entry = workspace_smoke._find_entry(ws_dir)
    if entry is None or not workspace_docker.available():
        raise ValueError("Yük testi için bir Python API projesi ve çalışan Docker gerekir")
    pkgs = sorted({*workspace_smoke._safe_requirements(ws_dir), "httpx"})
    with tempfile.TemporaryDirectory(prefix="cm6453_load_") as tmp:
        stage = Path(tmp) / "ws"
        workspace_docker._stage(ws_dir, pkgs, stage)
        command = ["python", "-c", load_prompt("api_load.py.txt"), f"/sandbox/{entry.relative_to(ws_dir).as_posix()}", str(total), str(workers)]
        res = workspace_docker.runner.run_workspace_command(stage, workspace_docker._sandbox_command(command), read_only_mount=False, timeout_s=60)
    found = re.search(r"^RESULT=(.*)$", res["stdout"], re.MULTILINE)
    if not found:
        raise ValueError("Yük testi tamamlanamadı: " + (res["stderr"] or "süre aşımı").strip().splitlines()[-1][:200])
    return json.loads(found.group(1))


def proof(ws_dir: Path) -> dict[str, Any]:
    try:
        record = json.loads((ws_dir / provenance.FILE_NAME).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        record = {}
    check = provenance.verify(ws_dir)
    return {
        "recorded": bool(record), "created": record.get("created", ""), "signed": check["signed"], "changed": check["changed"],
        "warnings": record.get("warnings", []), "files": len(record.get("files", {})),
        "dependencies": [c.get("name", "") for c in record.get("sbom", {}).get("components", [])],
        "events": event_log.read(ws_dir),
        "ledger": ledger.read(ws_dir),
        "timeline": [{"version": v["version"], "label": v.get("label", ""), "at": v.get("created_at", ""), "files": v.get("files_count", 0)} for v in wb.list_snapshots(ws_dir)],
    }


def _workspace(ws_id: str) -> Path:
    try:
        ws_dir = wb.safe_workspace_dir(ws_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if not ws_dir.is_dir():
        raise HTTPException(status_code=404, detail="Çalışma alanı bulunamadı.")
    return ws_dir


@router.get("/memory-view")
async def memory_view(user_id: str = "default"):
    """What the assistant has been told to remember, and the learned facts."""
    facts = [{"category": f.get("category", ""), "value": f.get("fact_value", "")} for f in memory_engine.list_semantic_facts(user_id=user_id)][:60]
    return {"preferences": preferences.load(user_id), "facts": facts}


@router.get("/workspaces/{id}/proof")
async def get_proof(id: str):
    return await asyncio.to_thread(proof, _workspace(id))


@router.post("/workspaces/{id}/api-console", dependencies=[Depends(require_local_or_admin)])
async def api_console(id: str, body: ConsoleRequest):
    ws_dir = _workspace(id)
    try:
        requests = parse_requests(body.requests)
        return {"responses": await asyncio.to_thread(run_console, ws_dir, requests)}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except (OSError, subprocess.SubprocessError) as exc:
        raise HTTPException(status_code=502, detail=f"Kum havuzu çalıştırılamadı: {exc}") from exc

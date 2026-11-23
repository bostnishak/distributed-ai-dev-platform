"""REST API for the AI Project Studio / Workspace Builder (VS Code / Antigravity-style IDE + EXE Builder)."""

from __future__ import annotations

import io
import json
import mimetypes
import shutil
import subprocess
import zipfile
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel

import workspace_builder as wb
from access_control import require_local_or_admin

router = APIRouter(prefix="/api/studio", tags=["studio"])


class GenerateRequest(BaseModel):
    prompt: str
    project_type: str = "auto"
    model: str = ""


class IterateRequest(BaseModel):
    instruction: str
    model: str = ""


class SaveFileRequest(BaseModel):
    path: str
    content: str


class BuildExeRequest(BaseModel):
    windowed: bool | None = None


@router.get("/workspaces")
async def list_workspaces():
    return {"workspaces": wb.list_workspaces()}


@router.post("/generate")
async def generate_workspace(body: GenerateRequest):
    if not body.prompt.strip():
        raise HTTPException(status_code=400, detail="Lütfen proje açıklaması (prompt) girin.")

    async def _event_stream():
        try:
            async for evt in wb.stream_generate_project(
                body.prompt.strip(),
                project_type=body.project_type,
                model_override=body.model or None,
            ):
                yield f"data: {json.dumps(evt, ensure_ascii=False)}\n\n"
        except Exception as exc:
            yield f"data: {json.dumps({'type': 'error', 'message': str(exc)}, ensure_ascii=False)}\n\n"

    return StreamingResponse(_event_stream(), media_type="text/event-stream")


@router.post("/workspaces/{id}/iterate")
async def iterate_workspace(id: str, body: IterateRequest):
    if not body.instruction.strip():
        raise HTTPException(status_code=400, detail="Lütfen değişiklik isteği girin.")
    try:
        ws_dir = wb.safe_workspace_dir(id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if not ws_dir.is_dir():
        raise HTTPException(status_code=404, detail="Çalışma alanı bulunamadı.")

    async def _event_stream():
        try:
            async for evt in wb.stream_iterate_project(
                id, body.instruction.strip(), model_override=body.model or None
            ):
                yield f"data: {json.dumps(evt, ensure_ascii=False)}\n\n"
        except Exception as exc:
            yield f"data: {json.dumps({'type': 'error', 'message': str(exc)}, ensure_ascii=False)}\n\n"

    return StreamingResponse(_event_stream(), media_type="text/event-stream")


@router.get("/workspaces/{id}/tree")
async def get_workspace_tree(id: str):
    try:
        ws_dir = wb.safe_workspace_dir(id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if not ws_dir.is_dir():
        raise HTTPException(status_code=404, detail="Çalışma alanı bulunamadı.")
    meta = wb.load_workspace_meta(ws_dir)
    exe_files = list((ws_dir / "dist").glob("*.exe")) if (ws_dir / "dist").is_dir() else []
    meta["has_exe"] = len(exe_files) > 0
    meta["exe_name"] = exe_files[0].name if exe_files else ""
    meta["has_web_preview"] = (ws_dir / "index.html").is_file() or (ws_dir / "public" / "index.html").is_file()
    return {"workspace": meta, "tree": wb.build_file_tree(ws_dir)}


@router.get("/workspaces/{id}/file")
async def read_workspace_file(id: str, path: str = Query(...)):
    try:
        ws_dir = wb.safe_workspace_dir(id)
        target = wb.safe_file_path(ws_dir, path)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if not target.is_file():
        raise HTTPException(status_code=404, detail="Dosya bulunamadı.")
    if target.suffix.lower() in (".exe", ".dll", ".png", ".jpg", ".jpeg", ".gif", ".ico", ".zip", ".pdf"):
        return {
            "path": path,
            "binary": True,
            "size": target.stat().st_size,
            "content": f"[İkili dosya: {target.name} · {target.stat().st_size:,} bayt]",
        }
    return {
        "path": path,
        "binary": False,
        "size": target.stat().st_size,
        "content": target.read_text(encoding="utf-8", errors="replace"),
    }


@router.put("/workspaces/{id}/file")
async def save_workspace_file(id: str, body: SaveFileRequest):
    try:
        ws_dir = wb.safe_workspace_dir(id)
        target = wb.safe_file_path(ws_dir, body.path)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if not ws_dir.is_dir():
        raise HTTPException(status_code=404, detail="Çalışma alanı bulunamadı.")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(body.content, encoding="utf-8")
    meta = wb.load_workspace_meta(ws_dir)
    meta["updated_at"] = datetime.now(UTC).isoformat()
    wb.save_workspace_meta(ws_dir, meta)
    return {"ok": True, "path": body.path, "size": target.stat().st_size}


@router.delete("/workspaces/{id}/file")
async def delete_workspace_file(id: str, path: str = Query(...)):
    try:
        ws_dir = wb.safe_workspace_dir(id)
        target = wb.safe_file_path(ws_dir, path)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if not target.exists():
        raise HTTPException(status_code=404, detail="Dosya bulunamadı.")
    if target.is_dir():
        shutil.rmtree(target)
    else:
        target.unlink()
    return {"ok": True, "path": path}


@router.delete("/workspaces/{id}", dependencies=[Depends(require_local_or_admin)])
async def delete_workspace(id: str):
    try:
        ws_dir = wb.safe_workspace_dir(id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if not ws_dir.is_dir():
        raise HTTPException(status_code=404, detail="Çalışma alanı bulunamadı.")
    shutil.rmtree(ws_dir)
    return {"ok": True, "id": id}


@router.post("/workspaces/{id}/build-exe", dependencies=[Depends(require_local_or_admin)])
async def build_exe(id: str, body: BuildExeRequest | None = None):
    try:
        res = await wb.build_workspace_exe(id, windowed=body.windowed if body else None)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return res


@router.post("/workspaces/{id}/launch-exe", dependencies=[Depends(require_local_or_admin)])
def launch_exe(id: str):
    """Launch the compiled Windows .exe locally so the user can run their generated app with one click."""
    try:
        ws_dir = wb.safe_workspace_dir(id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    dist = ws_dir / "dist"
    exe_files = list(dist.glob("*.exe")) if dist.is_dir() else []
    if not exe_files:
        raise HTTPException(status_code=404, detail="Henüz derlenmiş .exe dosyası yok.")
    exe = exe_files[0]
    subprocess.Popen([str(exe)], cwd=str(dist))
    return {"ok": True, "exe_name": exe.name}


@router.get("/workspaces/{id}/download-exe")
async def download_exe(id: str):
    try:
        ws_dir = wb.safe_workspace_dir(id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    dist = ws_dir / "dist"
    exe_files = list(dist.glob("*.exe")) if dist.is_dir() else []
    if not exe_files:
        raise HTTPException(status_code=404, detail="Henüz derlenmiş .exe dosyası yok.")
    exe = exe_files[0]
    return FileResponse(
        exe,
        media_type="application/octet-stream",
        headers={"Content-Disposition": f'attachment; filename="{exe.name}"'},
    )


@router.get("/workspaces/{id}/download.zip")
async def download_workspace_zip(id: str):
    try:
        ws_dir = wb.safe_workspace_dir(id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if not ws_dir.is_dir():
        raise HTTPException(status_code=404, detail="Çalışma alanı bulunamadı.")

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for rel in wb.list_relative_files(ws_dir):
            zf.write(ws_dir / rel, arcname=f"{id}/{rel}")
    buf.seek(0)
    return StreamingResponse(
        buf,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{id}.zip"'},
    )


@router.get("/workspaces/{id}/preview/{filepath:path}")
async def preview_workspace_file(id: str, filepath: str):
    """Serve static HTML/CSS/JS/assets of a web workspace for live iframe preview."""
    try:
        ws_dir = wb.safe_workspace_dir(id)
        rel = filepath or "index.html"
        target = wb.safe_file_path(ws_dir, rel)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if not target.is_file():
        # Try public/ fallback
        alt = ws_dir / "public" / rel
        if alt.is_file():
            target = alt
        else:
            raise HTTPException(status_code=404, detail="Önizleme dosyası bulunamadı.")
    media, _ = mimetypes.guess_type(str(target))
    return FileResponse(target, media_type=media or "application/octet-stream", headers={"Cache-Control": "no-cache"})


@router.get("/workspaces/{id}/history")
async def get_workspace_history(id: str):
    try:
        ws_dir = wb.safe_workspace_dir(id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if not ws_dir.is_dir():
        raise HTTPException(status_code=404, detail="Çalışma alanı bulunamadı.")
    return {"versions": wb.list_snapshots(ws_dir)}


@router.post("/workspaces/{id}/restore/{version}")
async def restore_workspace_version(id: str, version: str):
    try:
        return wb.restore_snapshot(id, version)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/workspaces/{id}/start-server", dependencies=[Depends(require_local_or_admin)])
def start_workspace_live_server(id: str):
    try:
        return wb.start_workspace_server(id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/workspaces/{id}/diff")
async def get_workspace_file_diff(id: str, path: str = Query(...), base_version: str = Query("v1")):
    """Return a unified line diff between base_version (default v1) and current file content."""
    import difflib

    try:
        ws_dir = wb.safe_workspace_dir(id)
        target = wb.safe_file_path(ws_dir, path)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if not target.is_file():
        raise HTTPException(status_code=404, detail="Dosya bulunamadı.")

    current_lines = target.read_text(encoding="utf-8", errors="replace").splitlines()
    snap_file = ws_dir / ".history" / base_version / path.replace("\\", "/").lstrip("/")
    base_lines = snap_file.read_text(encoding="utf-8", errors="replace").splitlines() if snap_file.is_file() else []

    diff_lines = list(
        difflib.unified_diff(
            base_lines,
            current_lines,
            fromfile=f"{base_version}/{path}",
            tofile=f"guncel/{path}",
            lineterm="",
        )
    )
    return {
        "path": path,
        "base_version": base_version,
        "has_changes": len(diff_lines) > 0,
        "base_content": "\n".join(base_lines),
        "current_content": "\n".join(current_lines),
        "diff": "\n".join(diff_lines) if diff_lines else f"({base_version} sürümü ile güncel dosya arasında fark yok)",
    }


class WorkspaceExecRequest(BaseModel):
    command: str


class WorkspaceGitRequest(BaseModel):
    action: str = "status"
    message: str = "AI Studio commit"
    branch: str = ""


@router.post("/workspaces/{id}/exec", dependencies=[Depends(require_local_or_admin)])
def exec_in_workspace(id: str, body: WorkspaceExecRequest):
    """Run a command inside the workspace directory for the embedded IDE terminal ([M28])."""
    import shlex
    import sys

    try:
        ws_dir = wb.safe_workspace_dir(id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if not ws_dir.is_dir():
        raise HTTPException(status_code=404, detail="Çalışma alanı bulunamadı.")
    cmd_str = (body.command or "").strip()
    if not cmd_str:
        raise HTTPException(status_code=400, detail="Komut boş olamaz.")

    parts = shlex.split(cmd_str, posix=(sys.platform != "win32"))
    if not parts:
        raise HTTPException(status_code=400, detail="Geçersiz komut.")
    if parts[0] in ("python", "python3", "py"):
        parts[0] = sys.executable
    elif parts[0] == "pytest":
        parts = [sys.executable, "-m", "pytest", *parts[1:]]

    try:
        proc = subprocess.run(
            parts,
            cwd=str(ws_dir),
            capture_output=True,
            text=True,
            timeout=12,
            check=False,
        )
        return {
            "ok": proc.returncode == 0,
            "exit_code": proc.returncode,
            "stdout": proc.stdout[-6000:],
            "stderr": proc.stderr[-6000:],
        }
    except FileNotFoundError:
        return {"ok": False, "exit_code": 127, "stdout": "", "stderr": f"Komut bulunamadı: {parts[0]}"}
    except subprocess.TimeoutExpired:
        return {"ok": False, "exit_code": -1, "stdout": "", "stderr": "Komut zaman aşımına uğradı (12 sn)."}


@router.post("/workspaces/{id}/git", dependencies=[Depends(require_local_or_admin)])
async def workspace_git_control(id: str, body: WorkspaceGitRequest):
    """Local Git version control (init, status, commit, log, branch) for a workspace ([M29])."""
    try:
        ws_dir = wb.safe_workspace_dir(id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if not ws_dir.is_dir():
        raise HTTPException(status_code=404, detail="Çalışma alanı bulunamadı.")

    def _git(*args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(["git", *args], cwd=str(ws_dir), capture_output=True, text=True, timeout=8, check=False)

    if not (ws_dir / ".git").is_dir():
        _git("init")
        _git("config", "user.email", "studio@local.ai")
        _git("config", "user.name", "AI Studio")

    act = (body.action or "status").lower()
    if act == "commit":
        _git("add", "-A")
        c = _git("commit", "-m", body.message or "AI Studio snapshot")
        out = (c.stdout + "\n" + c.stderr).strip()
    elif act == "branch" and body.branch:
        c = _git("checkout", "-B", body.branch)
        out = (c.stdout + "\n" + c.stderr).strip()
    else:
        st = _git("status", "-s")
        lg = _git("log", "-n", "8", "--oneline")
        out = f"--- DURUM ---\n{st.stdout.strip() or '(Temiz çalışma alanı)'}\n\n--- SON COMMITLER ---\n{lg.stdout.strip() or '(Henüz commit yok)'}"
    return {"ok": True, "action": act, "output": out}


@router.get("/workspaces/{id}/search")
async def search_workspace_files(id: str, q: str = Query(..., min_length=1)):
    """Instant text/regex search across all files in a workspace ([M29] Ctrl+Shift+F)."""
    try:
        ws_dir = wb.safe_workspace_dir(id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if not ws_dir.is_dir():
        raise HTTPException(status_code=404, detail="Çalışma alanı bulunamadı.")

    needle = q.strip().lower()
    matches = []
    for rel in wb.list_relative_files(ws_dir):
        p = ws_dir / rel
        if p.suffix.lower() in (".exe", ".dll", ".png", ".jpg", ".zip", ".pdf"):
            continue
        try:
            lines = p.read_text(encoding="utf-8", errors="ignore").splitlines()
        except OSError:
            continue
        for idx, ln in enumerate(lines, start=1):
            if needle in ln.lower():
                matches.append({"path": rel, "line": idx, "snippet": ln.strip()[:160]})
                if len(matches) >= 50:
                    return {"query": q, "matches": matches}
    return {"query": q, "matches": matches}


@router.get("/workspaces/{id}/code-graph")
async def get_workspace_code_graph(id: str):
    """Build multi-language AST symbol table and dependency graph for a workspace ([M21])."""
    import code_graph

    try:
        ws_dir = wb.safe_workspace_dir(id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if not ws_dir.is_dir():
        raise HTTPException(status_code=404, detail="Çalışma alanı bulunamadı.")
    return code_graph.build_workspace_code_graph(ws_dir)


@router.get("/workspaces/{id}/security-scan")
async def run_workspace_security_and_smoke(id: str):
    """Run SAST security vulnerability scan and Python/JS/JSON smoke verification ([M24]/[M25])."""
    import self_healing_runner

    try:
        ws_dir = wb.safe_workspace_dir(id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if not ws_dir.is_dir():
        raise HTTPException(status_code=404, detail="Çalışma alanı bulunamadı.")
    return self_healing_runner.run_workspace_smoke_check(ws_dir)


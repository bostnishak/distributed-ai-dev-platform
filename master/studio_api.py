"""REST API for the AI Project Studio / Workspace Builder (VS Code / Antigravity-style IDE + EXE Builder)."""

from __future__ import annotations

import io
import json
import mimetypes
import re
import shutil
import zipfile
from datetime import UTC, datetime
from typing import Literal

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel, Field

import preview_server
import process_utils
import sandbox
import workspace_builder as wb
from access_control import require_local_or_admin
from audit_log import AuditTrail

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
        except (httpx.HTTPError, OSError, RuntimeError, ValueError, TypeError, KeyError, AttributeError, ImportError) as exc:
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
        except (httpx.HTTPError, OSError, RuntimeError, ValueError, TypeError, KeyError, AttributeError, ImportError) as exc:
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
    meta["has_web_preview"] = wb.has_web_preview(ws_dir)
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
    AuditTrail().append_event(actor="admin", action="WORKSPACE_DELETED", payload={"workspace_id": id})
    return {"ok": True, "id": id}


@router.post("/workspaces/{id}/build-exe", dependencies=[Depends(require_local_or_admin)])
async def build_exe(id: str, body: BuildExeRequest | None = None):
    try:
        res = await wb.build_workspace_exe(id, windowed=body.windowed if body else None)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    AuditTrail().append_event(actor="admin", action="WORKSPACE_BUILD_EXE", payload={"workspace_id": id, "ok": bool(res.get("ok"))})
    return res


@router.post("/workspaces/{id}/launch-exe", dependencies=[Depends(require_local_or_admin)])
def launch_exe(id: str):
    """SEC-13/SEC-14: Refuse direct unsandboxed host .exe execution; direct users to safe download."""
    try:
        ws_dir = wb.safe_workspace_dir(id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    dist = ws_dir / "dist"
    exe_files = list(dist.glob("*.exe")) if dist.is_dir() else []
    if not exe_files:
        raise HTTPException(status_code=404, detail="Henüz derlenmiş .exe dosyası yok.")
    AuditTrail().append_event(
        actor="admin",
        action="WORKSPACE_LAUNCH_EXE_BLOCKED",
        payload={"workspace_id": id, "exe_name": exe_files[0].name},
    )
    raise HTTPException(
        status_code=403,
        detail=(
            "Güvenlik politikası gereği (SEC-13) üretilen .exe dosyaları sunucu ana makinesinde "
            "doğrudan çalıştırılmaz. Lütfen /download-exe bağlantısından indirip kendi ortamınızda çalıştırın."
        ),
    )


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
        for rel_dir in wb.list_relative_dirs(ws_dir):
            zf.writestr(zipfile.ZipInfo(f"{id}/{rel_dir}/"), b"")
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
        found = None
        for sub in ("public", "frontend"):
            try:
                alt = wb.safe_file_path(ws_dir, f"{sub}/{rel}")
            except ValueError:
                continue
            if alt.is_file():
                found = alt
                break
        if found is None:
            raise HTTPException(status_code=404, detail="Önizleme dosyası bulunamadı.")
        target = found
    media, _ = mimetypes.guess_type(str(target))
    return FileResponse(
        target,
        media_type=media or "application/octet-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Content-Type-Options": "nosniff",
            "Content-Security-Policy": (
                "sandbox allow-scripts allow-forms allow-modals; "
                "default-src 'self' 'unsafe-inline' data: blob:; "
                "connect-src 'none'; frame-ancestors 'self'"
            ),
        },
    )


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
    """SEC-13/SEC-17: Serve workspace preview strictly via the isolated second-origin preview server."""
    try:
        ws_dir = wb.safe_workspace_dir(id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if not ws_dir.is_dir():
        raise HTTPException(status_code=404, detail="Çalışma alanı bulunamadı.")
    preview_server.start_preview_server_background()
    origin = preview_server.get_preview_origin()
    url = f"{origin}/preview/{id}/index.html"
    AuditTrail().append_event(actor="admin", action="WORKSPACE_PREVIEW_STARTED", payload={"workspace_id": id, "url": url})
    return {"ok": True, "url": url, "isolated_origin": origin}


@router.get("/workspaces/{id}/diff")
async def get_workspace_file_diff(id: str, path: str = Query(...), base_version: str = Query("v1")):
    """Return a unified line diff between base_version (default v1) and current file content."""
    import difflib

    if not re.fullmatch(r"v\d+", base_version):
        raise HTTPException(status_code=400, detail="Geçersiz sürüm adı.")
    try:
        ws_dir = wb.safe_workspace_dir(id)
        target = wb.safe_file_path(ws_dir, path)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if not target.is_file():
        raise HTTPException(status_code=404, detail="Dosya bulunamadı.")

    current_lines = target.read_text(encoding="utf-8", errors="replace").splitlines()
    safe_rel = target.relative_to(ws_dir.resolve()).as_posix()
    snap_file = ws_dir / ".history" / base_version / safe_rel
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
    command: str = Field(min_length=1, max_length=500)


class WorkspaceActionRequest(BaseModel):
    action: Literal["run_tests", "install_dependencies", "start_preview", "build_exe"]
    target: str = Field(default=".", max_length=120)
    windowed: bool | None = None


class WorkspaceGitRequest(BaseModel):
    action: Literal["status", "commit", "branch"] = "status"
    message: str = Field(default="AI Studio commit", max_length=200)
    branch: str = Field(default="", max_length=80)


@router.post("/workspaces/{id}/actions", dependencies=[Depends(require_local_or_admin)])
async def run_workspace_action(id: str, body: WorkspaceActionRequest):
    """SEC-14: Action-based workspace execution (typed allowlisted actions; zero host raw-shell)."""
    try:
        ws_dir = wb.safe_workspace_dir(id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if not ws_dir.is_dir():
        raise HTTPException(status_code=404, detail="Çalışma alanı bulunamadı.")

    AuditTrail().append_event(
        actor="admin",
        action=f"WORKSPACE_ACTION_{body.action.upper()}",
        payload={"workspace_id": id, "target": body.target},
    )

    if body.action == "start_preview":
        preview_server.start_preview_server_background()
        origin = preview_server.get_preview_origin()
        return {"ok": True, "action": body.action, "url": f"{origin}/preview/{id}/index.html", "isolated_origin": origin}

    if body.action == "build_exe":
        return await wb.build_workspace_exe(id, windowed=body.windowed)

    if body.action == "run_tests":
        safe_target = body.target if re.fullmatch(r"[A-Za-z0-9_./\-]+", body.target or ".") else "."
        res = sandbox.run_workspace_command(ws_dir, ["python", "-m", "pytest", "--tb=short", "-q", safe_target])
        if not res.get("docker_available"):
            raise HTTPException(status_code=503, detail=res.get("stderr") or "Docker sandbox erişilemiyor.")
        return res

    if body.action == "install_dependencies":
        res = sandbox.run_workspace_command(
            ws_dir,
            ["python", "-m", "pip", "check"],
            read_only_mount=True,
        )
        if not res.get("docker_available"):
            raise HTTPException(status_code=503, detail=res.get("stderr") or "Docker sandbox erişilemiyor.")
        return res

    raise HTTPException(status_code=400, detail="Desteklenmeyen eylem.")


@router.post("/workspaces/{id}/exec", dependencies=[Depends(require_local_or_admin)])
def exec_in_workspace(id: str, body: WorkspaceExecRequest):
    """SEC-13/SEC-14: Run terminal commands strictly inside the hardened Docker sandbox (never on host)."""
    import shlex

    try:
        ws_dir = wb.safe_workspace_dir(id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if not ws_dir.is_dir():
        raise HTTPException(status_code=404, detail="Çalışma alanı bulunamadı.")
    cmd_str = (body.command or "").strip()
    if not cmd_str:
        raise HTTPException(status_code=400, detail="Komut boş olamaz.")

    parts = shlex.split(cmd_str, posix=True)
    if not parts:
        raise HTTPException(status_code=400, detail="Geçersiz komut.")

    AuditTrail().append_event(
        actor="admin",
        action="WORKSPACE_SANDBOX_EXEC",
        payload={"workspace_id": id, "argv_head": parts[0]},
    )

    res = sandbox.run_workspace_command(ws_dir, parts, read_only_mount=True)
    if not res.get("docker_available"):
        raise HTTPException(
            status_code=503,
            detail=res.get("stderr") or "Docker sandbox aktif değil; ana makinede serbest komut yürütme kapalı.",
        )
    return res


@router.post("/workspaces/{id}/git", dependencies=[Depends(require_local_or_admin)])
async def workspace_git_control(id: str, body: WorkspaceGitRequest):
    """Local Git version control (init, status, commit, log, branch) for a workspace ([M29])."""
    try:
        ws_dir = wb.safe_workspace_dir(id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if not ws_dir.is_dir():
        raise HTTPException(status_code=404, detail="Çalışma alanı bulunamadı.")

    git_bin = shutil.which("git")
    if not git_bin:
        raise HTTPException(status_code=503, detail="Git kurulu değil.")

    def _git(*args: str) -> process_utils.ProcessResult:
        return process_utils.run_process([git_bin, *args], cwd=ws_dir, timeout_s=8.0)

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


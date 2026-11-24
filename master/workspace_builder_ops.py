"""Filesystem, snapshot, ZIP import, EXE build, and live server ops for `workspace_builder.py`."""

from __future__ import annotations

import ast
import asyncio
import io
import json
import logging
import os
import re
import shutil
import socket
import subprocess
import sys
import zipfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import config
from process_utils import run_process, spawn_process

SKIP_DIRS = {"__pycache__", ".git", "node_modules", ".venv", "venv", "build", ".history"}
META_FILENAME = ".workspace.json"
_RUNNING_SERVERS: dict[str, tuple[int, subprocess.Popen]] = {}
log = logging.getLogger(__name__)


def workspaces_root() -> Path:
    root = config.WORKSPACES_DIR
    root.mkdir(parents=True, exist_ok=True)
    return root


def slugify(name: str) -> str:
    tr_map = str.maketrans("çğıöşüÇĞİÖŞÜ", "cgiosuCGIOSU")
    clean = name.translate(tr_map).lower()
    slug = re.sub(r"[^a-z0-9]+", "-", clean).strip("-")
    return slug[:48] or "proje"


def safe_workspace_dir(ws_id: str) -> Path:
    clean = "".join(c for c in ws_id if c.isalnum() or c in ("-", "_"))
    if not clean or clean != ws_id:
        raise ValueError("Geçersiz çalışma alanı kimliği.")
    return workspaces_root() / clean


def safe_file_path(ws_dir: Path, rel_path: str) -> Path:
    """Resolve rel_path strictly inside ws_dir; raise ValueError on path traversal."""
    cleaned = rel_path.replace("\\", "/").lstrip("/")
    if not cleaned or ".." in cleaned.split("/"):
        raise ValueError(f"Geçersiz dosya yolu: {rel_path}")
    target = (ws_dir / cleaned).resolve()
    root_res = ws_dir.resolve()
    if root_res not in target.parents and target != root_res:
        raise ValueError(f"Dosya yolu çalışma alanı dışına çıkamaz: {rel_path}")
    return target


def load_workspace_meta(ws_dir: Path) -> dict[str, Any]:
    meta_file = ws_dir / META_FILENAME
    if meta_file.is_file():
        return json.loads(meta_file.read_text(encoding="utf-8"))
    return {
        "id": ws_dir.name,
        "name": ws_dir.name,
        "project_type": "web",
        "description": "",
        "entry_point": "",
        "created_at": datetime.now(UTC).isoformat(),
    }


def save_workspace_meta(ws_dir: Path, meta: dict[str, Any]) -> None:
    ws_dir.mkdir(parents=True, exist_ok=True)
    (ws_dir / META_FILENAME).write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")


def list_workspaces() -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for p in workspaces_root().iterdir():
        if not p.is_dir():
            continue
        meta = load_workspace_meta(p)
        file_count = sum(
            1 for f in p.rglob("*")
            if f.is_file() and f.name != META_FILENAME and not any(part in SKIP_DIRS for part in f.parts)
        )
        exe_files = list((p / "dist").glob("*.exe")) if (p / "dist").is_dir() else []
        meta["file_count"] = file_count
        meta["has_exe"] = len(exe_files) > 0
        meta["exe_name"] = exe_files[0].name if exe_files else ""
        meta["has_web_preview"] = (p / "index.html").is_file() or (p / "public" / "index.html").is_file()
        items.append(meta)
    items.sort(key=lambda x: x.get("updated_at") or x.get("created_at") or "", reverse=True)
    return items


def build_file_tree(ws_dir: Path) -> list[dict[str, Any]]:
    """Return a nested VS Code-style Explorer tree of folders and files."""
    def _walk(cur: Path, rel_prefix: str = "") -> list[dict[str, Any]]:
        nodes: list[dict[str, Any]] = []
        try:
            entries = sorted(cur.iterdir(), key=lambda e: (not e.is_dir(), e.name.lower()))
        except OSError:
            return nodes
        for entry in entries:
            if entry.name == META_FILENAME or entry.name.endswith(".spec"):
                continue
            if entry.is_dir() and entry.name in SKIP_DIRS:
                continue
            rel = f"{rel_prefix}/{entry.name}" if rel_prefix else entry.name
            if entry.is_dir():
                nodes.append({"name": entry.name, "path": rel, "type": "dir", "children": _walk(entry, rel)})
            else:
                nodes.append({
                    "name": entry.name,
                    "path": rel,
                    "type": "file",
                    "size": entry.stat().st_size,
                    "ext": entry.suffix.lower(),
                })
        return nodes

    return _walk(ws_dir)


def list_relative_files(ws_dir: Path) -> list[str]:
    result = []
    for f in sorted(ws_dir.rglob("*")):
        if not f.is_file() or f.name == META_FILENAME:
            continue
        if any(part in SKIP_DIRS for part in f.relative_to(ws_dir).parts):
            continue
        result.append(f.relative_to(ws_dir).as_posix())
    return result


def verify_workspace_files(ws_dir: Path) -> list[str]:
    """Run lightweight syntax verification on Python and JSON files."""
    warnings: list[str] = []
    for rel in list_relative_files(ws_dir):
        p = ws_dir / rel
        if p.suffix == ".py":
            try:
                ast.parse(p.read_text(encoding="utf-8", errors="replace"), filename=rel)
            except SyntaxError as exc:
                warnings.append(f"Python sözdizimi uyarısı ({rel}:{exc.lineno}): {exc.msg}")
        elif p.suffix == ".json":
            try:
                json.loads(p.read_text(encoding="utf-8", errors="replace"))
            except json.JSONDecodeError as exc:
                warnings.append(f"JSON uyarısı ({rel}): {exc.msg}")
    return warnings


def _find_python_entry(ws_dir: Path, meta: dict[str, Any]) -> Path | None:
    ep = meta.get("entry_point", "")
    if ep and ep.endswith(".py") and (ws_dir / ep).is_file():
        return ws_dir / ep
    for cand in ("main.py", "app.py", "game.py", "run.py"):
        if (ws_dir / cand).is_file():
            return ws_dir / cand
    py_files = sorted(ws_dir.glob("*.py"))
    return py_files[0] if py_files else None


def _detect_gui_windowed(ws_dir: Path) -> bool:
    all_py = "\n".join(
        p.read_text(encoding="utf-8", errors="ignore")
        for p in ws_dir.rglob("*.py")
        if not any(part in SKIP_DIRS for part in p.parts)
    )
    return any(lib in all_py for lib in ("tkinter", "pygame", "PyQt", "PySide", "customtkinter"))


def _ensure_subpackage_inits(ws_dir: Path) -> None:
    for sub_py in ws_dir.rglob("*.py"):
        if any(part in SKIP_DIRS for part in sub_py.parts) or sub_py.parent == ws_dir:
            continue
        init_file = sub_py.parent / "__init__.py"
        if not init_file.exists():
            init_file.write_text("", encoding="utf-8")


def _build_exe_blocking(ws_dir: Path, meta: dict[str, Any], windowed: bool | None = None) -> dict[str, Any]:
    entry = _find_python_entry(ws_dir, meta)
    if entry is None:
        return {"ok": False, "error": "Bu çalışma alanında derlenecek Python giriş dosyası (main.py) bulunamadı.", "logs": ""}

    use_windowed = _detect_gui_windowed(ws_dir) if windowed is None else windowed
    _ensure_subpackage_inits(ws_dir)
    app_name = re.sub(r"[^A-Za-z0-9_-]+", "", meta.get("name", "").title().replace(" ", "")) or "StudioApp"
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm", "--onefile", "--clean",
        "--name", app_name,
        "--paths", str(ws_dir),
        "--distpath", str(ws_dir / "dist"),
        "--workpath", str(ws_dir / "build"),
        "--specpath", str(ws_dir / "build"),
    ]
    if use_windowed:
        cmd.append("--windowed")
    cmd.append(str(entry))

    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    try:
        proc = run_process(cmd, cwd=ws_dir, timeout_s=180.0, max_output_chars=12_000, env=env)
    except FileNotFoundError:
        return {"ok": False, "error": "PyInstaller yüklü değil.", "logs": ""}
    if proc.timed_out:
        return {"ok": False, "error": "EXE derlemesi 180 saniye zaman aşımına uğradı.", "logs": ""}

    logs = (proc.stdout + "\n" + proc.stderr)[-6000:]
    exe_ext = ".exe" if sys.platform == "win32" else ""
    exe_path = ws_dir / "dist" / f"{app_name}{exe_ext}"
    build_dir = ws_dir / "build"
    if build_dir.is_dir():
        shutil.rmtree(build_dir, ignore_errors=True)
    if proc.returncode != 0 or not exe_path.is_file():
        return {"ok": False, "error": "PyInstaller derlemesi başarısız oldu.", "logs": logs}

    meta["exe_name"] = exe_path.name
    meta["exe_size"] = exe_path.stat().st_size
    meta["updated_at"] = datetime.now(UTC).isoformat()
    save_workspace_meta(ws_dir, meta)
    return {"ok": True, "exe_name": exe_path.name, "exe_size": exe_path.stat().st_size, "logs": logs}


async def build_workspace_exe(ws_id: str, windowed: bool | None = None) -> dict[str, Any]:
    ws_dir = safe_workspace_dir(ws_id)
    if not ws_dir.is_dir():
        raise FileNotFoundError("Çalışma alanı bulunamadı.")
    meta = load_workspace_meta(ws_dir)
    return await asyncio.to_thread(_build_exe_blocking, ws_dir, meta, windowed)


def create_snapshot(ws_dir: Path, label: str = "") -> dict[str, Any]:
    """Save a lightweight version snapshot of all text files in <ws_dir>/.history/v<N>/."""
    hist_root = ws_dir / ".history"
    hist_root.mkdir(parents=True, exist_ok=True)
    existing = sorted(
        [d for d in hist_root.iterdir() if d.is_dir() and re.fullmatch(r"v\d+", d.name)],
        key=lambda d: int(d.name[1:]),
    )
    next_num = (int(existing[-1].name[1:]) + 1) if existing else 1
    ver = f"v{next_num}"
    snap_dir = hist_root / ver
    snap_dir.mkdir(parents=True, exist_ok=True)

    files_saved = 0
    for rel in list_relative_files(ws_dir):
        if rel.startswith("dist/"):
            continue
        dst = snap_dir / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ws_dir / rel, dst)
        files_saved += 1

    info = {
        "version": ver,
        "label": label or f"Sürüm {ver}",
        "files_count": files_saved,
        "created_at": datetime.now(UTC).isoformat(),
    }
    (snap_dir / ".snapshot.json").write_text(json.dumps(info, ensure_ascii=False, indent=2), encoding="utf-8")
    return info


def list_snapshots(ws_dir: Path) -> list[dict[str, Any]]:
    hist_root = ws_dir / ".history"
    if not hist_root.is_dir():
        return []
    out: list[dict[str, Any]] = []
    for d in sorted(
        [p for p in hist_root.iterdir() if p.is_dir() and re.fullmatch(r"v\d+", p.name)],
        key=lambda p: int(p.name[1:]),
        reverse=True,
    ):
        meta_f = d / ".snapshot.json"
        if meta_f.is_file():
            try:
                out.append(json.loads(meta_f.read_text(encoding="utf-8")))
            except (OSError, ValueError, TypeError) as exc:
                log.debug("Recoverable error skipped in loop: %s", exc)
                continue
    return out


def restore_snapshot(ws_id: str, version: str) -> dict[str, Any]:
    """Restore workspace files back to a given snapshot version (e.g. 'v1')."""
    ws_dir = safe_workspace_dir(ws_id)
    if not re.fullmatch(r"v\d+", version):
        raise ValueError("Geçersiz sürüm adı.")
    snap_dir = ws_dir / ".history" / version
    if not snap_dir.is_dir():
        raise FileNotFoundError(f"Sürüm bulunamadı: {version}")

    for rel in list_relative_files(ws_dir):
        if rel.startswith("dist/"):
            continue
        target = ws_dir / rel
        if target.is_file():
            target.unlink()

    for f in snap_dir.rglob("*"):
        if not f.is_file() or f.name == ".snapshot.json":
            continue
        dst = ws_dir / f.relative_to(snap_dir)
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(f, dst)

    meta = load_workspace_meta(ws_dir)
    meta["active_version"] = version
    meta["versions"] = list_snapshots(ws_dir)
    meta["updated_at"] = datetime.now(UTC).isoformat()
    save_workspace_meta(ws_dir, meta)
    return {"workspace": meta, "tree": build_file_tree(ws_dir)}


def import_zip_workspace(filename: str, raw_bytes: bytes) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Extract an uploaded .zip project into a real workspace directory on disk."""
    stem = Path(filename).stem or "yuklenen-proje"
    ws_id = f"{slugify(stem)}-{datetime.now(UTC).strftime('%m%d%H%M%S')}"
    ws_dir = safe_workspace_dir(ws_id)
    ws_dir.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(io.BytesIO(raw_bytes)) as zf:
        names = [i.filename for i in zf.infolist() if not i.is_dir()]
        top_dirs = {n.split("/")[0] for n in names if "/" in n}
        strip_prefix = f"{next(iter(top_dirs))}/" if (len(top_dirs) == 1 and all(n.startswith(f"{next(iter(top_dirs))}/") for n in names)) else ""

        for info in zf.infolist():
            if info.is_dir():
                continue
            rel = info.filename[len(strip_prefix):] if (strip_prefix and info.filename.startswith(strip_prefix)) else info.filename
            if not rel or any(part in SKIP_DIRS for part in Path(rel).parts):
                continue
            try:
                target = safe_file_path(ws_dir, rel)
            except ValueError:
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(zf.read(info.filename))

    rel_files = list_relative_files(ws_dir)
    has_html = "index.html" in rel_files or "public/index.html" in rel_files
    has_py = any(f.endswith(".py") for f in rel_files)
    ptype = "web" if has_html else ("desktop" if has_py else "fullstack")
    entry = "index.html" if "index.html" in rel_files else ("main.py" if "main.py" in rel_files else (rel_files[0] if rel_files else ""))

    create_snapshot(ws_dir, "ZIP içe aktarma")
    meta: dict[str, Any] = {
        "id": ws_id,
        "name": stem,
        "project_type": ptype,
        "description": f"{filename} arşivinden içe aktarıldı ({len(rel_files)} dosya).",
        "entry_point": entry,
        "has_web_preview": has_html,
        "has_exe": any(f.endswith(".exe") for f in rel_files),
        "versions": list_snapshots(ws_dir),
        "created_at": datetime.now(UTC).isoformat(),
        "updated_at": datetime.now(UTC).isoformat(),
    }
    save_workspace_meta(ws_dir, meta)
    return meta, build_file_tree(ws_dir)


def _find_free_port(start: int = 8110, end: int = 8190) -> int:
    for port in range(start, end):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            if s.connect_ex(("127.0.0.1", port)) != 0:
                return port
    return 8189


def start_workspace_server(ws_id: str) -> dict[str, Any]:
    """Start a live local HTTP server for a workspace (FastAPI, Flask, or static HTTP server)."""
    ws_dir = safe_workspace_dir(ws_id)
    if not ws_dir.is_dir():
        raise FileNotFoundError("Çalışma alanı bulunamadı.")

    if ws_id in _RUNNING_SERVERS:
        port, proc = _RUNNING_SERVERS[ws_id]
        if proc.poll() is None:
            return {"ok": True, "port": port, "url": f"http://127.0.0.1:{port}"}

    port = _find_free_port()
    meta = load_workspace_meta(ws_dir)
    entry = _find_python_entry(ws_dir, meta)

    cmd = [sys.executable, "-m", "http.server", str(port), "--bind", "127.0.0.1"]
    if entry is not None:
        code = entry.read_text(encoding="utf-8", errors="ignore")
        if "FastAPI" in code:
            cmd = [sys.executable, "-m", "uvicorn", f"{entry.stem}:app", "--host", "127.0.0.1", "--port", str(port)]
        elif "Flask" in code:
            cmd = [sys.executable, "-m", "flask", "--app", entry.stem, "run", "--host", "127.0.0.1", "--port", str(port)]

    proc = spawn_process(cmd, cwd=ws_dir)
    _RUNNING_SERVERS[ws_id] = (port, proc)
    return {"ok": True, "port": port, "url": f"http://127.0.0.1:{port}"}

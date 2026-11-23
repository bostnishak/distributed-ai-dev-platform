"""AI Project Studio / Workspace Builder (Antigravity / VS Code-like project generator + EXE builder).

Generates complete multi-file software projects (websites, e-commerce stores, Python games,
desktop apps, full-stack apps) directly into real workspace directories on disk, with:
- 2-stage AI architecture planning + file-by-file code generation via local Ollama
- Iterative AI editing on existing workspaces
- Tree explorer, file read/write/delete, ZIP export
- Live static preview for web/e-commerce workspaces
- Real Windows .exe compilation via PyInstaller for Python games & desktop apps
"""

from __future__ import annotations

import ast
import asyncio
import io
import json
import os
import re
import shutil
import socket
import subprocess
import sys
import zipfile
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx

import config

SKIP_DIRS = {"__pycache__", ".git", "node_modules", ".venv", "venv", "build", ".history"}
META_FILENAME = ".workspace.json"
_RUNNING_SERVERS: dict[str, tuple[int, subprocess.Popen]] = {}


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
                children = _walk(entry, rel)
                nodes.append({"name": entry.name, "path": rel, "type": "dir", "children": children})
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


async def pick_coder_model(preferred: str | None = None) -> str:
    candidates = [
        preferred,
        config.STUDIO_CODER_MODEL,
        "qwen2.5-coder:7b",
        "qwen3.5:9b",
        "qwen3.5:4b",
        config.MASTER_MODEL,
    ]
    candidates = [c for c in candidates if c]
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{config.OLLAMA_URL}/api/tags")
            resp.raise_for_status()
            installed = {m.get("name", "") for m in resp.json().get("models", [])}
            for cand in candidates:
                if cand in installed:
                    return cand
    except Exception:
        pass
    return config.MASTER_MODEL


async def _ollama_generate(model: str, system: str, user: str, num_predict: int = 4096, temperature: float = 0.25) -> str:
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "stream": False,
        "think": False,
        "options": {"num_predict": num_predict, "temperature": temperature},
    }
    async with httpx.AsyncClient(timeout=240.0) as client:
        resp = await client.post(f"{config.OLLAMA_URL}/api/chat", json=payload)
        resp.raise_for_status()
        return resp.json().get("message", {}).get("content", "")


def _strip_code_fences(raw: str) -> str:
    text = raw.strip()
    m = re.match(r"^```[a-zA-Z0-9_+-]*\s*\n([\s\S]*?)\n```\s*$", text)
    if m:
        return m.group(1)
    # If there's a fenced block inside surrounding prose, extract the largest one
    blocks = re.findall(r"```[a-zA-Z0-9_+-]*\s*\n([\s\S]*?)\n```", text)
    if blocks:
        return max(blocks, key=len)
    return text


def _extract_json_obj(raw: str) -> dict[str, Any] | None:
    m = re.search(r"\{[\s\S]*\}", raw)
    if not m:
        return None
    try:
        return json.loads(m.group(0))
    except json.JSONDecodeError:
        return None


ARCHITECT_SYSTEM_PROMPT = (
    "Sen kıdemli bir yazılım mimarısın. Kullanıcının isteğine göre eksiksiz, gerçek, çok klasörlü ve "
    "üretim kalitesinde bir proje dosya ağacı ve mimari planı çıkar.\n"
    "SADECE geçerli bir JSON objesi döndür, başka hiçbir metin ekleme:\n"
    "{\n"
    '  "name": "Proje Adı",\n'
    '  "project_type": "web" | "game" | "desktop" | "fullstack" | "cli",\n'
    '  "description": "Kısa özet",\n'
    '  "entry_point": "index.html veya main.py",\n'
    '  "files": [\n'
    '    {"path": "index.html", "purpose": "Ana sayfa yapısı"},\n'
    '    {"path": "css/styles.css", "purpose": "Modern responsive tasarım"},\n'
    '    {"path": "js/app.js", "purpose": "Etkileşimli uygulama mantığı"}\n'
    "  ]\n"
    "}\n"
    "Kurallar:\n"
    "- Web / e-ticaret / kurumsal site projeleri için saf HTML5 + modern CSS3 + modüler vanilla JS kullan (harici derleme aracı gerektirmeden tarayıcıda anında çalışsın, ana dosya 'index.html' olsun; css/, js/, data/ gibi düzenli alt klasörler kullan).\n"
    "- Oyun veya masaüstü (.exe) projeleri için Python standart kütüphanesi (tkinter Canvas) kullan ki PyInstaller ile tek tıkla .exe üretilebilsin; ana dosya 'main.py' olsun, game/ veya app/ alt paketlerine böl.\n"
    "- Full-stack / API projelerinde backend/ (FastAPI), frontend/ (HTML/CSS/JS), tests/, requirements.txt, README.md, .gitignore gibi eksiksiz profesyonel klasör yapısı kur.\n"
    "- İkili resim dosyaları (.png, .jpg, .ico) planlama; logo/ikon gerekiyorsa .svg dosyası veya inline SVG kullan.\n"
    "- Projenin kapsamına göre 5 ile 14 arası temiz, modüler dosya planla (README.md dahil)."
)

FILE_WRITER_SYSTEM_PROMPT = (
    "Sen uzman bir yazılım geliştiricisin. Sana verilen proje mimarisindeki TEK BİR dosyanın "
    "eksiksiz, çalışır, temiz, üretim kalitesinde kodunu yaz.\n"
    "Kurallar:\n"
    "- SADECE dosya içeriğini döndür (açıklama veya ek sohbet yazma).\n"
    "- Yarım bırakma, '// TODO' veya '...' kullanma; tüm fonksiyonları ve stilleri eksiksiz yaz.\n"
    "- Proje içindeki diğer dosya yolları, CSS sınıfları, JS fonksiyon adları ve Python importları ile %100 uyumlu ol.\n"
    "- ASLA emoji kullanma (ne HTML metinlerinde, ne butonlarda, ne de yorumlarda). İkon gerektiğinde temiz inline SVG kullan.\n"
    "- Web / CSS tasarımlarında kurumsal modern SaaS estetiği (Inter/Segoe UI tipografi, #0f172a / #1e293b / #4f46e5 renk paleti, ince kenarlıklar 1px solid rgba(255,255,255,0.08), yumuşak gölgeler, flexbox/grid, sekme geçişleri ve modern form kontrolleri) kullan; asla ilkel 2005 tarzı düz beyaz/gri kutular veya alert() kullanma.\n"
    "- Python masaüstü / oyun (.exe) projelerinde SADECE Python standart kütüphanesini (tkinter, tkinter.ttk, math, json, random, datetime, pathlib) kullan; PyQt5, customtkinter, pygame gibi harici paketleri ASLA import etme."
)


def _verify_workspace_files(ws_dir: Path) -> list[str]:
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


async def stream_generate_project(
    prompt: str,
    project_type: str = "auto",
    model_override: str | None = None,
) -> AsyncIterator[dict[str, Any]]:
    """2-stage SSE generator: Architect plan -> file-by-file generation -> verification."""
    model = await pick_coder_model(model_override)
    yield {"type": "status", "message": f"Mimari plan hazırlanıyor ({model})..."}

    type_hint = ""
    if project_type and project_type != "auto":
        type_hint = f"\nİstenen proje türü: {project_type}."

    arch_raw = await _ollama_generate(
        model=model,
        system=ARCHITECT_SYSTEM_PROMPT,
        user=f"Kullanıcı isteği:\n{prompt}{type_hint}",
        num_predict=2048,
        temperature=0.2,
    )
    plan = _extract_json_obj(arch_raw)
    if not plan or not isinstance(plan.get("files"), list) or not plan["files"]:
        # Sensible fallback plan if model returned non-JSON
        is_game = any(w in prompt.lower() for w in ("oyun", "game", "exe", "masaüstü", "tkinter", "snake", "tetris"))
        if is_game or project_type in ("game", "desktop"):
            plan = {
                "name": "Python Masaüstü Projesi",
                "project_type": "game" if is_game else "desktop",
                "description": prompt[:140],
                "entry_point": "main.py",
                "files": [
                    {"path": "main.py", "purpose": "Uygulama giriş noktası"},
                    {"path": "app/engine.py", "purpose": "Ana mantık ve arayüz"},
                    {"path": "app/config.py", "purpose": "Sabitler ve tema"},
                    {"path": "README.md", "purpose": "Kurulum ve kullanım"},
                ],
            }
        else:
            plan = {
                "name": "Web Projesi",
                "project_type": "web",
                "description": prompt[:140],
                "entry_point": "index.html",
                "files": [
                    {"path": "index.html", "purpose": "Ana HTML sayfası"},
                    {"path": "css/styles.css", "purpose": "Modern stil dosyası"},
                    {"path": "js/app.js", "purpose": "Etkileşimli JS mantığı"},
                    {"path": "README.md", "purpose": "Proje dokümantasyonu"},
                ],
            }

    ws_name = str(plan.get("name") or "Yeni Proje").strip()
    ws_id = f"{slugify(ws_name)}-{datetime.now(UTC).strftime('%m%d%H%M%S')}"
    ws_dir = safe_workspace_dir(ws_id)
    ws_dir.mkdir(parents=True, exist_ok=True)

    binary_exts = (".png", ".jpg", ".jpeg", ".gif", ".ico", ".webp", ".bmp", ".mp3", ".wav", ".ttf", ".woff", ".woff2")
    planned_files = [
        {"path": str(f["path"]).replace("\\", "/").lstrip("/"), "purpose": str(f.get("purpose", ""))}
        for f in plan["files"][:16]
        if isinstance(f, dict) and f.get("path") and not str(f["path"]).lower().endswith(binary_exts)
    ]

    meta = {
        "id": ws_id,
        "name": ws_name,
        "project_type": str(plan.get("project_type") or "web"),
        "description": str(plan.get("description") or prompt[:180]),
        "entry_point": str(plan.get("entry_point") or planned_files[0]["path"]),
        "model": model,
        "prompt": prompt,
        "created_at": datetime.now(UTC).isoformat(),
        "updated_at": datetime.now(UTC).isoformat(),
    }
    save_workspace_meta(ws_dir, meta)

    yield {"type": "plan", "workspace": meta, "files": planned_files}

    # Stage 2: Write each file with full architecture awareness
    tree_summary = "\n".join(f"- {f['path']}: {f['purpose']}" for f in planned_files)
    written_snippets: list[str] = []

    for idx, fspec in enumerate(planned_files, start=1):
        fpath = fspec["path"]
        yield {"type": "file_start", "path": fpath, "index": idx, "total": len(planned_files)}

        context_tail = "\n\n".join(written_snippets[-3:])
        file_prompt = (
            f"Proje Adı: {ws_name}\n"
            f"Proje Türü: {meta['project_type']}\n"
            f"Kullanıcı İsteği: {prompt}\n\n"
            f"Tüm Dosya Ağacı:\n{tree_summary}\n\n"
            + (f"Önceki dosyaların özeti:\n{context_tail}\n\n" if context_tail else "")
            + f"ŞİMDİ SADECE ŞU DOSYANIN EKSİKSİZ İÇERİĞİNİ YAZ: `{fpath}`\n"
            f"Dosya amacı: {fspec['purpose']}"
        )
        raw_code = await _ollama_generate(
            model=model,
            system=FILE_WRITER_SYSTEM_PROMPT,
            user=file_prompt,
            num_predict=4096,
            temperature=0.2,
        )
        code = _strip_code_fences(raw_code)
        if fpath.endswith(".py"):
            try:
                ast.parse(code, filename=fpath)
            except SyntaxError as exc:
                fix_raw = await _ollama_generate(
                    model=model,
                    system=FILE_WRITER_SYSTEM_PROMPT,
                    user=(
                        f"`{fpath}` dosyasında Python SyntaxError oluştu ({exc.lineno}. satır: {exc.msg}).\n"
                        f"Hatalı kod:\n```python\n{code}\n```\n\n"
                        "Sözdizimi hatasını düzeltip dosyanın eksiksiz, geçerli Python kodunu döndür."
                    ),
                    num_predict=4096,
                    temperature=0.1,
                )
                code = _strip_code_fences(fix_raw)
        target = safe_file_path(ws_dir, fpath)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(code, encoding="utf-8")

        # Keep a compact snippet for sibling consistency
        written_snippets.append(f"=== {fpath} ===\n{code[:1200]}")
        yield {"type": "file_done", "path": fpath, "size": len(code.encode("utf-8")), "index": idx, "total": len(planned_files)}

    warnings = _verify_workspace_files(ws_dir)
    create_snapshot(ws_dir, "İlk oluşturma")
    meta["versions"] = list_snapshots(ws_dir)
    meta["updated_at"] = datetime.now(UTC).isoformat()
    save_workspace_meta(ws_dir, meta)

    yield {
        "type": "done",
        "workspace": meta,
        "tree": build_file_tree(ws_dir),
        "warnings": warnings,
    }


async def stream_iterate_project(
    ws_id: str,
    instruction: str,
    model_override: str | None = None,
) -> AsyncIterator[dict[str, Any]]:
    """Modify or add files in an existing workspace based on a follow-up prompt."""
    ws_dir = safe_workspace_dir(ws_id)
    if not ws_dir.is_dir():
        raise FileNotFoundError("Çalışma alanı bulunamadı.")
    meta = load_workspace_meta(ws_dir)
    model = await pick_coder_model(model_override)
    existing_files = list_relative_files(ws_dir)

    yield {"type": "status", "message": f"Değişiklik planı çıkarılıyor ({model})..."}

    plan_prompt = (
        f"Mevcut proje: {meta.get('name')} ({meta.get('project_type')})\n"
        f"Mevcut dosyalar:\n" + "\n".join(f"- {p}" for p in existing_files) + "\n\n"
        f"Kullanıcının yeni isteği:\n{instruction}\n\n"
        "Hangi dosyaların güncellenmesi veya yeni oluşturulması gerektiğini SADECE JSON olarak yaz:\n"
        '{"files": [{"path": "js/app.js", "purpose": "Yapılacak değişiklik"}]}'
    )
    raw_plan = await _ollama_generate(
        model=model,
        system="Sadece geçerli JSON döndür. En fazla 5 dosya seç.",
        user=plan_prompt,
        num_predict=1024,
        temperature=0.15,
    )
    parsed = _extract_json_obj(raw_plan)
    target_files = (parsed or {}).get("files") or []
    if not target_files and existing_files:
        target_files = [{"path": meta.get("entry_point") or existing_files[0], "purpose": instruction}]

    for idx, fspec in enumerate(target_files[:6], start=1):
        fpath = str(fspec["path"]).replace("\\", "/").lstrip("/")
        yield {"type": "file_start", "path": fpath, "index": idx, "total": len(target_files[:6])}

        target = safe_file_path(ws_dir, fpath)
        current_content = target.read_text(encoding="utf-8", errors="replace") if target.is_file() else ""
        edit_prompt = (
            f"Proje: {meta.get('name')}\n"
            f"Mevcut dosyalar: {', '.join(existing_files)}\n"
            f"Değişiklik isteği: {instruction}\n"
            f"Hedef dosya: `{fpath}` ({fspec.get('purpose', '')})\n\n"
            + (f"Mevcut dosya içeriği:\n```\n{current_content[:6000]}\n```\n\n" if current_content else "")
            + "Bu dosyanın güncel ve EKSİKSİZ tüm içeriğini yaz."
        )
        raw_code = await _ollama_generate(
            model=model,
            system=FILE_WRITER_SYSTEM_PROMPT,
            user=edit_prompt,
            num_predict=4096,
            temperature=0.2,
        )
        code = _strip_code_fences(raw_code)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(code, encoding="utf-8")
        yield {"type": "file_done", "path": fpath, "size": len(code.encode("utf-8")), "index": idx, "total": len(target_files[:6])}

    warnings = _verify_workspace_files(ws_dir)
    create_snapshot(ws_dir, instruction[:60])
    meta["versions"] = list_snapshots(ws_dir)
    meta["updated_at"] = datetime.now(UTC).isoformat()
    save_workspace_meta(ws_dir, meta)
    yield {"type": "done", "workspace": meta, "tree": build_file_tree(ws_dir), "warnings": warnings}


def _find_python_entry(ws_dir: Path, meta: dict[str, Any]) -> Path | None:
    ep = meta.get("entry_point", "")
    if ep and ep.endswith(".py") and (ws_dir / ep).is_file():
        return ws_dir / ep
    for cand in ("main.py", "app.py", "game.py", "run.py"):
        if (ws_dir / cand).is_file():
            return ws_dir / cand
    py_files = sorted(ws_dir.glob("*.py"))
    return py_files[0] if py_files else None


def _build_exe_blocking(ws_dir: Path, meta: dict[str, Any], windowed: bool | None = None) -> dict[str, Any]:
    entry = _find_python_entry(ws_dir, meta)
    if entry is None:
        return {"ok": False, "error": "Bu çalışma alanında derlenecek Python giriş dosyası (main.py) bulunamadı.", "logs": ""}

    # Auto-detect GUI apps (tkinter/pygame/PyQt) so they launch cleanly without console window
    if windowed is None:
        all_py = "\n".join(
            p.read_text(encoding="utf-8", errors="ignore")
            for p in ws_dir.rglob("*.py")
            if not any(part in SKIP_DIRS for part in p.parts)
        )
        windowed = any(lib in all_py for lib in ("tkinter", "pygame", "PyQt", "PySide", "customtkinter"))

    # Ensure every sub-package folder with .py files has an __init__.py so PyInstaller resolves imports
    for sub_py in ws_dir.rglob("*.py"):
        if any(part in SKIP_DIRS for part in sub_py.parts):
            continue
        if sub_py.parent != ws_dir:
            init_file = sub_py.parent / "__init__.py"
            if not init_file.exists():
                init_file.write_text("", encoding="utf-8")

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
    if windowed:
        cmd.append("--windowed")
    cmd.append(str(entry))

    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"

    try:
        proc = subprocess.run(
            cmd,
            cwd=str(ws_dir),
            capture_output=True,
            text=True,
            timeout=180,
            env=env,
            check=False,
        )
    except FileNotFoundError:
        return {"ok": False, "error": "PyInstaller yüklü değil.", "logs": ""}
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": "EXE derlemesi 180 saniye zaman aşımına uğradı.", "logs": ""}

    logs = (proc.stdout + "\n" + proc.stderr)[-6000:]
    exe_ext = ".exe" if sys.platform == "win32" else ""
    exe_path = ws_dir / "dist" / f"{app_name}{exe_ext}"

    # Clean up temporary build/ folder to keep workspace tidy
    build_dir = ws_dir / "build"
    if build_dir.is_dir():
        shutil.rmtree(build_dir, ignore_errors=True)

    if proc.returncode != 0 or not exe_path.is_file():
        return {"ok": False, "error": "PyInstaller derlemesi başarısız oldu.", "logs": logs}

    meta["exe_name"] = exe_path.name
    meta["exe_size"] = exe_path.stat().st_size
    meta["updated_at"] = datetime.now(UTC).isoformat()
    save_workspace_meta(ws_dir, meta)

    return {
        "ok": True,
        "exe_name": exe_path.name,
        "exe_size": exe_path.stat().st_size,
        "logs": logs,
    }


async def build_workspace_exe(ws_id: str, windowed: bool | None = None) -> dict[str, Any]:
    ws_dir = safe_workspace_dir(ws_id)
    if not ws_dir.is_dir():
        raise FileNotFoundError("Çalışma alanı bulunamadı.")
    meta = load_workspace_meta(ws_dir)
    return await asyncio.to_thread(_build_exe_blocking, ws_dir, meta, windowed)


# --- Snapshot / Version History (v1, v2, v3... & 1-Click Rollback) ---

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
        src = ws_dir / rel
        dst = snap_dir / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
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
            except Exception:
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

    # Remove current non-dist, non-skip files
    for rel in list_relative_files(ws_dir):
        if rel.startswith("dist/"):
            continue
        target = ws_dir / rel
        if target.is_file():
            target.unlink()

    # Copy files from snapshot back to workspace root
    for f in snap_dir.rglob("*"):
        if not f.is_file() or f.name == ".snapshot.json":
            continue
        rel = f.relative_to(snap_dir)
        dst = ws_dir / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(f, dst)

    meta = load_workspace_meta(ws_dir)
    meta["active_version"] = version
    meta["versions"] = list_snapshots(ws_dir)
    meta["updated_at"] = datetime.now(UTC).isoformat()
    save_workspace_meta(ws_dir, meta)
    return {"workspace": meta, "tree": build_file_tree(ws_dir)}


# --- Import Existing .ZIP Archive into a Live Workspace ---

def import_zip_workspace(filename: str, raw_bytes: bytes) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Extract an uploaded .zip project into a real workspace directory on disk."""
    stem = Path(filename).stem or "yuklenen-proje"
    ws_id = f"{slugify(stem)}-{datetime.now(UTC).strftime('%m%d%H%M%S')}"
    ws_dir = safe_workspace_dir(ws_id)
    ws_dir.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(io.BytesIO(raw_bytes)) as zf:
        names = [i.filename for i in zf.infolist() if not i.is_dir()]
        # Strip single top-level folder prefix if all files share one
        top_dirs = {n.split("/")[0] for n in names if "/" in n}
        strip_prefix = f"{next(iter(top_dirs))}/" if (len(top_dirs) == 1 and all(n.startswith(f"{next(iter(top_dirs))}/") for n in names)) else ""

        for info in zf.infolist():
            if info.is_dir():
                continue
            rel = info.filename
            if strip_prefix and rel.startswith(strip_prefix):
                rel = rel[len(strip_prefix):]
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
    meta = {
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


# --- Live Background App Runner for Full-Stack / Python Backend Workspaces ---

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

    # Reuse existing running server if still alive
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
            mod_name = entry.stem
            cmd = [sys.executable, "-m", "uvicorn", f"{mod_name}:app", "--host", "127.0.0.1", "--port", str(port)]
        elif "Flask" in code:
            cmd = [sys.executable, "-m", "flask", "--app", entry.stem, "run", "--host", "127.0.0.1", "--port", str(port)]

    proc = subprocess.Popen(
        cmd,
        cwd=str(ws_dir),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    _RUNNING_SERVERS[ws_id] = (port, proc)
    return {"ok": True, "port": port, "url": f"http://127.0.0.1:{port}"}

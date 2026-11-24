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
import json
import logging
import re
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx

import config
from prompt_loader import load_prompt
from workspace_builder_ops import (
    _RUNNING_SERVERS,
    META_FILENAME,
    SKIP_DIRS,
    _build_exe_blocking,
    _find_free_port,
    _find_python_entry,
    build_file_tree,
    build_workspace_exe,
    create_snapshot,
    import_zip_workspace,
    list_relative_files,
    list_snapshots,
    list_workspaces,
    load_workspace_meta,
    restore_snapshot,
    safe_file_path,
    safe_workspace_dir,
    save_workspace_meta,
    slugify,
    start_workspace_server,
    verify_workspace_files,
    workspaces_root,
)

__all__ = [
    "ARCHITECT_SYSTEM_PROMPT",
    "FILE_WRITER_SYSTEM_PROMPT",
    "META_FILENAME",
    "SKIP_DIRS",
    "_RUNNING_SERVERS",
    "_build_exe_blocking",
    "_find_free_port",
    "_find_python_entry",
    "build_file_tree",
    "build_workspace_exe",
    "create_snapshot",
    "import_zip_workspace",
    "list_relative_files",
    "list_snapshots",
    "list_workspaces",
    "load_workspace_meta",
    "pick_coder_model",
    "restore_snapshot",
    "safe_file_path",
    "safe_workspace_dir",
    "save_workspace_meta",
    "slugify",
    "start_workspace_server",
    "stream_generate_project",
    "stream_iterate_project",
    "workspaces_root",
]

ARCHITECT_SYSTEM_PROMPT = load_prompt("b4_ws_architect.txt")

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

_BINARY_EXTS = (".png", ".jpg", ".jpeg", ".gif", ".ico", ".webp", ".bmp", ".mp3", ".wav", ".ttf", ".woff", ".woff2")
_verify_workspace_files = verify_workspace_files


async def pick_coder_model(preferred: str | None = None) -> str:
    candidates = [
        c for c in (preferred, config.STUDIO_CODER_MODEL, "qwen2.5-coder:7b", "qwen3.5:9b", "qwen3.5:4b", config.MASTER_MODEL)
        if c
    ]
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{config.OLLAMA_URL}/api/tags")
            resp.raise_for_status()
            installed = {m.get("name", "") for m in resp.json().get("models", [])}
            for cand in candidates:
                if cand in installed:
                    return cand
    except (httpx.HTTPError, OSError, ValueError, TypeError, KeyError) as exc:
        logging.getLogger(__name__).debug("Recoverable error suppressed: %s", exc)
    return config.MASTER_MODEL


async def _ollama_generate(model: str, system: str, user: str, num_predict: int = 4096, temperature: float = 0.25) -> str:
    import gateway

    prof = "code" if temperature <= 0.3 else "analytic"
    res = await gateway.default_client.chat(
        [{"role": "system", "content": system}, {"role": "user", "content": user}],
        model=model,
        profile=prof,
        num_predict=num_predict,
        timeout_s=240.0,
        feature="workspace_builder",
        max_retries=0,
    )
    return res.content


def _strip_code_fences(raw: str) -> str:
    text = raw.strip()
    m = re.match(r"^```[a-zA-Z0-9_+-]*\s*\n([\s\S]*?)\n```\s*$", text)
    if m:
        return m.group(1)
    blocks = re.findall(r"```[a-zA-Z0-9_+-]*\s*\n([\s\S]*?)\n```", text)
    return str(max(blocks, key=len)) if blocks else text


def _extract_json_obj(raw: str) -> dict[str, Any] | None:
    m = re.search(r"\{[\s\S]*\}", raw)
    if not m:
        return None
    try:
        return json.loads(m.group(0))
    except json.JSONDecodeError:
        return None


def _fallback_architecture_plan(prompt: str, project_type: str) -> dict[str, Any]:
    is_game = any(w in prompt.lower() for w in ("oyun", "game", "exe", "masaüstü", "tkinter", "snake", "tetris"))
    if is_game or project_type in ("game", "desktop"):
        return {
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
    return {
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


def _prepare_workspace_from_plan(plan: dict[str, Any], prompt: str, model: str) -> tuple[Path, dict[str, Any], list[dict[str, str]]]:
    ws_name = str(plan.get("name") or "Yeni Proje").strip()
    ws_id = f"{slugify(ws_name)}-{datetime.now(UTC).strftime('%m%d%H%M%S')}"
    ws_dir = safe_workspace_dir(ws_id)
    ws_dir.mkdir(parents=True, exist_ok=True)
    planned_files = [
        {"path": str(f["path"]).replace("\\", "/").lstrip("/"), "purpose": str(f.get("purpose", ""))}
        for f in plan["files"][:16]
        if isinstance(f, dict) and f.get("path") and not str(f["path"]).lower().endswith(_BINARY_EXTS)
    ]
    meta: dict[str, Any] = {
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
    return ws_dir, meta, planned_files


async def _generate_and_write_file(
    ws_dir: Path,
    model: str,
    fspec: dict[str, str],
    file_prompt: str,
) -> str:
    fpath = fspec["path"]
    raw_code = await _ollama_generate(model=model, system=FILE_WRITER_SYSTEM_PROMPT, user=file_prompt, num_predict=4096, temperature=0.2)
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
    for parent in reversed(target.parents):
        if parent == ws_dir or ws_dir not in parent.parents:
            continue
        if parent.is_file():
            parent.replace(parent.with_name(f"{parent.name}_module.py"))
    if target.is_dir():
        target = target / "__init__.py"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(code, encoding="utf-8")
    return code


async def stream_generate_project(
    prompt: str,
    project_type: str = "auto",
    model_override: str | None = None,
) -> AsyncIterator[dict[str, Any]]:
    """2-stage SSE generator: Architect plan -> file-by-file generation -> verification."""
    model = await pick_coder_model(model_override)
    yield {"type": "status", "message": f"Mimari plan hazırlanıyor ({model})..."}

    type_hint = f"\nİstenen proje türü: {project_type}." if (project_type and project_type != "auto") else ""
    arch_raw = await _ollama_generate(
        model=model,
        system=ARCHITECT_SYSTEM_PROMPT,
        user=f"Kullanıcı isteği:\n{prompt}{type_hint}",
        num_predict=2048,
        temperature=0.2,
    )
    plan = _extract_json_obj(arch_raw)
    if not plan or not isinstance(plan.get("files"), list) or not plan["files"]:
        plan = _fallback_architecture_plan(prompt, project_type)

    ws_dir, meta, planned_files = _prepare_workspace_from_plan(plan, prompt, model)
    yield {"type": "plan", "workspace": meta, "files": planned_files}

    tree_summary = "\n".join(f"- {f['path']}: {f['purpose']}" for f in planned_files)
    written_snippets: list[str] = []

    for idx, fspec in enumerate(planned_files, start=1):
        fpath = fspec["path"]
        yield {"type": "file_start", "path": fpath, "index": idx, "total": len(planned_files)}
        context_tail = "\n\n".join(written_snippets[-3:])
        file_prompt = (
            f"Proje Adı: {meta['name']}\nProje Türü: {meta['project_type']}\nKullanıcı İsteği: {prompt}\n\n"
            f"Tüm Dosya Ağacı:\n{tree_summary}\n\n"
            + (f"Önceki dosyaların özeti:\n{context_tail}\n\n" if context_tail else "")
            + f"ŞİMDİ SADECE ŞU DOSYANIN EKSİKSİZ İÇERİĞİNİ YAZ: `{fpath}`\nDosya amacı: {fspec['purpose']}"
        )
        code = await _generate_and_write_file(ws_dir, model, fspec, file_prompt)
        written_snippets.append(f"=== {fpath} ===\n{code[:1200]}")
        yield {"type": "file_done", "path": fpath, "size": len(code.encode("utf-8")), "index": idx, "total": len(planned_files)}

    warnings = verify_workspace_files(ws_dir)
    create_snapshot(ws_dir, "İlk oluşturma")
    meta["versions"] = list_snapshots(ws_dir)
    meta["updated_at"] = datetime.now(UTC).isoformat()
    save_workspace_meta(ws_dir, meta)
    yield {"type": "done", "workspace": meta, "tree": build_file_tree(ws_dir), "warnings": warnings}


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
            f"Proje: {meta.get('name')}\nMevcut dosyalar: {', '.join(existing_files)}\n"
            f"Değişiklik isteği: {instruction}\nHedef dosya: `{fpath}` ({fspec.get('purpose', '')})\n\n"
            + (f"Mevcut dosya içeriği:\n```\n{current_content[:6000]}\n```\n\n" if current_content else "")
            + "Bu dosyanın güncel ve EKSİKSİZ tüm içeriğini yaz."
        )
        raw_code = await _ollama_generate(model=model, system=FILE_WRITER_SYSTEM_PROMPT, user=edit_prompt, num_predict=4096, temperature=0.2)
        code = _strip_code_fences(raw_code)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(code, encoding="utf-8")
        yield {"type": "file_done", "path": fpath, "size": len(code.encode("utf-8")), "index": idx, "total": len(target_files[:6])}

    warnings = verify_workspace_files(ws_dir)
    create_snapshot(ws_dir, instruction[:60])
    meta["versions"] = list_snapshots(ws_dir)
    meta["updated_at"] = datetime.now(UTC).isoformat()
    save_workspace_meta(ws_dir, meta)
    yield {"type": "done", "workspace": meta, "tree": build_file_tree(ws_dir), "warnings": warnings}

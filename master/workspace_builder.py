"""AI Project Studio / Workspace Builder (Antigravity / VS Code-like project generator + EXE builder).

Generates complete multi-file software projects (websites, e-commerce stores, Python games,
desktop apps, full-stack apps) directly into real workspace directories on disk, with:
- 2-stage AI architecture planning + file-by-file code generation via local Ollama
- Explicit prompt folder/file path enforcement & cross-file contract manifest
- Iterative AI editing on existing workspaces with syntax verification
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
    has_web_preview,
    import_zip_workspace,
    list_relative_dirs,
    list_relative_files,
    list_snapshots,
    list_workspaces,
    load_workspace_meta,
    make_workspace_id,
    restore_snapshot,
    safe_file_path,
    safe_workspace_dir,
    save_workspace_meta,
    slugify,
    start_workspace_server,
    verify_workspace_files,
    workspaces_root,
)
from workspace_kit import KIT_CLASSES
from workspace_requirements import repair_project
from workspace_smoke import smoke_and_repair

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
    "has_web_preview",
    "import_zip_workspace",
    "list_relative_dirs",
    "list_relative_files",
    "list_snapshots",
    "list_workspaces",
    "load_workspace_meta",
    "make_workspace_id",
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

FILE_WRITER_SYSTEM_PROMPT = load_prompt("b4_ws_writer.txt").replace("{kit_classes}", KIT_CLASSES)

_BINARY_EXTS = (".png", ".jpg", ".jpeg", ".gif", ".ico", ".webp", ".bmp", ".mp3", ".wav", ".ttf", ".woff", ".woff2")
_FILE_PATH_RE = re.compile(
    r"(?<![A-Za-z0-9_./:-])([A-Za-z0-9_.-]+(?:/[A-Za-z0-9_.-]+)*\."
    r"(?:py|js|mjs|ts|tsx|jsx|html|css|scss|json|md|txt|yml|yaml|toml|sql|sh|cfg|ini|svg|xml|csv))\b"
)
_DIR_PATH_RE = re.compile(r"(?<![A-Za-z0-9_./:-])([A-Za-z0-9_.-]+(?:/[A-Za-z0-9_.-]+)*/)")
_SPECIAL_FILES = ("Dockerfile", "Makefile", ".gitignore", ".env.example")
_ITERATE_CONTENT_LIMIT = 24000
_verify_workspace_files = verify_workspace_files
_log = logging.getLogger(__name__)


async def pick_coder_model(preferred: str | None = None) -> str:
    candidates = [
        c for c in (preferred, config.PROJECT_CODER_MODEL, config.STUDIO_CODER_MODEL, "qwen2.5-coder:7b", "qwen3.5:9b", "qwen3.5:4b", config.MASTER_MODEL)
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
        _log.debug("Recoverable error suppressed: %s", exc)
    return config.MASTER_MODEL


async def _ollama_generate(model: str, system: str, user: str, num_predict: int = 4096, temperature: float = 0.25) -> str:
    import gateway

    prof = "code" if temperature <= 0.3 else "analytic"
    res = await gateway.default_client.chat(
        [{"role": "system", "content": system}, {"role": "user", "content": user}],
        model=model,
        profile=prof,
        num_predict=num_predict,
        timeout_s=600.0,
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


def _iter_balanced_braces(text: str) -> list[str]:
    """Extract top-level balanced `{...}` segments while respecting JSON string escapes."""
    candidates: list[str] = []
    depth, start, in_str, escaped = 0, -1, False, False
    for idx, ch in enumerate(text):
        if in_str:
            in_str = not (ch == '"' and not escaped)
            escaped = (ch == "\\") and not escaped
            continue
        if ch == '"':
            in_str = True
        elif ch == "{":
            start = idx if depth == 0 else start
            depth += 1
        elif ch == "}" and depth > 0:
            depth -= 1
            if depth == 0 and start >= 0:
                candidates.append(text[start : idx + 1])
                start = -1
    return candidates


def _try_parse_json_dict(raw_obj: str) -> dict[str, Any] | None:
    for candidate in (raw_obj, re.sub(r",\s*([}\]])", r"\1", raw_obj)):
        try:
            parsed = json.loads(candidate)
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            continue
    return None


def _extract_json_obj(raw: str) -> dict[str, Any] | None:
    """Parse a JSON object from LLM text using balanced-brace scanning and trailing-comma cleanup."""
    if not raw:
        return None
    parsed_dicts: list[dict[str, Any]] = []
    for seg in _iter_balanced_braces(raw):
        obj = _try_parse_json_dict(seg)
        if obj is not None:
            parsed_dicts.append(obj)
    for obj in parsed_dicts:
        if "files" in obj:
            return obj
    return parsed_dicts[0] if parsed_dicts else None


def _is_safe_rel_path(rel: str) -> bool:
    parts = [p for p in rel.split("/") if p]
    if not parts or any(p in (".", "..") or p in SKIP_DIRS for p in parts):
        return False
    return not any(c in rel for c in (":", "*", "?", "<", ">", "|"))


def _extract_requested_paths(prompt: str) -> tuple[list[str], list[str]]:
    """Extract explicitly mentioned file and folder paths from the user prompt."""
    cleaned_prompt = re.sub(r"https?://\S+", " ", (prompt or "").split("\n\n--- ARAŞTIRILMIŞ ÜRÜN TANIMI")[0])  # the research brief is not a list of paths
    files: list[str] = []
    dirs: list[str] = []
    seen_files: set[str] = set()
    seen_dirs: set[str] = set()

    for m in _FILE_PATH_RE.finditer(cleaned_prompt):
        rel = m.group(1).replace("\\", "/").lstrip("./")
        if _is_safe_rel_path(rel) and not rel.lower().endswith(_BINARY_EXTS) and rel not in seen_files:
            seen_files.add(rel)
            files.append(rel)
    for sp in _SPECIAL_FILES:
        if re.search(rf"(?<![A-Za-z0-9_.-]){re.escape(sp)}(?![A-Za-z0-9_.-])", cleaned_prompt) and sp not in seen_files:
            seen_files.add(sp)
            files.append(sp)
    for m in _DIR_PATH_RE.finditer(cleaned_prompt):
        rel = m.group(1).replace("\\", "/").strip("/")
        if _is_safe_rel_path(rel) and rel not in seen_dirs:
            seen_dirs.add(rel)
            dirs.append(rel)
    return files, dirs


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


def _filter_planned_files(raw_files: list[Any], limit: int = 16) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    seen: set[str] = set()
    for f in raw_files[:limit]:
        if not isinstance(f, dict) or not f.get("path"):
            continue
        rel = str(f["path"]).replace("\\", "/").lstrip("/")
        if not _is_safe_rel_path(rel) or rel.lower().endswith(_BINARY_EXTS) or rel in seen or rel.endswith("/"):  # a folder is not a file to write
            continue
        seen.add(rel)
        out.append({"path": rel, "purpose": str(f.get("purpose", ""))})
    return out


def _ensure_requested_tests(planned: list[dict[str, str]], prompt: str) -> None:
    """The user asked for tests but the plan has no test file: add one that imports and exercises the real modules."""
    if re.search(r"pytest|unittest|test(?:ler|leri|ini)?\b", prompt, re.IGNORECASE) and not any("test" in f["path"].lower() for f in planned):
        planned.append({"path": "tests/test_app.py", "purpose": "pytest testleri: projedeki gerçek modülleri içe aktarıp ana işlevleri ve uç durumları sınar"})


def _prepare_workspace_from_plan(
    plan: dict[str, Any], prompt: str, model: str
) -> tuple[Path, dict[str, Any], list[dict[str, str]]]:
    ws_name = str(plan.get("name") or "Yeni Proje").strip()
    ws_id = make_workspace_id(ws_name)
    ws_dir = safe_workspace_dir(ws_id)
    ws_dir.mkdir(parents=True, exist_ok=True)

    raw_files = plan.get("files") if isinstance(plan.get("files"), list) else []
    planned_files = _filter_planned_files(raw_files, limit=16)
    if not planned_files:
        fb = _fallback_architecture_plan(prompt, str(plan.get("project_type") or "auto"))
        planned_files = _filter_planned_files(fb["files"], limit=16)
    _ensure_requested_tests(planned_files, prompt.split("\n\n--- ARAŞTIRILMIŞ ÜRÜN TANIMI")[0])

    req_files, req_dirs = _extract_requested_paths(prompt)
    existing_paths = {f["path"] for f in planned_files}
    for rf in req_files:
        if rf not in existing_paths:
            planned_files.append({"path": rf, "purpose": "Kullanıcı isteğinde belirtilen dosya"})
            existing_paths.add(rf)
    for rd in req_dirs:
        try:
            safe_file_path(ws_dir, rd).mkdir(parents=True, exist_ok=True)
        except ValueError:
            continue

    default_entry = planned_files[0]["path"] if planned_files else "README.md"
    meta: dict[str, Any] = {
        "id": ws_id,
        "name": ws_name,
        "project_type": str(plan.get("project_type") or "web"),
        "description": str(plan.get("description") or prompt[:180]),
        "entry_point": str(plan.get("entry_point") or default_entry),
        "requested_dirs": req_dirs,
        "model": model,
        "prompt": prompt,
        "created_at": datetime.now(UTC).isoformat(),
        "updated_at": datetime.now(UTC).isoformat(),
    }
    save_workspace_meta(ws_dir, meta)
    return ws_dir, meta, planned_files


def _extract_python_contract(code: str) -> str:
    syms: list[str] = []
    try:
        tree = ast.parse(code)
        for node in tree.body:
            if isinstance(node, ast.ClassDef):
                syms.append(f"class {node.name}")
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                args = [a.arg for a in node.args.args[:4]]
                syms.append(f"def {node.name}({', '.join(args)})")
            elif isinstance(node, ast.Assign):
                for tgt in node.targets:
                    if isinstance(tgt, ast.Name) and tgt.id.isupper():
                        syms.append(tgt.id)
    except SyntaxError:
        syms = re.findall(r"^(?:def|class)\s+([A-Za-z_][A-Za-z0-9_]*)", code, flags=re.M)
    return f"symbols={syms[:14]}"


def _extract_file_contract(fpath: str, code: str) -> str:
    """Produce a compact cross-file interface summary (IDs, classes, exports, Python symbols)."""
    low = fpath.lower()
    if low.endswith((".html", ".htm")):
        ids = list(dict.fromkeys(re.findall(r'\bid=["\']([^"\']+)["\']', code)))[:18]
        classes = list(dict.fromkeys(re.findall(r'\bclass=["\']([^"\']+)["\']', code)))[:12]
        refs = list(dict.fromkeys(re.findall(r'(?:src|href)=["\']([^"\']+)["\']', code)))[:10]
        return f"- {fpath}: ids={ids} classes={classes} refs={refs}"[:240]
    if low.endswith((".css", ".scss")):
        sel_cls = list(dict.fromkeys(re.findall(r"\.([a-zA-Z_-][a-zA-Z0-9_-]*)", code)))[:18]
        sel_ids = list(dict.fromkeys(re.findall(r"#([a-zA-Z_-][a-zA-Z0-9_-]*)", code)))[:10]
        return f"- {fpath}: classes={sel_cls} ids={sel_ids}"[:240]
    if low.endswith((".js", ".mjs", ".ts", ".tsx", ".jsx")):
        fns = list(dict.fromkeys(re.findall(r"(?:export\s+)?(?:async\s+)?function\s+([A-Za-z_$][A-Za-z0-9_$]*)", code)))[:12]
        clz = list(dict.fromkeys(re.findall(r"(?:export\s+)?class\s+([A-Za-z_$][A-Za-z0-9_$]*)", code)))[:6]
        exps = list(dict.fromkeys(re.findall(r"export\s+(?:const|let|var)\s+([A-Za-z_$][A-Za-z0-9_$]*)", code)))[:8]
        return f"- {fpath}: fn={fns} class={clz} exports={exps}"[:240]
    if low.endswith(".py"):
        return f"- {fpath}: {_extract_python_contract(code)}"[:240]
    if low.endswith(".json"):
        try:
            data = json.loads(code)
            keys = list(data.keys())[:12] if isinstance(data, dict) else (list(data[0].keys())[:10] if isinstance(data, list) and data and isinstance(data[0], dict) else [])
            return f"- {fpath}: json_keys={keys}"[:200]
        except json.JSONDecodeError:
            return f"- {fpath}: json"
    return f"- {fpath}: ({len(code)} chars)"


def _validate_code_syntax(fpath: str, code: str) -> str | None:
    if fpath.endswith(".py"):
        try:
            ast.parse(code, filename=fpath)
        except SyntaxError as exc:
            return f"Python SyntaxError ({exc.lineno}. satır: {exc.msg})"
    elif fpath.endswith(".json"):
        try:
            json.loads(code)
        except json.JSONDecodeError as exc:
            return f"JSON DecodeError ({exc.lineno}. satır: {exc.msg})"
    return None


async def _validate_and_fix_code(model: str, fpath: str, code: str) -> str:
    """Validate .py (AST) and .json syntax; auto-retry once and re-verify after repair."""
    err = _validate_code_syntax(fpath, code)
    if err is None:
        return code
    lang = "python" if fpath.endswith(".py") else "json"
    fix_raw = await _ollama_generate(
        model=model,
        system=FILE_WRITER_SYSTEM_PROMPT,
        user=(
            f"`{fpath}` dosyasında sözdizimi hatası oluştu: {err}.\n"
            f"Hatalı içerik:\n```{lang}\n{code}\n```\n\n"
            f"Hatayı düzeltip dosyanın eksiksiz, geçerli {lang} içeriğini döndür."
        ),
        num_predict=4096,
        temperature=0.1,
    )
    fixed = _strip_code_fences(fix_raw)
    err2 = _validate_code_syntax(fpath, fixed)
    if err2 is None:
        return fixed
    if fpath.endswith(".json"):
        recovered = _extract_json_obj(fixed) or _extract_json_obj(code)
        if recovered is not None:
            return json.dumps(recovered, ensure_ascii=False, indent=2)
    _log.warning("Syntax re-verification still failed for %s: %s", fpath, err2)
    return fixed


def _write_workspace_file(ws_dir: Path, fpath: str, code: str) -> Path:
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
    return target


async def _generate_and_write_file(
    ws_dir: Path,
    model: str,
    fspec: dict[str, str],
    file_prompt: str,
) -> str:
    fpath = fspec["path"]
    raw_code = await _ollama_generate(model=model, system=FILE_WRITER_SYSTEM_PROMPT, user=file_prompt, num_predict=4096, temperature=0.2)
    code = await _validate_and_fix_code(model, fpath, _strip_code_fences(raw_code))
    _write_workspace_file(ws_dir, fpath, code)
    return code


def _build_existing_contracts(ws_dir: Path, rel_files: list[str], limit: int = 20) -> str:
    lines: list[str] = []
    for rel in rel_files[:limit]:
        p = ws_dir / rel
        if not p.is_file() or p.suffix.lower() in _BINARY_EXTS:
            continue
        try:
            text = p.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        lines.append(_extract_file_contract(rel, text))
    return "\n".join(lines)


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
    contracts: list[str] = []

    for idx, fspec in enumerate(planned_files, start=1):
        fpath = fspec["path"]
        yield {"type": "file_start", "path": fpath, "index": idx, "total": len(planned_files)}
        manifest_block = "\n".join(contracts)
        context_tail = "\n\n".join(written_snippets[-3:])
        file_prompt = (
            f"Proje Adı: {meta['name']}\nProje Türü: {meta['project_type']}\nKullanıcı İsteği: {prompt}\n\n"
            f"Tüm Dosya Ağacı:\n{tree_summary}\n\n"
            + (f"Yazılan Dosyaların Sözleşme Özeti (ID/CSS/Export/Sembol):\n{manifest_block}\n\n" if manifest_block else "")
            + (f"Son dosyaların kod özetleri:\n{context_tail}\n\n" if context_tail else "")
            + f"ŞİMDİ SADECE ŞU DOSYANIN EKSİKSİZ İÇERİĞİNİ YAZ: `{fpath}`\nDosya amacı: {fspec['purpose']}"
        )
        code = await _generate_and_write_file(ws_dir, model, fspec, file_prompt)
        contracts.append(_extract_file_contract(fpath, code))
        written_snippets.append(f"=== {fpath} ===\n{code[:1200]}")
        yield {"type": "file_done", "path": fpath, "size": len(code.encode("utf-8")), "index": idx, "total": len(planned_files)}

    repair_project(ws_dir)
    smoke_warning = ""
    async for evt in smoke_and_repair(ws_dir, lambda _p, ask: _ollama_generate(model, FILE_WRITER_SYSTEM_PROMPT, ask, temperature=0.1)):
        if evt["type"] == "status":
            yield evt
        else:
            smoke_warning = evt["warning"]
    warnings = verify_workspace_files(ws_dir) + ([smoke_warning] if smoke_warning else [])
    create_snapshot(ws_dir, "İlk oluşturma")
    meta["versions"] = list_snapshots(ws_dir)
    meta["updated_at"] = datetime.now(UTC).isoformat()
    save_workspace_meta(ws_dir, meta)
    yield {"type": "done", "workspace": meta, "tree": build_file_tree(ws_dir), "warnings": warnings}


def _select_iterate_targets(
    ws_dir: Path, parsed: dict[str, Any] | None, existing_files: list[str], meta: dict[str, Any], instruction: str
) -> list[dict[str, str]]:
    raw_targets = (parsed or {}).get("files") or []
    targets = _filter_planned_files(raw_targets, limit=6)
    req_files, req_dirs = _extract_requested_paths(instruction)
    for rd in req_dirs:
        try:
            safe_file_path(ws_dir, rd).mkdir(parents=True, exist_ok=True)
        except ValueError:
            continue
    seen = {t["path"] for t in targets}
    for rf in req_files:
        if rf not in seen:
            targets.append({"path": rf, "purpose": instruction})
            seen.add(rf)
    if not targets and existing_files:
        targets = [{"path": str(meta.get("entry_point") or existing_files[0]), "purpose": instruction}]
    return targets[:8]


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
        system="Sadece geçerli JSON döndür. En fazla 6 dosya seç.",
        user=plan_prompt,
        num_predict=1024,
        temperature=0.15,
    )
    targets = _select_iterate_targets(ws_dir, _extract_json_obj(raw_plan), existing_files, meta, instruction)
    contract_manifest = _build_existing_contracts(ws_dir, existing_files)

    for idx, fspec in enumerate(targets, start=1):
        fpath = fspec["path"]
        yield {"type": "file_start", "path": fpath, "index": idx, "total": len(targets)}
        target = safe_file_path(ws_dir, fpath)
        current_content = target.read_text(encoding="utf-8", errors="replace") if target.is_file() else ""
        edit_prompt = (
            f"Proje: {meta.get('name')}\nMevcut dosyalar: {', '.join(existing_files)}\n"
            + (f"Proje Dosya Sözleşmeleri:\n{contract_manifest}\n\n" if contract_manifest else "")
            + f"Değişiklik isteği: {instruction}\nHedef dosya: `{fpath}` ({fspec.get('purpose', '')})\n\n"
            + (f"Mevcut dosya içeriği:\n```\n{current_content[:_ITERATE_CONTENT_LIMIT]}\n```\n\n" if current_content else "")
            + "Bu dosyanın güncel ve EKSİKSİZ tüm içeriğini yaz."
        )
        code = await _generate_and_write_file(ws_dir, model, fspec, edit_prompt)
        yield {"type": "file_done", "path": fpath, "size": len(code.encode("utf-8")), "index": idx, "total": len(targets)}

    repair_project(ws_dir)
    warnings = verify_workspace_files(ws_dir)
    create_snapshot(ws_dir, instruction[:60])
    meta["versions"] = list_snapshots(ws_dir)
    meta["updated_at"] = datetime.now(UTC).isoformat()
    save_workspace_meta(ws_dir, meta)
    yield {"type": "done", "workspace": meta, "tree": build_file_tree(ws_dir), "warnings": warnings}

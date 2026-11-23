"""IDE-06 & IDE-18: Multi-target build packaging (PWA, Docker) and static/DOM web UI verifier inside master/factory/."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from code_graph import IGNORED_DIRS, parse_html_file

_GET_BY_ID_RE = re.compile(r"""document\.getElementById\(\s*['"]([^'"]+)['"]\s*\)""")
_QUERY_ID_RE = re.compile(r"""document\.querySelector(?:All)?\(\s*['"]#([A-Za-z0-9_-]+)['"]\s*\)""")
_VIEWPORT_RE = re.compile(r"""<meta\b[^>]*name\s*=\s*['"]viewport['"]""", re.IGNORECASE)
_JS_HAZARD_RE = re.compile(r"""\b(?:undefinedVariable|null\.[A-Za-z_]|NaN\s*===\s*NaN)\b""")


def generate_pwa_assets(ws_dir: Path, app_name: str = "AI Studio App") -> dict[str, Any]:
    ws_dir = Path(ws_dir).resolve()
    ws_dir.mkdir(parents=True, exist_ok=True)
    clean_name = (app_name or "AI Studio App").strip() or "AI Studio App"
    manifest_data = {
        "name": clean_name,
        "short_name": clean_name[:12].strip() or "AIApp",
        "start_url": "/index.html",
        "display": "standalone",
        "background_color": "#090d16",
        "theme_color": "#4f46e5",
    }
    manifest_path = ws_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest_data, indent=2, ensure_ascii=False), encoding="utf-8")
    sw_path = ws_dir / "service-worker.js"
    sw_path.write_text(
        "self.addEventListener('install', () => self.skipWaiting());\n"
        "self.addEventListener('fetch', (e) => { if (e.request.method === 'GET') e.respondWith(fetch(e.request)); });\n",
        encoding="utf-8",
    )
    return {"manifest_path": str(manifest_path), "service_worker_path": str(sw_path), "app_name": clean_name}


def generate_docker_bundle(ws_dir: Path, port: int = 8080) -> dict[str, Any]:
    ws_dir = Path(ws_dir).resolve()
    ws_dir.mkdir(parents=True, exist_ok=True)
    safe_port = max(1024, min(int(port or 8080), 65535))
    cmd = f'CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "{safe_port}"]' if (ws_dir / "main.py").is_file() else f'CMD ["python", "-m", "http.server", "{safe_port}"]'
    dockerfile_path = ws_dir / "Dockerfile"
    dockerfile_path.write_text(f"FROM python:3.12-slim\nWORKDIR /app\nCOPY . /app\nEXPOSE {safe_port}\n{cmd}\n", encoding="utf-8")
    svc = re.sub(r"[^a-z0-9_-]", "-", ws_dir.name.lower()).strip("-") or "ai-app"
    compose_path = ws_dir / "docker-compose.yml"
    compose_path.write_text(f"services:\n  {svc}:\n    build: .\n    ports:\n      - '127.0.0.1:{safe_port}:{safe_port}'\n", encoding="utf-8")
    return {"dockerfile_path": str(dockerfile_path), "docker_compose_path": str(compose_path), "port": safe_port}


def verify_web_workspace_ui(ws_dir: Path) -> dict[str, Any]:
    ws_dir = Path(ws_dir).resolve()
    html_files, css_files, js_files = [], [], []
    if ws_dir.exists():
        for p in sorted(ws_dir.rglob("*")):
            if any(part in IGNORED_DIRS for part in p.parts) or not p.is_file():
                continue
            ext = p.suffix.lower()
            if ext == ".html":
                html_files.append(p)
            elif ext == ".css":
                css_files.append(p)
            elif ext in {".js", ".ts"}:
                js_files.append(p)

    all_ids: set[str] = set()
    missing_viewport, broken_links, missing_dom, hazards = [], [], [], []
    for hp in html_files:
        rel = hp.relative_to(ws_dir).as_posix()
        src = hp.read_text(encoding="utf-8", errors="replace")
        parsed = parse_html_file(src)
        all_ids.update(parsed["ids"])
        if not _VIEWPORT_RE.search(src):
            missing_viewport.append(rel)
        for ref in [*parsed["scripts"], *parsed["stylesheets"]]:
            cleaned = ref.split("?", 1)[0].split("#", 1)[0].strip()
            if not cleaned or cleaned.startswith(("http://", "https://", "//", "data:")):
                continue
            target = (ws_dir / cleaned.lstrip("/")) if cleaned.startswith("/") else (hp.parent / cleaned)
            if not target.is_file():
                broken_links.append({"file": rel, "asset": cleaned})

    for jp in js_files:
        rel = jp.relative_to(ws_dir).as_posix()
        src = jp.read_text(encoding="utf-8", errors="replace")
        for ref_id in sorted(set(_GET_BY_ID_RE.findall(src)) | set(_QUERY_ID_RE.findall(src))):
            if html_files and ref_id not in all_ids:
                missing_dom.append({"js_file": rel, "id": ref_id})
        if src.count("{") != src.count("}"):
            hazards.append({"file": rel, "type": "unbalanced_braces"})
        for m in _JS_HAZARD_RE.finditer(src):
            hazards.append({"file": rel, "type": "runtime_hazard", "token": m.group(0)})

    total = len(missing_viewport) + len(broken_links) + len(missing_dom) + len(hazards)
    return {
        "workspace": str(ws_dir),
        "ok": total == 0,
        "html_file_count": len(html_files),
        "css_file_count": len(css_files),
        "js_file_count": len(js_files),
        "missing_viewport_files": missing_viewport,
        "broken_asset_links": broken_links,
        "missing_dom_ids": missing_dom,
        "runtime_js_hazards": hazards,
        "total_issues": total,
    }

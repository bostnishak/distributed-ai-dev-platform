"""Cluster B (`[M26]`, Faz 6.4): Multi-Target Build & Deployment Pipelines (PWA, Docker, PyInstaller).

Provides:
- `generate_pwa_assets(ws_dir: Path, app_name: str = "AI Studio App") -> dict`
- `generate_docker_bundle(ws_dir: Path, port: int = 8080) -> dict`
- `generate_all_deploy_targets(ws_dir: Path) -> dict`
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


def generate_pwa_assets(ws_dir: Path, app_name: str = "AI Studio App") -> dict[str, Any]:
    """Write a valid `manifest.json` and offline-capable `service-worker.js` into `ws_dir`."""
    ws_dir = Path(ws_dir).resolve()
    ws_dir.mkdir(parents=True, exist_ok=True)
    clean_name = (app_name or "AI Studio App").strip() or "AI Studio App"
    short_name = clean_name[:12].strip() or "AIApp"

    manifest_data = {
        "name": clean_name,
        "short_name": short_name,
        "start_url": "/index.html",
        "display": "standalone",
        "background_color": "#090d16",
        "theme_color": "#4f46e5",
        "orientation": "any",
        "icons": [
            {
                "src": "/icon-192.png",
                "sizes": "192x192",
                "type": "image/png",
            },
            {
                "src": "/icon-512.png",
                "sizes": "512x512",
                "type": "image/png",
            },
        ],
    }

    manifest_path = ws_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest_data, indent=2, ensure_ascii=False), encoding="utf-8")

    sw_code = """const CACHE_NAME = "ai-studio-pwa-v1";
const OFFLINE_ASSETS = [
  "/",
  "/index.html",
  "/styles.css",
  "/app.js",
  "/manifest.json"
];

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(OFFLINE_ASSETS))
  );
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => k !== CACHE_NAME).map((k) => caches.delete(k)))
    )
  );
  self.clients.claim();
});

self.addEventListener("fetch", (event) => {
  if (event.request.method !== "GET") return;
  event.respondWith(
    caches.match(event.request).then((cached) => cached || fetch(event.request))
  );
});
"""
    sw_path = ws_dir / "service-worker.js"
    sw_path.write_text(sw_code, encoding="utf-8")

    return {
        "manifest_path": str(manifest_path),
        "service_worker_path": str(sw_path),
        "app_name": clean_name,
    }


def generate_docker_bundle(ws_dir: Path, port: int = 8080) -> dict[str, Any]:
    """Write production `Dockerfile` and `docker-compose.yml` into `ws_dir`."""
    ws_dir = Path(ws_dir).resolve()
    ws_dir.mkdir(parents=True, exist_ok=True)
    safe_port = max(1024, min(int(port or 8080), 65535))

    has_requirements = (ws_dir / "requirements.txt").is_file()
    has_main_py = (ws_dir / "main.py").is_file()

    if has_main_py:
        cmd_line = f'CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "{safe_port}"]'
    else:
        cmd_line = f'CMD ["python", "-m", "http.server", "{safe_port}"]'

    req_install = (
        "COPY requirements.txt ./\nRUN pip install --no-cache-dir -r requirements.txt\n"
        if has_requirements
        else ""
    )

    dockerfile_content = f"""FROM python:3.11-slim

WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

{req_install}COPY . /app

EXPOSE {safe_port}
{cmd_line}
"""
    dockerfile_path = ws_dir / "Dockerfile"
    dockerfile_path.write_text(dockerfile_content, encoding="utf-8")

    service_name = re.sub(r"[^a-z0-9_-]", "-", ws_dir.name.lower()).strip("-") or "ai-app"
    compose_content = f"""version: "3.9"
services:
  {service_name}:
    build: .
    ports:
      - "{safe_port}:{safe_port}"
    restart: unless-stopped
"""
    compose_path = ws_dir / "docker-compose.yml"
    compose_path.write_text(compose_content, encoding="utf-8")

    return {
        "dockerfile_path": str(dockerfile_path),
        "docker_compose_path": str(compose_path),
        "port": safe_port,
    }


def generate_all_deploy_targets(ws_dir: Path) -> dict[str, Any]:
    """Generate PWA assets, Docker bundle, and a PyInstaller `.spec` build configuration in `ws_dir`."""
    ws_dir = Path(ws_dir).resolve()
    ws_dir.mkdir(parents=True, exist_ok=True)

    pwa = generate_pwa_assets(ws_dir, app_name=ws_dir.name)
    docker = generate_docker_bundle(ws_dir, port=8080)

    py_candidates = [p.name for p in sorted(ws_dir.glob("*.py"))]
    entry_script = "main.py"
    for preferred in ("app_gui.py", "main.py", "cli.py", "app.py"):
        if preferred in py_candidates:
            entry_script = preferred
            break
    else:
        if py_candidates:
            entry_script = py_candidates[0]

    app_slug = re.sub(r"[^A-Za-z0-9_]", "_", ws_dir.name).strip("_") or "EnterpriseApp"
    spec_content = f"""# -*- mode: python ; coding: utf-8 -*-

a = Analysis(
    ['{entry_script}'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={{}},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='{app_slug}',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
)
"""
    spec_path = ws_dir / f"{app_slug}.spec"
    spec_path.write_text(spec_content, encoding="utf-8")

    return {
        "pwa": pwa,
        "docker": docker,
        "pyinstaller_spec_path": str(spec_path),
        "entry_script": entry_script,
    }

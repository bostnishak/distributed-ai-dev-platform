"""Functional check of a generated web page: load it in jsdom inside the offline Docker sandbox, click every control, type into inputs.

What it catches: scripts that throw at load or on click, handlers that were never attached, pages that do not react at all.
jsdom is installed once from a networked step (cached); the page itself runs without network.
"""

from __future__ import annotations

import json
import re
import shutil
import tempfile
from pathlib import Path
from typing import Any

from sandbox import runner

NODE_IMAGE = "node:20-slim"
_PROBE = (Path(__file__).parent / "prompts" / "jsdom_probe.js.txt").read_text(encoding="utf-8")
_CACHE = Path(tempfile.gettempdir()) / "cm6453_jsdom"
_HARDENING = ["--rm", "--cap-drop", "ALL", "--security-opt", "no-new-privileges:true", "--memory", "768m", "--cpus", "1", "--pids-limit", "256"]
_FRAME_RE = re.compile(r"file:///sandbox/([\w./-]+\.(?:js|html)):(\d+)")


def has_page(ws_dir: Path) -> bool:
    return (ws_dir / "index.html").is_file()


def _ensure_jsdom() -> bool:
    if (_CACHE / "node_modules" / "jsdom").is_dir():
        return True
    _CACHE.mkdir(parents=True, exist_ok=True)
    (_CACHE / "package.json").write_text('{"name":"probe","private":true}', encoding="utf-8")
    args = ["docker", "run", *_HARDENING, "-v", f"{_CACHE.resolve()}:/app", "-w", "/app", "-e", "HOME=/tmp", NODE_IMAGE, "npm", "install", "--ignore-scripts", "--no-audit", "--no-fund", "--loglevel=error", "jsdom@22"]
    runner._run_docker_cmd(args, timeout_s=300)
    return (_CACHE / "node_modules" / "jsdom").is_dir()


def probe(ws_dir: Path) -> dict[str, Any] | None:
    """{"errors": [...], "controls": N, "clicked": N, "changed": bool} for the page, or None when the sandbox/jsdom is unavailable."""
    if not _ensure_jsdom():
        return None
    with tempfile.TemporaryDirectory(prefix="cm6453_web_") as tmp:
        stage = Path(tmp) / "ws"
        shutil.copytree(ws_dir, stage, ignore=shutil.ignore_patterns(".history", ".git", "node_modules"))
        (stage / ".probe.js").write_text(_PROBE, encoding="utf-8")
        args = ["docker", "run", *_HARDENING, "--network", "none", "-v", f"{stage.resolve()}:/sandbox", "-v", f"{(_CACHE / 'node_modules').resolve()}:/node_modules:ro",
                "-w", "/sandbox", "-e", "NODE_PATH=/node_modules", NODE_IMAGE, "timeout", "25", "node", ".probe.js"]
        proc = runner._run_docker_cmd(args, timeout_s=60)
    line = next((ln for ln in reversed(proc.stdout.splitlines()) if ln.startswith("{")), "")
    try:
        return json.loads(line)
    except ValueError:
        return None


def problem(ws_dir: Path, result: dict[str, Any]) -> tuple[Path | None, str] | None:
    """(file to repair, error text) when the probe found a functional problem, else None."""
    errors = result.get("errors") or []
    if errors:
        text = "\n".join(errors)
        m = _FRAME_RE.search(text)
        target = ws_dir / m.group(1) if m and (ws_dir / m.group(1)).is_file() else _main_script(ws_dir)
        return target, "Sayfa tarayıcı ortamında çalıştırıldığında şu hatalar oluştu:\n" + text
    shown = " ".join(result.get("texts") or [])
    if re.search(r"\bNaN\b|\bundefined\b|\[object|\bnull\b|Infinity", shown):
        return _main_script(ws_dir), f"Sayfada kullanıcıya bozuk değerler görünüyor (NaN/undefined/null): \"{shown[:140]}\". Başlangıç durumunu ve hesaplama/biçimlendirme kodunu düzelt; ekranda hiçbir zaman NaN, undefined ya da null yazmasın."
    if result.get("controls", 0) >= 3 and not result.get("changed"):
        return _main_script(ws_dir), f"Sayfada {result['controls']} düğme/kontrol var ama hiçbirine tıklayınca sayfa içeriği değişmiyor: olay dinleyicileri bağlanmamış ya da id/sınıf adları uyuşmuyor."
    return None


def _main_script(ws_dir: Path) -> Path | None:
    html = (ws_dir / "index.html").read_text(encoding="utf-8", errors="replace")
    for src in re.findall(r'<script[^>]+src=["\']([^"\']+)["\']', html):
        p = ws_dir / src.lstrip("./")
        if p.is_file():
            return p
    return None

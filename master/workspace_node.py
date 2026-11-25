"""Run generated Node.js projects in a throw-away, offline Docker container (dependencies come from a networked install step)."""

from __future__ import annotations

import hashlib
import json
import re
import shutil
import tempfile
from pathlib import Path

from sandbox import runner

NODE_IMAGE = "node:20-slim"
_CACHE = Path(tempfile.gettempdir()) / "cm6453_node_modules"
_FALLBACK_ENTRIES = ("server.js", "index.js", "app.js", "src/index.js", "src/server.js", "main.js")
_FRAME_RE = re.compile(r"(/sandbox/[^\s:()]+\.js):(\d+)")
_HARDENING = ["--rm", "--cap-drop", "ALL", "--security-opt", "no-new-privileges:true", "--memory", "512m", "--cpus", "1", "--pids-limit", "128"]


def _package(ws_dir: Path) -> dict:
    try:
        data = json.loads((ws_dir / "package.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def find_entry(ws_dir: Path) -> str | None:
    """Relative path of the script `npm start` would run, or None when this is not a runnable Node project."""
    pkg = _package(ws_dir)
    if not pkg:
        return None
    start = str((pkg.get("scripts") or {}).get("start", ""))
    m = re.match(r"node\s+(\S+\.js)\b", start)
    candidates = [m.group(1)] if m else []
    candidates += [str(pkg["main"])] if pkg.get("main") else []
    candidates += list(_FALLBACK_ENTRIES)
    return next((c for c in candidates if (ws_dir / c).is_file()), None)


def failing_file(ws_dir: Path, log: str) -> Path | None:
    for raw, _line in reversed(_FRAME_RE.findall(log)):
        p = ws_dir / raw.removeprefix("/sandbox/")
        if p.is_file() and "node_modules" not in p.parts:
            return p
    return None


def _install(ws_dir: Path, stage: Path) -> None:
    pkg = _package(ws_dir)
    if not (pkg.get("dependencies") or pkg.get("devDependencies")):
        return
    key = hashlib.sha256(json.dumps([pkg.get("dependencies"), pkg.get("devDependencies")], sort_keys=True).encode()).hexdigest()[:16]
    cached = _CACHE / key / "node_modules"
    if not cached.is_dir():
        stage_cmd = ["docker", "run", *_HARDENING, "-v", f"{stage.resolve()}:/app", "-w", "/app", "-e", "HOME=/tmp", NODE_IMAGE,
                     "npm", "install", "--ignore-scripts", "--no-audit", "--no-fund", "--loglevel=error"]
        runner._run_docker_cmd(stage_cmd, timeout_s=300)
        if (stage / "node_modules").is_dir():
            shutil.copytree(stage / "node_modules", cached)
    elif not (stage / "node_modules").exists():
        shutil.copytree(cached, stage / "node_modules")


def run_probe(ws_dir: Path, entry: str) -> tuple[bool, str]:
    """(ok, log). Still running when the timeout hits means the server started fine."""
    with tempfile.TemporaryDirectory(prefix="cm6453_node_") as tmp:
        stage = Path(tmp) / "ws"
        shutil.copytree(ws_dir, stage, ignore=shutil.ignore_patterns(".history", ".git", "node_modules"))
        _install(ws_dir, stage)
        args = ["docker", "run", *_HARDENING, "--network", "none", "-v", f"{stage.resolve()}:/sandbox", "-w", "/sandbox",
                "-e", "PORT=3000", "-e", "NODE_ENV=development", NODE_IMAGE, "timeout", "10", "node", entry]
        proc = runner._run_docker_cmd(args, timeout_s=40)
    if proc.timed_out or proc.returncode in (0, 124):  # 124 = our own `timeout` ended a server that kept running
        return True, ""
    return False, (proc.stderr or proc.stdout)[-2000:]

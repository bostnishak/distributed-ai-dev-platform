"""Notice files saved by another program (an editor, git, a sync tool) inside a project.

Each look compares every project file's time and size with the last look. A change that the platform did not record
itself is written into the project's history, the state is saved as a version, and the files are checked.
"""

from __future__ import annotations

import json
import logging
import time
from datetime import datetime
from pathlib import Path

import atomic_io
import code_audit
import config
import event_log
import workspace_builder_ops as ops

_log = logging.getLogger(__name__)
_SKIP = {".history", ".ai-os", ".git", "node_modules", "__pycache__", ".venv", "venv", "dist", "build"}
_OWN_MARGIN_S = 15
_MAX_FILES = 300


def _state_file() -> Path:
    return config.data_dir() / "external_watch.json"


def signature(ws_dir: Path) -> dict[str, list[int]]:
    found: dict[str, list[int]] = {}
    for path in sorted(ws_dir.rglob("*")):
        relative = path.relative_to(ws_dir)
        if _SKIP & set(relative.parts) or relative.name.startswith(".") or not path.is_file():
            continue
        stat = path.stat()
        found[relative.as_posix()] = [stat.st_mtime_ns, stat.st_size]
        if len(found) >= _MAX_FILES:
            break
    return found


def _recorded_by_platform(ws_dir: Path, changed_at: float) -> bool:
    """True when the history already has an entry at (or after) the time the file changed."""
    events = event_log.read(ws_dir, 1)
    if not events:
        return False
    try:
        last = datetime.strptime(events[-1]["at"], "%Y-%m-%dT%H:%M:%S").timestamp()
    except (KeyError, ValueError):
        return False
    return last >= changed_at - _OWN_MARGIN_S


def _handle(ws_dir: Path, changed: list[str], removed: list[str]) -> None:
    detail = ", ".join([*changed[:5], *(f"{name} (silindi)" for name in removed[:3])])
    event_log.record(ws_dir, "dışarıdan değişiklik", detail)
    try:
        ops.create_snapshot(ws_dir, "dışarıdan değişiklik")
        problems = code_audit.diagnostics(ws_dir)
    except (OSError, ValueError, RuntimeError) as exc:
        _log.warning("dış değişiklik işlenemedi (%s): %r", ws_dir.name, exc)
        return
    if problems:
        event_log.record(ws_dir, "dış değişiklikten sonra sorun", "; ".join(str(p) for p in problems[:3]))


def scan(root: Path | None = None) -> list[str]:
    """Project ids that were changed from outside since the last look. The first look only remembers."""
    root = root or ops.workspaces_root()
    if not root.is_dir():
        return []
    try:
        known = json.loads(_state_file().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        known = {}
    current, outside = {}, []
    for ws_dir in sorted(p for p in root.iterdir() if p.is_dir()):
        try:
            now = current[ws_dir.name] = signature(ws_dir)
        except OSError:
            continue
        before = known.get(ws_dir.name)
        if before is None or before == now:
            continue
        changed = [name for name, value in now.items() if before.get(name) != value]
        removed = [name for name in before if name not in now]
        newest = max((now[name][0] / 1e9 for name in changed), default=time.time())
        if not _recorded_by_platform(ws_dir, newest):
            _handle(ws_dir, changed, removed)
            outside.append(ws_dir.name)
    if current != known:
        atomic_io.write_text(_state_file(), json.dumps(current))
    return outside

"""The night summary: what happened to the projects in the last day, what failed, known vulnerabilities, disk and
database health. Written to data/reports at the nightly hour; "gece özeti" builds it on demand.
"""

from __future__ import annotations

import re
import time
from collections.abc import Callable
from datetime import datetime, timedelta
from pathlib import Path

import atomic_io
import config
import db_health
import dependency_audit
import disk_gc
import event_log
import research_context
import workspace_builder_ops as ops

_ASK_RE = re.compile(r"^\s*(?:gece|günlük)\s+özeti\s*[.!?]?\s*$", re.IGNORECASE)
_FAILURE_WORDS = ("sorun", "durdu", "başarısız", "hata", "geri al")


def _recent(ws_dir: Path, since: datetime) -> list[dict]:
    found = []
    for event in event_log.read(ws_dir, 200):
        try:
            if datetime.strptime(event["at"], "%Y-%m-%dT%H:%M:%S") >= since:
                found.append(event)
        except (KeyError, ValueError):
            continue
    return found


def build(now: datetime | None = None, audit: Callable[[Path], tuple[int, list[str]]] = dependency_audit.audit) -> str:
    now = now or datetime.now()
    projects, failures, vulnerable = [], [], []
    root = ops.workspaces_root()
    for ws_dir in sorted(p for p in root.iterdir() if p.is_dir()):
        events = _recent(ws_dir, now - timedelta(days=1))
        if not events:
            continue
        projects.append(f"- {ws_dir.name}: {len(events)} olay, sonuncusu '{events[-1]['kind']}' ({events[-1]['at'][11:16]})")
        failures += [f"- {ws_dir.name} {e['at'][11:16]} {e['kind']}: {e['detail']}" for e in events if any(w in e["kind"] for w in _FAILURE_WORDS)]
        if research_context.web_enabled() and dependency_audit.pinned(ws_dir):
            try:
                vulnerable += [f"- {ws_dir.name}: {line[2:]}" for line in audit(ws_dir)[1]]
            except (OSError, ValueError, KeyError, RuntimeError) as exc:
                vulnerable.append(f"- {ws_dir.name}: denetlenemedi ({type(exc).__name__})")
    broken = {p.name: result for p in db_health.databases() if (result := db_health.quick_check(p)) != "ok"}
    sections = [f"# Günlük özet — {now:%Y-%m-%d %H:%M}", "## Son 24 saatte değişen projeler", *(projects[:30] or ["- Değişen proje yok."]),
                "## Sorunlar", *(failures[:20] or ["- Kayıtlı sorun yok."]),
                "## Bağımlılık açıkları", *(vulnerable[:20] or ["- Değişen projelerde bilinen açık bulunmadı."]),
                "## Sistem", f"- Veritabanları: {', '.join(f'{k}: {v}' for k, v in broken.items()) if broken else 'denetim temiz'}", f"- {disk_gc.status().splitlines()[0]}"]
    return "\n".join(sections) + "\n"


def write(now: datetime | None = None) -> Path:
    target = config.data_dir() / "reports" / f"gunluk-{time.strftime('%Y-%m-%d')}.md"
    target.parent.mkdir(parents=True, exist_ok=True)
    atomic_io.write_text(target, build(now))
    return target


def answer(prompt: str) -> str:
    return build() if _ASK_RE.match(prompt) else ""

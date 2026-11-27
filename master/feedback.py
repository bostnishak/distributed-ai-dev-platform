"""What the user thought of a delivery: thumbs up or down, and edits made by hand. Kept with the run history."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

import config
import event_log
import security_scan


def _file() -> Path:
    return config.data_dir() / "feedback.jsonl"


def record(ws_dir: Path, kind: str, detail: str = "") -> dict[str, Any]:
    """kind: "beğenildi", "beğenilmedi" or "elle düzenleme". Secrets are removed before anything is written."""
    entry = {"at": time.strftime("%Y-%m-%dT%H:%M:%S"), "workspace": ws_dir.name, "kind": kind, "detail": security_scan.redact(detail)[:500]}
    _file().parent.mkdir(parents=True, exist_ok=True)
    with _file().open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry, ensure_ascii=False) + "\n")
    event_log.record(ws_dir, kind, entry["detail"])
    return entry


def load(limit: int = 200) -> list[dict[str, Any]]:
    try:
        lines = _file().read_text(encoding="utf-8").splitlines()[-limit:]
        return [json.loads(line) for line in lines]
    except (OSError, ValueError):
        return []

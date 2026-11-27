"""Append-only history of what happened to a project: every saved version and every return to an older one.

Together with the version snapshots this gives time travel: any listed state can be restored, and nothing is rewritten.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

FILE = ".events.jsonl"


def record(ws_dir: Path, kind: str, detail: str) -> None:
    try:
        with (ws_dir / FILE).open("a", encoding="utf-8") as handle:
            handle.write(json.dumps({"at": time.strftime("%Y-%m-%dT%H:%M:%S"), "kind": kind, "detail": detail[:160]}, ensure_ascii=False) + "\n")
    except OSError:
        return  # history is helpful, never a reason to fail the change itself


def read(ws_dir: Path, limit: int = 50) -> list[dict]:
    try:
        lines = (ws_dir / FILE).read_text(encoding="utf-8").splitlines()
    except OSError:
        return []
    events = []
    for line in lines[-limit:]:
        try:
            events.append(json.loads(line))
        except ValueError:
            continue
    return events

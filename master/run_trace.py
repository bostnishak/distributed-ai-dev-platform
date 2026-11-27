"""Stage timings and trajectories of project runs (local files only, secrets removed).

Every status line of a generation closes the previous stage, so the time of each step is measured without touching the
pipeline. Finished runs are appended to data/trajectories.jsonl with the programmatic verdict: the raw material for
evaluation and, later, for fine-tuning.
"""

from __future__ import annotations

import json
import logging
import time
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

import config
import security_scan
import skill_library

_log = logging.getLogger(__name__)
_FAIL_MARK = "Otomatik çalıştırma testi hata"


def _path() -> Path:
    return Path(config.DB_PATH).resolve().parent / "trajectories.jsonl"


def _stage_name(evt: dict[str, Any]) -> str:
    if evt.get("type") == "status":
        return str(evt.get("message", ""))[:80]
    return f"dosya yazımı: {evt.get('path', '')}" if evt.get("type") == "file_start" else ""


def save(record: dict[str, Any]) -> None:
    try:
        path = _path()
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(security_scan.redact(json.dumps(record, ensure_ascii=False)) + "\n")
    except OSError as exc:
        _log.warning("Yörünge kaydedilemedi: %s", exc)


def _file_names(tree: Any) -> list[str]:
    out: list[str] = []
    for node in tree if isinstance(tree, list) else []:
        if node.get("type") in ("dir", "folder"):
            out += _file_names(node.get("children"))
        elif node.get("path") or node.get("name"):
            out.append(str(node.get("path") or node.get("name")))
    return out


async def traced(events: AsyncIterator[dict[str, Any]], request: str) -> AsyncIterator[dict[str, Any]]:
    """Pass the events through unchanged while recording how long each stage took."""
    started = mark = time.monotonic()
    stage, stages = "başlangıç", []
    done: dict[str, Any] = {}
    try:
        async for evt in events:
            if name := _stage_name(evt):
                now = time.monotonic()
                stages.append({"stage": stage, "seconds": round(now - mark, 1)})
                stage, mark = name, now
            if evt.get("type") == "done":
                done = evt
            yield evt
    finally:
        stages.append({"stage": stage, "seconds": round(time.monotonic() - mark, 1)})
        warnings = [str(w) for w in done.get("warnings") or []]
        if done and not any(_FAIL_MARK in w for w in warnings):
            skill_library.add(security_scan.redact(request), _file_names(done.get("tree")))
        save({"at": time.strftime("%Y-%m-%dT%H:%M:%S"), "request": request[:4000], "workspace": (done.get("workspace") or {}).get("id", ""),
              "total_seconds": round(time.monotonic() - started, 1), "stages": stages, "warnings": warnings[:5],
              "passed": bool(done) and not any(_FAIL_MARK in w for w in warnings)})


def summary(limit: int = 50) -> dict[str, Any]:
    """Pass rate, median duration and the slowest stages of the latest runs."""
    try:
        lines = _path().read_text(encoding="utf-8").splitlines()[-limit:]
    except OSError:
        return {"runs": 0}
    runs = [json.loads(line) for line in lines if line.startswith("{")]
    if not runs:
        return {"runs": 0}
    totals = sorted(r["total_seconds"] for r in runs)
    stages = sorted((s for r in runs for s in r["stages"]), key=lambda s: -s["seconds"])[:5]
    return {"runs": len(runs), "pass_rate": round(sum(r["passed"] for r in runs) / len(runs), 2), "median_seconds": totals[len(totals) // 2], "slowest_stages": stages}

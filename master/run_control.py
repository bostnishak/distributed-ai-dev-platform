"""Live state of a multi-step run: its graph, an event log, and the user's controls (pause, resume, steer, edit, skip).

Events are kept in memory for live viewers and appended to data/runs/<id>.jsonl, so a finished run can still be
replayed step by step with the time slider after a restart.
"""

from __future__ import annotations

import asyncio
import json
import re
import time
import uuid
from pathlib import Path
from typing import Any

import config

_RUNS: dict[str, Run] = {}
_KEEP = 20
_ID_RE = re.compile(r"^[a-f0-9]{12}$")


def _folder() -> Path:
    return config.data_dir() / "runs"


class Run:
    def __init__(self, title: str, ws_id: str = "") -> None:
        self.id = uuid.uuid4().hex[:12]
        self.title, self.ws_id = title[:160], ws_id
        self.nodes: dict[str, dict[str, Any]] = {}
        self.events: list[dict[str, Any]] = []
        self.notes: list[str] = []
        self.state = "running"
        self.go = asyncio.Event()
        self.go.set()
        self.started = time.time()

    def emit(self, kind: str, **data: Any) -> None:
        event = {"seq": len(self.events) + 1, "t": round(time.time() - self.started, 2), "kind": kind, **data}
        self.events.append(event)
        try:
            _folder().mkdir(parents=True, exist_ok=True)
            with (_folder() / f"{self.id}.jsonl").open("a", encoding="utf-8") as handle:
                handle.write(json.dumps({"run": self.id, "title": self.title, "ws": self.ws_id, **event}, ensure_ascii=False) + "\n")
        except OSError:
            return  # the live view still works; only the replay after a restart is lost

    def add_node(self, node_id: str, **info: Any) -> None:
        self.nodes[node_id] = {"id": node_id, "status": "waiting", **info}
        self.emit("node", node=dict(self.nodes[node_id]))

    def update(self, node_id: str, **changes: Any) -> None:
        self.nodes[node_id].update(changes)
        self.emit("node", node=dict(self.nodes[node_id]))

    def pause(self) -> None:
        if self.state == "running":
            self.state = "paused"
            self.go.clear()
            self.emit("paused")

    def resume(self) -> None:
        if self.state == "paused":
            self.state = "running"
            self.go.set()
            self.emit("resumed")

    def steer(self, note: str) -> None:
        """A course correction: applies to every step that has not started yet."""
        self.notes.append(note.strip()[:400])
        self.emit("steer", note=self.notes[-1], affects=[n["id"] for n in self.nodes.values() if n["status"] == "waiting"])

    def edit(self, node_id: str, purpose: str = "", skip: bool = False) -> bool:
        node = self.nodes.get(node_id)
        if not node or node["status"] != "waiting":
            return False
        if skip:
            self.update(node_id, status="skipped")
        else:
            self.update(node_id, purpose=purpose.strip()[:600], edited=True)
        return True

    def finish(self, state: str) -> None:
        if self.state in ("running", "paused"):
            self.state = state
            self.go.set()
            self.emit("finished", state=state)

    def summary(self) -> dict[str, Any]:
        return {"id": self.id, "title": self.title, "ws_id": self.ws_id, "state": self.state, "nodes": list(self.nodes.values()), "events": len(self.events)}


def start(title: str, ws_id: str = "") -> Run:
    run = Run(title, ws_id)
    _RUNS[run.id] = run
    for old in list(_RUNS)[:-_KEEP]:
        if _RUNS[old].state not in ("running", "paused"):
            del _RUNS[old]
    run.emit("started", title=run.title)
    return run


def get(run_id: str) -> Run | None:
    return _RUNS.get(run_id)


def events_of(run_id: str) -> list[dict[str, Any]]:
    if run := _RUNS.get(run_id):
        return run.events
    if not _ID_RE.match(run_id):
        return []
    try:
        lines = (_folder() / f"{run_id}.jsonl").read_text(encoding="utf-8").splitlines()
        return [json.loads(line) for line in lines]
    except (OSError, ValueError):
        return []


def recent(limit: int = 10) -> list[dict[str, Any]]:
    """Newest first: live runs, then finished ones found on disk."""
    out = {r.id: r.summary() for r in reversed(list(_RUNS.values()))}
    files = sorted(_folder().glob("*.jsonl"), key=lambda p: p.stat().st_mtime, reverse=True) if _folder().is_dir() else []
    for path in files:
        if len(out) >= limit:
            break
        if path.stem in out or not (events := events_of(path.stem)):
            continue
        finished = next((e["state"] for e in reversed(events) if e["kind"] == "finished"), "interrupted")
        out[path.stem] = {"id": path.stem, "title": events[0].get("title", ""), "ws_id": events[0].get("ws", ""), "state": finished, "nodes": [], "events": len(events)}
    return list(out.values())[:limit]

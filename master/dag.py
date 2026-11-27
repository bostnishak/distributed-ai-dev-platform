"""Run steps in dependency order, as many at once as allowed, under the user's live control.

A step starts only when everything it depends on is done. Among ready steps the one using the model that is already
loaded goes first (fewer reloads). Background steps (warm-ups for the checks that follow) run beside the others and
take no slot. Pausing lets running steps finish and starts nothing new; notes given meanwhile reach later steps.
"""

from __future__ import annotations

import asyncio
import time
from collections.abc import AsyncIterator, Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any

import run_control

_HEARTBEAT_S = 10.0
_MAX_PAUSE_S = 30 * 60


@dataclass
class Node:
    id: str
    work: Callable[[dict[str, Any]], Awaitable[Any]]  # receives the node's live record (purpose may have been edited) plus "notes"
    deps: tuple[str, ...] = ()
    model: str = ""
    title: str = ""
    purpose: str = ""
    background: bool = False
    extra: dict[str, Any] = field(default_factory=dict)


def check(nodes: list[Node]) -> None:
    """ValueError when a dependency is unknown or the graph has a cycle (it could never finish)."""
    known = {n.id for n in nodes}
    if unknown := sorted({d for n in nodes for d in n.deps} - known):
        raise ValueError(f"bilinmeyen bağımlılık: {', '.join(unknown)}")
    done: set[str] = set()
    while len(done) < len(known):
        step = {n.id for n in nodes if n.id not in done and set(n.deps) <= done}
        if not step:
            raise ValueError(f"bağımlılık döngüsü: {', '.join(sorted(known - done))}")
        done |= step


def _ready(run: run_control.Run, nodes: list[Node], started: set[str], last_model: str) -> list[Node]:
    finished = {i for i, n in run.nodes.items() if n["status"] in ("done", "skipped")}
    ready = [n for n in nodes if n.id not in started and run.nodes[n.id]["status"] == "waiting" and set(n.deps) <= finished]
    return sorted(ready, key=lambda n: (not n.background, n.model != last_model))  # stable: plan order within each group


async def _timed(run: run_control.Run, node: Node) -> Any:
    run.update(node.id, status="running")
    started = time.perf_counter()
    result = await node.work({**run.nodes[node.id], "notes": list(run.notes)})
    seconds = round(time.perf_counter() - started, 2)
    size = len(result) if isinstance(result, str) else 0
    run.update(node.id, status="done", seconds=seconds, chars=size, tokens_per_s=round(size / 4 / seconds, 1) if size and seconds else 0)
    return result


async def _wait_while_paused(run: run_control.Run) -> AsyncIterator[tuple[str, None, None]]:
    waited = 0.0
    while run.state == "paused":
        yield "paused", None, None
        try:
            await asyncio.wait_for(run.go.wait(), _HEARTBEAT_S)
        except TimeoutError:
            waited += _HEARTBEAT_S
            if waited >= _MAX_PAUSE_S:
                run.resume()


def _launch(run: run_control.Run, nodes: list[Node], running: dict[asyncio.Task, Node], started: set[str], limits: tuple[int, str]) -> list[Node]:
    """Start every ready step there is room for (nothing while paused); returns the ones started."""
    width, last_model = limits
    launched: list[Node] = []
    if run.state != "running":
        return launched
    for node in _ready(run, nodes, started, last_model):
        if not node.background and sum(not n.background for n in running.values()) >= max(1, width):
            continue
        started.add(node.id)
        running[asyncio.create_task(_timed(run, node))] = node
        launched.append(node)
    return launched


def _result(run: run_control.Run, task: asyncio.Task, node: Node) -> Any:
    if (error := task.exception()) is not None:
        run.update(node.id, status="failed", error=f"{type(error).__name__}: {error}"[:300])
        raise error
    return task.result()


async def execute(run: run_control.Run, nodes: list[Node], width: int = 2) -> AsyncIterator[tuple[str, Node | None, Any]]:
    """Yields ("start", node, None), ("done", node, result) and ("paused", None, None)."""
    check(nodes)
    for n in nodes:
        run.add_node(n.id, title=n.title or n.id, deps=list(n.deps), model=n.model, purpose=n.purpose, background=n.background, **n.extra)
    running: dict[asyncio.Task, Node] = {}
    started: set[str] = set()
    last_model, completed = "", False
    try:
        while True:
            if run.state == "paused" and not running:
                async for item in _wait_while_paused(run):
                    yield item
            for node in _launch(run, nodes, running, started, (width, last_model)):
                last_model = node.model or last_model
                yield "start", node, None
            if not running:
                if run.state == "paused":
                    continue
                break
            finished, _pending = await asyncio.wait(running, timeout=_HEARTBEAT_S, return_when=asyncio.FIRST_COMPLETED)
            for task in finished:
                node = running.pop(task)
                yield "done", node, _result(run, task, node)
        completed = True
    finally:
        for task in running:
            task.cancel()
        run.finish("done" if completed else "interrupted")

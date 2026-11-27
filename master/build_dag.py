"""File writing of a project build and of a follow-up change, as a live dependency graph.

New build: the first file alone (others reuse its ids and classes), the independent files side by side, tests last;
meanwhile the sandbox and browser checks that follow are warmed up. Follow-up change: one file after another.
While it runs the user can pause, add a course correction, rewrite what a waiting file must do, or skip it.
"""

from __future__ import annotations

import asyncio
import importlib.util
import os
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

import checkpoint
import dag
import run_control
import workspace_docker
from workspace_batches import apply_edit, file_batches, file_prompt

WARMUP = "ön hazırlık"


def _notes(record: dict[str, Any]) -> str:
    return "".join(f"\n\nKULLANICININ ÇALIŞIRKEN EKLEDİĞİ TALİMAT (uygula): {n}" for n in record.get("notes", []))


async def _warm_up(_record: dict[str, Any]) -> str:
    """Load what verification will need, while the files are still being written."""
    ready = await asyncio.to_thread(workspace_docker.available)
    browser = importlib.util.find_spec("playwright") is not None
    return f"kod kutusu {'hazır' if ready else 'yok'}, tarayıcı {'hazır' if browser else 'yok'}"


def file_nodes(planned: list[dict[str, Any]], work_for: Any, model: str) -> list[dag.Node]:
    batches = file_batches(planned)
    anchor = batches[0][0]["path"] if batches else ""
    tests = [f["path"] for f in planned[1:] if "test" in f["path"].lower()]
    others = [f["path"] for f in planned if f["path"] not in tests]
    nodes = [dag.Node(WARMUP, _warm_up, title="Denetim ön hazırlığı", background=True)]
    for batch in batches:
        for spec in batch:
            path = spec["path"]
            deps = () if path == anchor else tuple(others) if path in tests else (anchor,)
            nodes.append(dag.Node(path, work_for(spec), deps=deps, model=str(spec.get("model") or model), title=path, purpose=str(spec.get("purpose", ""))))
    return nodes


async def _drive(run: run_control.Run, nodes: list[dag.Node], width: int, order: list[str]) -> AsyncIterator[tuple[str, str, Any]]:
    async for kind, node, result in dag.execute(run, nodes, width):
        if kind == "paused":
            yield "paused", "", None
        elif node is not None and not node.background and node.id in order:
            yield kind, node.id, result


def _file_event(kind: str, path: str, order: list[str], code: str = "") -> dict[str, Any]:
    event = {"type": "file_start" if kind == "start" else "file_done", "path": path, "index": order.index(path) + 1, "total": len(order)}
    if kind == "done":
        event["size"] = len(code.encode("utf-8"))
    return event


_PAUSED = {"type": "status", "message": "Duraklatıldı. Savaş odasından devam ettirebilir ya da talimat ekleyebilirsin."}


async def generate_files(ws_dir: Path, meta: dict[str, Any], request: str, model: str, planned: list[dict[str, Any]]) -> AsyncIterator[dict[str, Any]]:
    import workspace_builder as wb

    run = run_control.start(request, str(meta.get("id", "")))
    width = max(1, int(os.environ.get("WS_PARALLEL", "2")))
    tree = "\n".join(f"- {f['path']}: {f['purpose']}" for f in planned)
    snippets: list[str] = []
    contracts: list[str] = []

    def work_for(spec: dict[str, Any]) -> Any:
        async def work(record: dict[str, Any]) -> str:
            current = {**spec, "purpose": record.get("purpose") or spec.get("purpose", "")}
            prompt = file_prompt(meta, request + _notes(record), tree, (contracts, snippets), current)
            code = await wb._generate_and_write_file(ws_dir, model, current, prompt)
            contracts.append(wb._extract_file_contract(spec["path"], code))
            snippets.append(f"=== {spec['path']} ===\n{code[:1200]}")
            checkpoint.done(ws_dir, spec["path"])
            return code

        return work

    order = [f["path"] for f in planned]
    yield {"type": "run", "run_id": run.id}
    async for kind, path, result in _drive(run, file_nodes(planned, work_for, model), width, order):
        yield _PAUSED if kind == "paused" else _file_event(kind, path, order, result or "")


async def edit_files(ws_dir: Path, instruction: str, model: str, targets: list[dict[str, Any]], prompt_for: Any) -> AsyncIterator[dict[str, Any]]:
    """`prompt_for(spec, instruction)` returns (current content, edit prompt) for one target file."""
    import workspace_builder as wb

    run = run_control.start(instruction, ws_dir.name)
    order = [f["path"] for f in targets]

    def work_for(spec: dict[str, Any]) -> Any:
        async def work(record: dict[str, Any]) -> str:
            current_spec = {**spec, "purpose": record.get("purpose") or spec.get("purpose", "")}
            current, prompt = prompt_for(current_spec, instruction + _notes(record))
            return await apply_edit(wb._generate_and_write_file, (ws_dir, model, prompt), current_spec, current)

        return work

    nodes = [dag.Node(s["path"], work_for(s), deps=(order[i - 1],) if i else (), model=str(s.get("model") or model), title=s["path"], purpose=str(s.get("purpose", "")))
             for i, s in enumerate(targets)]
    yield {"type": "run", "run_id": run.id}
    async for kind, path, result in _drive(run, nodes, 1, order):
        yield _PAUSED if kind == "paused" else _file_event(kind, path, order, result or "")

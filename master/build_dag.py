"""File writing of a project build and of a follow-up change, as a live dependency graph.

New build: the first file alone (others reuse its ids and classes), the independent files side by side, tests last;
meanwhile the sandbox and browser checks that follow are warmed up. Follow-up change: one file after another.
While it runs the user can pause, add a course correction, rewrite what a waiting file must do, or skip it.
"""

from __future__ import annotations

import asyncio
import difflib
import importlib.util
import os
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

import budgets
import checkpoint
import dag
import req_ledger
import run_control
import slice_build
import spec_pointer
import workspace_docker
import write_lease
from workspace_batches import apply_edit, file_batches, file_prompt

WARMUP = "ön hazırlık"


def _notes(record: dict[str, Any]) -> str:
    return "".join(f"\n\nKULLANICININ ÇALIŞIRKEN EKLEDİĞİ TALİMAT (uygula): {n}" for n in record.get("notes", []))


async def _warm_up(_record: dict[str, Any]) -> str:
    """Load what verification will need, while the files are still being written."""
    ready = await asyncio.to_thread(workspace_docker.available)
    browser = importlib.util.find_spec("playwright") is not None
    return f"kod kutusu {'hazır' if ready else 'yok'}, tarayıcı {'hazır' if browser else 'yok'}"


def _governed(ws_dir: Path, budget: budgets.Budget, work_for: Any) -> Any:
    """Every writer holds the lease of its file while it writes and spends from its own slice of the run's budget."""

    def wrap(spec: dict[str, Any]) -> Any:
        work = work_for(spec)

        async def governed(record: dict[str, Any]) -> str:
            path = spec["path"]
            async with write_lease.TABLE.lease(f"{budget.name}:{path}", [f"{ws_dir.name}/{path}"]):
                return await budgets.within(budget.child(path), work(record))

        return governed

    return wrap


async def _rolled_back(ws_dir: Path, before: dict[str, str], events: AsyncIterator[tuple[str, str, Any]]) -> AsyncIterator[tuple[str, str, Any]]:
    """A change that ran out of budget leaves the project as it was before it."""
    try:
        async for event in events:
            yield event
    except budgets.BudgetExceeded:
        for path, text in before.items():
            target = ws_dir / path
            if text:
                target.write_text(text, encoding="utf-8")
            else:
                target.unlink(missing_ok=True)
        raise


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


def _text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace") if path.is_file() else ""


def file_diff(path: str, old: str, new: str, limit: int = 4000) -> str:
    """The unified diff shown in the live stream; "" when nothing changed."""
    lines = difflib.unified_diff(old.splitlines(), new.splitlines(), fromfile=f"önce/{path}", tofile=f"sonra/{path}", lineterm="", n=2)
    return "\n".join(lines)[:limit]


_PAUSED = {"type": "status", "message": "Duraklatıldı. Savaş odasından devam ettirebilir ya da talimat ekleyebilirsin."}


async def _sliced(ws_dir: Path, model: str, spec: dict[str, Any], prompt: str) -> str:
    """The many-constraint page: three checked slices instead of one shot (see slice_build)."""
    import workspace_builder as wb

    chosen = await wb.pick_coder_model(os.environ.get("SLICE_MODEL") or model)
    system = str(spec.get("system") or wb.FILE_WRITER_SYSTEM_PROMPT)

    def writer(temperature: float) -> Any:
        async def generate(system_text: str, user: str) -> str:
            return await wb._ollama_generate(chosen, system_text, user, num_predict=int(spec.get("tokens") or 9000), temperature=temperature)

        return generate

    code = await slice_build.build((ws_dir, prompt, system), req_ledger.ACTIVE.get(), writer(0.2), writer(0.1))
    wb._write_workspace_file(ws_dir, spec["path"], code)
    return code


async def generate_files(ws_dir: Path, meta: dict[str, Any], request: str, model: str, planned: list[dict[str, Any]]) -> AsyncIterator[dict[str, Any]]:
    import workspace_builder as wb

    run = run_control.start(request, str(meta.get("id", "")))
    budget = budgets.run_budget(f"koşu {run.id}")
    ledger = req_ledger.ACTIVE.get()
    if ledger:
        spec_pointer.freeze(ws_dir, request, ledger)
    width = max(1, int(os.environ.get("WS_PARALLEL", "2")))
    tree = "\n".join(f"- {f['path']}: {f['purpose']}" for f in planned)
    snippets: list[str] = []
    contracts: list[str] = []

    def work_for(spec: dict[str, Any]) -> Any:
        async def work(record: dict[str, Any]) -> str:
            current = {**spec, "purpose": record.get("purpose") or spec.get("purpose", "")}
            prompt = file_prompt(meta, request + _notes(record), tree, (contracts, snippets), current) + spec_pointer.pointer(ws_dir, spec["path"], ledger)
            if slice_build.applies(spec["path"], req_ledger.ACTIVE.get()):
                code = await _sliced(ws_dir, str(current.get("model") or model), current, prompt)
            else:
                code = await wb._generate_and_write_file(ws_dir, model, current, prompt)
            contracts.append(wb._extract_file_contract(spec["path"], code))
            snippets.append(f"=== {spec['path']} ===\n{code[:1200]}")
            checkpoint.done(ws_dir, spec["path"])
            return code

        return work

    order = [f["path"] for f in planned]
    yield {"type": "run", "run_id": run.id}
    async for kind, path, result in _drive(run, file_nodes(planned, _governed(ws_dir, budget, work_for), model), width, order):
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

    budget = budgets.run_budget(f"koşu {run.id}")
    governed = _governed(ws_dir, budget, work_for)
    nodes = [dag.Node(s["path"], governed(s), deps=(order[i - 1],) if i else (), model=str(s.get("model") or model), title=s["path"], purpose=str(s.get("purpose", "")))
             for i, s in enumerate(targets)]
    before = {path: _text(ws_dir / path) for path in order}
    yield {"type": "run", "run_id": run.id}
    async for kind, path, result in _rolled_back(ws_dir, before, _drive(run, nodes, 1, order)):
        if kind == "paused":
            yield _PAUSED
            continue
        event = _file_event(kind, path, order, result or "")
        if kind == "done":
            event["diff"] = file_diff(path, before[path], _text(ws_dir / path))
        yield event

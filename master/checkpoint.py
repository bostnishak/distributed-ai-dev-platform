"""Resume an interrupted project build from the last finished file instead of starting over.

The plan and the list of finished files are saved next to the project; "devam et" in the chat writes only what is
missing, then runs the same repair and run checks.
"""

from __future__ import annotations

import json
import re
import subprocess
import time
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx
from fastapi.responses import StreamingResponse

FILE = ".checkpoint.json"
_RESUME_RE = re.compile(r"^\s*(?:(?:yarım kalan|kaldığın yerden)[\w\s]{0,30}|devam(?:\s+et(?:tir)?)?|resume|continue)\s*[.!]*\s*$", re.IGNORECASE)
_STEER_RE = re.compile(r"^\s*(?:devam\s+et|kaldığın\s+yerden(?:\s+devam\s+et)?|resume|continue)\s+(?:ama|fakat|ancak|but)\s+(?P<extra>.{3,400}?)\s*$", re.IGNORECASE | re.DOTALL)
_MAX_AGE_S = 24 * 3600


def save(ws_dir: Path, request: str, model: str, files: list[dict[str, Any]]) -> None:
    _write(ws_dir, {"request": request, "model": model, "files": files, "done": []})


def _write(ws_dir: Path, data: dict[str, Any]) -> None:
    tmp = ws_dir / (FILE + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    tmp.replace(ws_dir / FILE)  # a crash while writing leaves the previous checkpoint intact


def load(ws_dir: Path) -> dict[str, Any] | None:
    try:
        data = json.loads((ws_dir / FILE).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return data if isinstance(data, dict) and data.get("files") else None


def done(ws_dir: Path, path: str) -> None:
    if data := load(ws_dir):
        data["done"] = [*data["done"], path]
        _write(ws_dir, data)


def clear(ws_dir: Path) -> None:
    (ws_dir / FILE).unlink(missing_ok=True)


def remaining(ws_dir: Path, data: dict[str, Any]) -> list[dict[str, Any]]:
    return [f for f in data["files"] if f["path"] not in data["done"] or not (ws_dir / f["path"]).is_file()]


def steering(prompt: str) -> str:
    """The extra instruction of "continue, but ..." ('' for a plain resume or another sentence)."""
    match = _STEER_RE.match(prompt)
    return match["extra"].rstrip(".!") if match else ""


def is_resume(prompt: str) -> bool:
    return bool(_RESUME_RE.match(prompt) or _STEER_RE.match(prompt))


async def stream_resume(ws_id: str, extra: str = "") -> AsyncIterator[dict[str, Any]]:
    import workspace_builder as wb
    from workspace_batches import file_prompt
    from workspace_smoke import smoke_and_repair

    ws_dir = wb.safe_workspace_dir(ws_id)
    data = load(ws_dir)
    if not data:
        return
    meta = wb.load_workspace_meta(ws_dir)
    model = await wb.pick_coder_model(data.get("model"))
    todo = remaining(ws_dir, data)
    finished = [f["path"] for f in data["files"] if f not in todo]
    yield {"type": "status", "message": f"{len(finished)} dosya hazır, kalan {len(todo)} dosya yazılıyor ({model})..."}
    tree = "\n".join(f"- {f['path']}: {f.get('purpose', '')}" for f in data["files"])
    texts = {p: (ws_dir / p).read_text(encoding="utf-8", errors="replace") for p in finished}
    contracts = [wb._extract_file_contract(p, t) for p, t in texts.items()]
    snippets = [f"=== {p} ===\n{t[:1200]}" for p, t in texts.items()]
    for index, spec in enumerate(todo, start=1):
        yield {"type": "file_start", "path": spec["path"], "index": index, "total": len(todo)}
        request = data["request"] + (f"\n\nYARIDA EKLENEN TALİMAT (kalan dosyalarda uygula): {extra}" if extra else "")
        prompt = file_prompt(meta, request, tree, (contracts, snippets), spec)
        code = await wb._generate_and_write_file(ws_dir, model, spec, prompt)
        contracts.append(wb._extract_file_contract(spec["path"], code))
        snippets.append(f"=== {spec['path']} ===\n{code[:1200]}")
        done(ws_dir, spec["path"])
        yield {"type": "file_done", "path": spec["path"], "size": len(code.encode("utf-8")), "index": index, "total": len(todo)}
    wb.repair_project(ws_dir)
    warning = ""
    async for evt in smoke_and_repair(ws_dir, lambda _p, ask: wb._ollama_generate(model, wb.FILE_WRITER_SYSTEM_PROMPT, ask, temperature=0.1)):
        if evt["type"] == "status":
            yield evt
        else:
            warning = evt["warning"]
    warnings = wb.verify_workspace_files(ws_dir) + ([warning] if warning else [])
    wb.create_snapshot(ws_dir, "Kaldığı yerden tamamlandı")
    meta["versions"] = wb.list_snapshots(ws_dir)
    meta["updated_at"] = datetime.now(UTC).isoformat()
    wb.save_workspace_meta(ws_dir, meta)
    clear(ws_dir)
    yield {"type": "done", "workspace": meta, "tree": wb.build_file_tree(ws_dir), "warnings": warnings}


def _find(history: str) -> str:
    """Workspace of this conversation with an unfinished build, else the newest one interrupted in the last day."""
    import revise_chat
    import workspace_builder as wb

    candidates = [revise_chat.last_workspace_id(history)]
    candidates += [str(w.get("id", "")) for w in wb.list_workspaces()]
    for position, ws_id in enumerate(candidates):
        if not ws_id:
            continue
        try:
            marker = wb.safe_workspace_dir(ws_id) / FILE
            if marker.is_file() and (position == 0 or time.time() - marker.stat().st_mtime < _MAX_AGE_S):
                return ws_id
        except (ValueError, OSError):
            continue
    return ""


def fastpath(prompt: str, history: str) -> StreamingResponse | None:
    if not is_resume(prompt) or not (ws_id := _find(history)):
        return None
    return StreamingResponse(_stream(ws_id, steering(prompt)), media_type="text/event-stream")


async def _stream(ws_id: str, extra: str = ""):
    import assistant_stream_fastpaths as fp
    import workspace_builder as wb

    yield fp.sse_event({"type": "token", "content": "Yarım kalan proje bulundu, kaldığı yerden devam ediliyor...\n"})
    try:
        async for evt in stream_resume(ws_id, extra):
            if evt["type"] == "status":
                yield fp.sse_event({"type": "status", "message": evt["message"]})
            elif evt["type"] == "file_done":
                yield fp.sse_event({"type": "token", "content": f"- `{evt['path']}` yazıldı\n"})
            elif evt["type"] == "done":
                note = "\n".join(f"> {w}" for w in evt["warnings"][:3])
                yield fp.sse_event({"type": "token", "content": f"\nProje tamamlandı. Önizlemeden kontrol et.\n{note}\n"})
                yield fp.sse_event(fp._attach_workspace_flags(wb, evt["workspace"], evt["tree"]))
        yield fp.sse_event({"type": "done", "model": "proje-devam", "task_type": "proje"})
    except (httpx.HTTPError, subprocess.SubprocessError, OSError, ValueError, TypeError, KeyError, RuntimeError) as exc:
        yield fp.sse_event({"type": "error", "content": f"{exc} (yazılan dosyalar korundu; tekrar 'devam et' yazabilirsin)"})

"""Chat commands on the conversation's project that need no model: undo, go back to a version, rename a symbol."""

from __future__ import annotations

import re
from pathlib import Path

import code_search
import lsp_client
import refactor
import refactor_move
import repo_map
import revise_chat
import workspace_inspect

_UNDO_RE = re.compile(r"^\s*(?:(?:son\s+)?(?:değişikliği|degisikligi)?\s*geri\s+al|önceki\s+(?:sürüme|hale)\s+(?:dön|geri dön)|undo)\s*[.!]*\s*$", re.IGNORECASE)
_LOAD_RE = re.compile(r"^\s*(?:(?:api\s+)?yük\s+testi(?:\s+yap)?|load\s+test)\s*[.!]*\s*$", re.IGNORECASE)
_VERSION_RE = re.compile(r"^\s*(?:v(?P<a>\d+)\s*['\u2019]?\s*(?:ye|ya|e|a)?\s*(?:geri\s+)?dön|restore\s+v(?P<b>\d+)|sürüm\s+(?P<c>\d+)\s*['\u2019]?\s*(?:e|a|ye|ya)\s*(?:geri\s+)?dön)\s*[.!]*\s*$", re.IGNORECASE)


def parse(prompt: str) -> tuple[str, str] | None:
    """("undo", ""), ("version", "v2") or ("rename", "old new")."""
    if _UNDO_RE.match(prompt):
        return "undo", ""
    if match := _VERSION_RE.match(prompt):
        return "version", "v" + (match["a"] or match["b"] or match["c"])
    if topic := code_search.asked(prompt):
        return "search", topic
    if symbol := lsp_client.asked_symbol(prompt):
        return "references", symbol
    if _LOAD_RE.match(prompt):
        return "load", ""
    if pair := refactor.parse(prompt):
        return "rename", " ".join(pair)
    if refactor_move.parse(prompt):
        return "restructure", prompt
    return None


def previous_version(versions: list[dict], active: str) -> str:
    """The snapshot before the one the project is at now ('' when there is none)."""
    numbers = sorted(int(v["version"][1:]) for v in versions)
    current = int(active[1:]) if active else (numbers[-1] if numbers else 0)
    older = [n for n in numbers if n < current]
    return f"v{older[-1]}" if older else ""


def run(ws_id: str, command: str, value: str) -> str:
    """Carry the command out and say what happened."""
    import workspace_builder as wb

    ws_dir = wb.safe_workspace_dir(ws_id)
    meta = wb.load_workspace_meta(ws_dir)
    if command == "search":
        return code_search.answer(ws_dir, value)
    if command == "references":
        return lsp_client.answer(ws_dir, value)
    if command == "load":
        return load_summary(workspace_inspect.run_load(ws_dir))
    if command == "rename":
        old, new = value.split(" ")
        changed = refactor.rename(ws_dir, old, new)
        if not changed:
            return f"Projede `{old}` adında bir sembol bulamadım; hiçbir dosya değişmedi."
        version = wb.create_snapshot(ws_dir, f"{old} -> {new}")
        meta.update(versions=wb.list_snapshots(ws_dir), active_version=version["version"])
        wb.save_workspace_meta(ws_dir, meta)
        note = repo_map.dependents_note(ws_dir, changed)
        return f"`{old}` → `{new}` olarak model kullanılmadan yeniden adlandırıldı: {', '.join(changed)}." + (f"\n> {note}" if note.startswith("Kırık") else "")
    if command == "restructure":
        return _restructure(ws_dir, meta, value)
    versions = wb.list_snapshots(ws_dir)
    target = value or previous_version(versions, str(meta.get("active_version") or ""))
    if not target or target not in {v["version"] for v in versions}:
        return "Geri dönülecek bir önceki sürüm yok." if command == "undo" else f"{target} adında bir sürüm yok. Olanlar: {', '.join(sorted(v['version'] for v in versions))}"
    wb.restore_snapshot(ws_id, target)
    return f"Proje **{target}** sürümüne döndürüldü. Sonraki sürümler silinmedi; istersen onlara da dönebilirim."


def _restructure(ws_dir: Path, meta: dict, prompt: str) -> str:
    """Move code into a new module or migrate a signature, then save a version."""
    import workspace_builder as wb

    parsed = refactor_move.parse(prompt)
    try:
        changed = refactor_move.run(ws_dir, *parsed) if parsed else []
    except ValueError as exc:
        return f"Yapılmadı: {exc}"
    if not changed:
        return "Değişecek bir yer bulunamadı."
    version = wb.create_snapshot(ws_dir, prompt[:60])
    meta.update(versions=wb.list_snapshots(ws_dir), active_version=version["version"])
    wb.save_workspace_meta(ws_dir, meta)
    note = repo_map.dependents_note(ws_dir, changed)
    return f"Model kullanılmadan yapıldı: {', '.join(changed)}." + (f"\n> {note}" if note.startswith("Kırık") else "")


def load_summary(result: dict) -> str:
    if not result.get("requests"):
        return "Yük testi için parametresiz bir GET uç noktası bulamadım."
    return (f"**Yük testi** ({result['requests']} istek, aynı anda {result['workers']}; yalıtılmış kutuda, ağ gecikmesi hariç)\n"
            f"- Uç noktalar: {', '.join(result['paths'])}\n- Saniyede istek: {result['rps']}\n"
            f"- Gecikme p50/p95/p99: {result['p50']} / {result['p95']} / {result['p99']} ms\n- 5xx hata: {result['errors']}")


def fastpath(prompt: str, history: str):
    import assistant_stream_fastpaths as fp
    import workspace_builder as wb

    parsed = parse(prompt)
    ws_id = revise_chat.last_workspace_id(history) if parsed else ""
    if not ws_id:
        return None
    try:
        if not wb.safe_workspace_dir(ws_id).is_dir():
            return None
        message = run(ws_id, *parsed)
    except (ValueError, OSError, KeyError) as exc:
        return fp.single_token_stream(f"İşlem yapılamadı: {exc}", "proje-komut", "proje")
    return fp.single_token_stream(message, "proje-komut", "proje")
